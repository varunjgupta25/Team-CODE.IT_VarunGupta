import json
import os
import threading
from typing import Any, Dict, List, Optional
from core.config import settings

# Attempt Firebase Admin imports
try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False


class FirestoreDB:
    """
    Unified database interface for Firestore.
    Operates seamlessly against either a live Google Cloud Firestore instance or
    a thread-safe local JSON-backed store when running in mock/local development mode.
    """

    def __init__(self):
        self._lock = threading.Lock()
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
        self._save_to_disk = True

        os.makedirs(self._data_dir, exist_ok=True)
        self._load_local_store()

        if not self._use_mock and FIREBASE_AVAILABLE:
            self._init_real_firebase()

    def _init_real_firebase(self):
        try:
            if settings.FIREBASE_CREDENTIALS_PATH and os.path.exists(settings.FIREBASE_CREDENTIALS_PATH):
                cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
                if not firebase_admin._apps:
                    firebase_admin.initialize_app(cred)
                self._firestore_client = firestore.client()
                self._use_mock = False
            else:
                # Fallback to local store if file does not exist
                self._use_mock = True
        except Exception:
            self._use_mock = True

    def _load_local_store(self):
        with self._lock:
            if os.path.exists(self._store_file):
                try:
                    with open(self._store_file, "r", encoding="utf-8") as f:
                        loaded = json.load(f)
                        for col in self._mem_store:
                            if col in loaded:
                                self._mem_store[col] = loaded[col]
                except Exception:
                    pass

    def _save_local_store(self):
        if self._use_mock and getattr(self, "_save_to_disk", True):
            with self._lock:
                try:
                    with open(self._store_file, "w", encoding="utf-8") as f:
                        json.dump(self._mem_store, f, indent=2, default=str)
                except Exception:
                    pass

    def get_document(self, collection: str, doc_id: str) -> Optional[Dict[str, Any]]:
        if not self._use_mock and self._firestore_client:
            doc_ref = self._firestore_client.collection(collection).document(doc_id)
            doc = doc_ref.get()
            if doc.exists:
                data = doc.to_dict()
                data["id"] = doc.id
                return data
            return None

        with self._lock:
            col = self._mem_store.get(collection, {})
            doc = col.get(doc_id)
            if doc is not None:
                copied = dict(doc)
                copied["id"] = doc_id
                return copied
            return None

    def set_document(self, collection: str, doc_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        doc_data = dict(data)
        doc_data["id"] = doc_id

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
        if not self._use_mock and self._firestore_client:
            self._firestore_client.collection(collection).document(doc_id).update(data)
            return self.get_document(collection, doc_id)

        with self._lock:
            if collection not in self._mem_store or doc_id not in self._mem_store[collection]:
                raise KeyError(f"Document {doc_id} not found in collection {collection}")
            self._mem_store[collection][doc_id].update(data)
            updated = dict(self._mem_store[collection][doc_id])
            updated["id"] = doc_id

        self._save_local_store()
        return updated

    def delete_document(self, collection: str, doc_id: str) -> bool:
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
                item = d.to_dict()
                item["id"] = d.id
                result.append(item)
            return result

        with self._lock:
            col = self._mem_store.get(collection, {})
            results = []
            for doc_id, doc in col.items():
                item = dict(doc)
                item["id"] = doc_id
                results.append(item)
            return results

    def query_collection(self, collection: str, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
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
