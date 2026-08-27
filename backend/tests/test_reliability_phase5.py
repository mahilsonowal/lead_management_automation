# pyrefly: ignore [missing-import]
import pytest
import sqlite3
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
from app.models import LeadInput
from app.db import save_lead, get_lead_by_id, log_workflow_error, get_workflow_errors, init_db

client = TestClient(app)


def test_duplicate_lead_upsert():
    """Verify that submitting the same lead_id updates rather than crashes."""
    init_db()
    lead_id = "LEAD-DUP-TEST-001"
    
    lead_v1 = {
        "lead_id": lead_id,
        "name": "Original Name",
        "email": "original@example.com",
        "company": "Original Corp",
        "requested_service": "AI Automation",
        "message": "First inquiry message.",
        "score": 50,
        "classification": "warm",
        "status": "OPEN"
    }
    save_lead(lead_v1)
    
    lead_v2 = {
        "lead_id": lead_id,
        "name": "Updated Name",
        "email": "original@example.com",
        "company": "Updated Corp",
        "requested_service": "AI Automation",
        "message": "Updated inquiry message.",
        "score": 85,
        "classification": "hot",
        "status": "CONTACTED"
    }
    save_lead(lead_v2)
    
    stored = get_lead_by_id(lead_id)
    assert stored is not None
    assert stored["score"] == 85
    assert stored["classification"] == "hot"
    assert stored["status"] == "CONTACTED"


def test_database_graceful_error_handling():
    """Verify that a temporary DB error doesn't bring down the API endpoint."""
    payload = {
        "name": "Database Failure Lead",
        "email": "dbtest@example.com",
        "company": "Test Co",
        "requested_service": "Automation",
        "message": "Testing database resilience under simulated failure."
    }
    
    # Mock save_lead to throw a SQLite exception
    with patch("app.main.save_lead", side_effect=sqlite3.OperationalError("Simulated DB lock")):
        response = client.post("/analyze-lead", json=payload)
        # API should still return 200 OK analysis results to the caller (n8n)
        assert response.status_code == 200
        data = response.json()
        assert data["score"] > 0
        assert data["classification"] in ["hot", "warm", "cold"]


def test_error_logging_audit_trail():
    """Verify that workflow errors are correctly recorded in the database."""
    init_db()
    error_type = "SIMULATED_TEST_ERROR"
    error_msg = "Test error message for audit verification"
    
    log_workflow_error(
        error_type=error_type,
        error_message=error_msg,
        lead_id="LEAD-TEST-AUDIT",
        payload={"test": "payload_data"}
    )
    
    errors = get_workflow_errors()
    assert any(e["error_type"] == error_type and e["error_message"] == error_msg for e in errors)
