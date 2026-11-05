import copy
from datetime import datetime, timezone
import json
import logging
import os
import threading
from typing import Any, Callable, Dict, List, Optional
from core.config import settings

logger = logging.getLogger(__name__)

# Attempt Firebase Admin imports
try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    from google.api_core import retry as google_retry
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False


class TransactionContext:
    """
    Unified transaction context passed to transaction callbacks.
    Provides atomic read-then-write semantics across both Firestore and mock store.
    """

    def __init__(self, db_instance: "FirestoreDB", real_tx=None):
        self._db = db_instance
        self._real_tx = real_tx
        self._pending_writes: List[Callable[[], None]] = []

    def get_document(self, collection: str, doc_id: str) -> Optional[Dict[str, Any]]:
        if self._real_tx and self._db._firestore_client:
            doc_ref = self._db._firestore_client.collection(collection).document(doc_id)
            snapshot = doc_ref.get(transaction=self._real_tx)
            if snapshot.exists:
                data = snapshot.to_dict() or {}
                if not data.get("isDeleted", False):
                    data["id"] = snapshot.id
                    return data
            return None
        return self._db.get_document(collection, doc_id)

    def set_document(self, collection: str, doc_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        now_iso = datetime.now(timezone.utc).isoformat()
        doc_data = dict(data)
        doc_data["id"] = doc_id
        if "created_at" not in doc_data and "createdAt" not in doc_data:
            doc_data["created_at"] = now_iso
        doc_data["updated_at"] = now_iso

        if self._real_tx and self._db._firestore_client:
            doc_ref = self._db._firestore_client.collection(collection).document(doc_id)
            self._real_tx.set(doc_ref, doc_data)
            return doc_data
        return self._db.set_document(collection, doc_id, doc_data)

    def update_document(self, collection: str, doc_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        update_data = dict(data)
        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

        if self._real_tx and self._db._firestore_client:
            doc_ref = self._db._firestore_client.collection(collection).document(doc_id)
            self._real_tx.update(doc_ref, update_data)
            return update_data
        return self._db.update_document(collection, doc_id, update_data)

    def delete_document(self, collection: str, doc_id: str, soft: bool = True) -> bool:
        if soft:
            self.update_document(collection, doc_id, {
                "isDeleted": True,
                "deleted_at": datetime.now(timezone.utc).isoformat()
            })
            return True

        if self._real_tx and self._db._firestore_client:
            doc_ref = self._db._firestore_client.collection(collection).document(doc_id)
            self._real_tx.delete(doc_ref)
            return True
        return self._db.delete_document(collection, doc_id, soft=False)

    def list_collection(self, collection: str) -> List[Dict[str, Any]]:
        return self._db.list_collection(collection)

    def query_collection(self, collection: str, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        return self._db.query_collection(collection, filters)

    def get_documents_in_bulk(self, collection: str, doc_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        return self._db.get_documents_in_bulk(collection, doc_ids)


class FirestoreDB:
    """
    Unified production-grade database interface for Firestore.
    Features:
    - Connection pooling & lifecycle management (connect on startup, disconnect on shutdown)
    - Credentials loaded from JSON environment variable or service account path
    - Server-side indexed querying using .where()
    - Atomic transactions support with retry strategies
    - Soft-delete and timestamp tracking (created_at, updated_at)
    - Fallback in-memory storage strictly isolated to local testing & development
    - Resilient to read-only environments
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._use_mock = settings.USE_MOCK_FIREBASE
        self._data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        self._store_file = os.path.join(self._data_dir, "store.json")
        self._mem_store: Dict[str, Dict[str, Dict[str, Any]]] = {
            "users": {},
            "workers": {},
            "jobs": {},
            "offers": {},
            "reviews": {},
            "sos_alerts": {},
            "reports": {},
        }
        self._firestore_client = None
        self._save_to_disk = False

        try:
            os.makedirs(self._data_dir, exist_ok=True)
        except Exception as exc:
            logger.warning("Could not create data dir %s: %s. Continuing in memory.", self._data_dir, exc)

        # If real firebase requested or in production, initialize connection
        if not self._use_mock or settings.ENV in ["production", "staging"]:
            self._init_real_firebase()

    def connect(self):
        """
        Lifecycle hook invoked during application startup.
        Ensures database readiness and validates remote connection in production.
        """
        if not self._use_mock:
            if not FIREBASE_AVAILABLE:
                raise RuntimeError("CRITICAL: firebase-admin is required for production database mode.")
            if not self._firestore_client:
                self._init_real_firebase()
            if not self._firestore_client:
                raise RuntimeError("CRITICAL: Failed to connect to production Firestore database.")
            logger.info("Successfully established connection to Firestore database.")
        else:
            logger.info("Database initialized in development/mock in-memory mode.")

    def disconnect(self):
        """
        Lifecycle hook invoked during application shutdown.
        Closes connection pools and releases socket resources cleanly.
        """
        if self._firestore_client is not None:
            try:
                if hasattr(self._firestore_client, "close"):
                    self._firestore_client.close()
                logger.info("Database connection closed cleanly.")
            except Exception as exc:
                logger.warning("Error during database shutdown: %s", exc)
            finally:
                self._firestore_client = None

    def _init_real_firebase(self):
        if not FIREBASE_AVAILABLE:
            if settings.ENV in ["production", "staging"]:
                raise RuntimeError("CRITICAL: firebase-admin is not installed in production environment.")
            self._use_mock = True
            return

        try:
            cred = None
            if settings.FIREBASE_CREDENTIALS_JSON:
                try:
                    cred_dict = json.loads(settings.FIREBASE_CREDENTIALS_JSON)
                    cred = credentials.Certificate(cred_dict)
                except Exception as json_err:
                    raise ValueError(f"Invalid FIREBASE_CREDENTIALS_JSON: {json_err}") from json_err
            elif settings.FIREBASE_CREDENTIALS_PATH and os.path.exists(settings.FIREBASE_CREDENTIALS_PATH):
                cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
            elif settings.FIRESTORE_PROJECT_ID:
                cred = credentials.ApplicationDefault()

            if cred:
                app_options = {}
                if settings.FIRESTORE_PROJECT_ID:
                    app_options["projectId"] = settings.FIRESTORE_PROJECT_ID

                if not firebase_admin._apps:
                    firebase_admin.initialize_app(cred, app_options if app_options else None)

                self._firestore_client = firestore.client()
                self._use_mock = False
                logger.info("Real Firestore client initialized successfully.")
            else:
                if settings.ENV in ["production", "staging"]:
                    raise RuntimeError("CRITICAL: No valid Firestore credentials found for production environment.")
                self._use_mock = True
        except Exception as exc:
            if settings.ENV in ["production", "staging"]:
                raise RuntimeError(f"Database connection failure in production: {exc}") from exc
            logger.warning("Firestore initialization skipped: %s. Using in-memory store.", exc)
            self._use_mock = True

    def _save_local_store(self):
        if self._use_mock and getattr(self, "_save_to_disk", False):
            with self._lock:
                try:
                    with open(self._store_file, "w", encoding="utf-8") as f:
                        json.dump(self._mem_store, f, indent=2, default=str)
                except Exception as exc:
                    logger.warning("Failed to save local store to %s: %s. Continuing in memory.", self._store_file, exc)

    def get_document(self, collection: str, doc_id: str) -> Optional[Dict[str, Any]]:
        if not self._use_mock and self._firestore_client:
            doc_ref = self._firestore_client.collection(collection).document(doc_id)
            doc = doc_ref.get()
            if doc.exists:
                data = doc.to_dict() or {}
                if not data.get("isDeleted", False):
                    data["id"] = doc.id
                    return data
            return None

        with self._lock:
            col = self._mem_store.get(collection, {})
            doc = col.get(doc_id)
            if doc is not None and not doc.get("isDeleted", False):
                copied = dict(doc)
                copied["id"] = doc_id
                return copied
            return None

    def set_document(self, collection: str, doc_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        doc_data = dict(data)
        doc_data["id"] = doc_id
        now_iso = datetime.now(timezone.utc).isoformat()
        if "created_at" not in doc_data and "createdAt" not in doc_data:
            doc_data["created_at"] = now_iso
        doc_data["updated_at"] = now_iso

        if not self._use_mock and self._firestore_client:
            self._firestore_client.collection(collection).document(doc_id).set(doc_data)
            return doc_data

        with self._lock:
            if collection not in self._mem_store:
                self._mem_store[collection] = {}
            self._mem_store[collection][doc_id] = doc_data
        self._save_local_store()
        return doc_data

    def update_document(self, collection: str, doc_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        update_data = dict(data)
        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

        if not self._use_mock and self._firestore_client:
            self._firestore_client.collection(collection).document(doc_id).update(update_data)
            return self.get_document(collection, doc_id)

        with self._lock:
            if collection not in self._mem_store or doc_id not in self._mem_store[collection]:
                raise KeyError(f"Document {doc_id} not found in collection {collection}")
            self._mem_store[collection][doc_id].update(update_data)
            updated = dict(self._mem_store[collection][doc_id])
            updated["id"] = doc_id
            self._save_local_store()
            return updated

    def delete_document(self, collection: str, doc_id: str, soft: bool = False) -> bool:
        if soft:
            try:
                self.update_document(collection, doc_id, {
                    "isDeleted": True,
                    "deleted_at": datetime.now(timezone.utc).isoformat()
                })
                return True
            except KeyError:
                return False

        if not self._use_mock and self._firestore_client:
            self._firestore_client.collection(collection).document(doc_id).delete()
            return True

        with self._lock:
            if collection in self._mem_store and doc_id in self._mem_store[collection]:
                del self._mem_store[collection][doc_id]
                self._save_local_store()
                return True
        return False

    def list_collection(self, collection: str) -> List[Dict[str, Any]]:
        if not self._use_mock and self._firestore_client:
            docs = self._firestore_client.collection(collection).stream()
            result = []
            for d in docs:
                item = d.to_dict() or {}
                if not item.get("isDeleted", False):
                    item["id"] = d.id
                    result.append(item)
            return result

        with self._lock:
            col = self._mem_store.get(collection, {})
            results = []
            for doc_id, doc in col.items():
                if not doc.get("isDeleted", False):
                    item = dict(doc)
                    item["id"] = doc_id
                    results.append(item)
            return results

    def query_collection(self, collection: str, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Execute filtered collection queries.
        In real Firestore mode, uses server-side .where() clauses to avoid full table scans.
        """
        if not self._use_mock and self._firestore_client:
            query = self._firestore_client.collection(collection)
            for k, v in filters.items():
                query = query.where(k, "==", v)
            docs = query.stream()
            results = []
            for d in docs:
                item = d.to_dict() or {}
                if not item.get("isDeleted", False):
                    item["id"] = d.id
                    results.append(item)
            return results

        all_docs = self.list_collection(collection)
        filtered = []
        for doc in all_docs:
            match = True
            for k, v in filters.items():
                if doc.get(k) != v:
                    match = False
                    break
            if match:
                filtered.append(doc)
        return filtered

    def get_documents_in_bulk(self, collection: str, doc_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Batch-fetches multiple documents by their IDs in a single O(1) bulk operation.
        Eliminates N+1 query patterns.
        """
        if not doc_ids:
            return {}

        unique_ids = list(set(doc_ids))

        if not self._use_mock and self._firestore_client:
            result = {}
            for i in range(0, len(unique_ids), 500):
                chunk = unique_ids[i:i+500]
                refs = [self._firestore_client.collection(collection).document(did) for did in chunk]
                snapshots = self._firestore_client.get_all(refs)
                for s in snapshots:
                    if s.exists:
                        d = s.to_dict() or {}
                        if not d.get("isDeleted", False):
                            d["id"] = s.id
                            result[s.id] = d
            return result

        with self._lock:
            col = self._mem_store.get(collection, {})
            result = {}
            for did in unique_ids:
                doc = col.get(did)
                if doc and not doc.get("isDeleted", False):
                    item = dict(doc)
                    item["id"] = did
                    result[did] = item
            return result

    def get_reports_count_in_bulk(self, worker_ids: Optional[List[str]] = None) -> Dict[str, int]:
        """
        Batch aggregates report counts per worker in a single pass.
        Eliminates individual N queries when matching or listing workers.
        """
        all_reports = self.list_collection("reports")
        counts: Dict[str, int] = {}
        target_set = set(worker_ids) if worker_ids is not None else None
        for r in all_reports:
            wid = r.get("workerId")
            if wid:
                if target_set is None or wid in target_set:
                    counts[wid] = counts.get(wid, 0) + 1
        return counts

    def run_transaction(self, callback: Callable[[TransactionContext], Any]) -> Any:
        """
        Execute a unit of work inside an atomic transaction.
        In Firestore mode, retries automatically on contention via Firestore transactional engine.
        In mock mode, provides isolated snapshot semantics with rollback on error.
        """
        if not self._use_mock and self._firestore_client:
            @firestore.transactional
            def _firestore_tx(transaction):
                ctx = TransactionContext(self, real_tx=transaction)
                return callback(ctx)

            tx = self._firestore_client.transaction()
            return _firestore_tx(tx)

        with self._lock:
            snapshot = copy.deepcopy(self._mem_store)
            ctx = TransactionContext(self)
            try:
                result = callback(ctx)
                self._save_local_store()
                return result
            except Exception:
                self._mem_store = snapshot
                raise

    def clear_collection(self, collection: str):
        if not self._use_mock and self._firestore_client:
            docs = self._firestore_client.collection(collection).stream()
            for doc in docs:
                doc.reference.delete()
            return

        with self._lock:
            if collection in self._mem_store:
                self._mem_store[collection] = {}
        self._save_local_store()


db = FirestoreDB()
