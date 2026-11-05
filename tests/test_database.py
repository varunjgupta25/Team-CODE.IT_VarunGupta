"""
tests/test_database.py

Unit and integration tests for the production-grade database layer:
1. CRUD operations with timestamp tracking (created_at, updated_at).
2. Soft-delete and hard-delete behavior.
3. Collection queries with multi-key filtering.
4. Atomic transaction semantics (commit and rollback on exception).
5. Fast-fail connection lifecycle in production mode.
"""

import pytest
from core.config import settings
from core.database import FirestoreDB, db


def test_database_crud_with_timestamps():
    """Verify document creation, updates, and automatic timestamp tracking."""
    doc_id = "test_crud_doc_1"
    initial_data = {"name": "Test Item", "status": "active"}

    saved = db.set_document("test_col", doc_id, initial_data)
    assert saved["id"] == doc_id
    assert "created_at" in saved
    assert "updated_at" in saved

    fetched = db.get_document("test_col", doc_id)
    assert fetched is not None
    assert fetched["name"] == "Test Item"
    assert fetched["created_at"] == saved["created_at"]

    # Update document
    updated = db.update_document("test_col", doc_id, {"status": "inactive"})
    assert updated["status"] == "inactive"
    assert updated["updated_at"] >= saved["updated_at"]

    # Clean up
    db.delete_document("test_col", doc_id, soft=False)
    assert db.get_document("test_col", doc_id) is None


def test_database_soft_delete():
    """Verify soft-delete marks document as isDeleted and excludes it from queries."""
    doc_id = "test_soft_delete_doc"
    db.set_document("test_soft", doc_id, {"name": "Temporary Record"})

    # Perform soft delete
    deleted = db.delete_document("test_soft", doc_id, soft=True)
    assert deleted is True

    # Document should not be returned by get_document or list_collection
    assert db.get_document("test_soft", doc_id) is None
    listed = db.list_collection("test_soft")
    assert not any(d["id"] == doc_id for d in listed)


def test_database_query_filtering():
    """Verify query_collection filters documents correctly."""
    db.clear_collection("test_query")
    db.set_document("test_query", "q1", {"category": "electrician", "rating": 5})
    db.set_document("test_query", "q2", {"category": "electrician", "rating": 4})
    db.set_document("test_query", "q3", {"category": "plumber", "rating": 5})

    # Query single filter
    plumbers = db.query_collection("test_query", {"category": "plumber"})
    assert len(plumbers) == 1
    assert plumbers[0]["id"] == "q3"

    # Query multi-field filter
    top_elec = db.query_collection("test_query", {"category": "electrician", "rating": 5})
    assert len(top_elec) == 1
    assert top_elec[0]["id"] == "q1"


def test_database_transaction_commit():
    """Verify atomic transaction commits multi-document writes cleanly."""
    def _tx_callback(tx):
        tx.set_document("tx_col", "tx_doc_1", {"balance": 100})
        tx.set_document("tx_col", "tx_doc_2", {"balance": 200})
        return "success"

    result = db.run_transaction(_tx_callback)
    assert result == "success"

    doc1 = db.get_document("tx_col", "tx_doc_1")
    doc2 = db.get_document("tx_col", "tx_doc_2")
    assert doc1 is not None and doc1["balance"] == 100
    assert doc2 is not None and doc2["balance"] == 200


def test_database_transaction_rollback():
    """Verify transaction rolls back all pending writes when an exception is raised."""
    db.set_document("tx_col", "orig_doc", {"balance": 500})

    def _failing_tx(tx):
        tx.update_document("tx_col", "orig_doc", {"balance": 1000})
        tx.set_document("tx_col", "new_doc", {"balance": 300})
        raise ValueError("Simulated transaction failure")

    with pytest.raises(ValueError, match="Simulated transaction failure"):
        db.run_transaction(_failing_tx)

    # State must be completely restored
    orig = db.get_document("tx_col", "orig_doc")
    assert orig["balance"] == 500
    assert db.get_document("tx_col", "new_doc") is None


def test_production_fail_fast_without_credentials(monkeypatch):
    """Verify database connect fails fast if production environment lacks credentials."""
    prod_db = FirestoreDB()
    monkeypatch.setattr(prod_db, "_use_mock", False)
    monkeypatch.setattr(prod_db, "_firestore_client", None)

    with pytest.raises(RuntimeError, match="CRITICAL"):
        prod_db.connect()

