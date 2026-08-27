# pyrefly: ignore [missing-import]
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    """Verify that the health check endpoint returns 200 OK and healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_hot_lead_scoring():
    """
    Profile 1: Rahul Das
    - Urgent keyword in message (+30)
    - Target service 'CRM and AI automation' (+25)
    - Company provided (+20)
    - Valid email (+15)
    - Long message >= 30 chars (+10)
    Expected score: 100, classification: hot
    """
    payload = {
        "name": "Rahul Das",
        "email": "rahul@example.com",
        "company": "North East Digital Agency",
        "requested_service": "CRM and AI automation",
        "message": "We urgently need help automating our customer support and lead follow-up process."
    }
    response = client.post("/analyze-lead", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["classification"] == "hot"
    assert data["score"] == 100
    assert data["service_requested"] == "CRM and AI automation"
    assert "Immediate direct callback" in data["next_action"]
    assert "Rahul Das" in data["reply"]


def test_warm_lead_scoring():
    """
    Profile 2: Priya Sharma
    - No urgency keyword (0)
    - Target service 'AI and Workflow Operations' (+25)
    - Company provided (+20)
    - Valid email (+15)
    - Long message >= 30 chars (+10)
    Expected score: 70 -> hot, or without target keywords:
    Let's test Priya with 'SaaS operations' (no target keyword):
    - No urgency (0)
    - 'SaaS operations' (0)
    - Company provided (+20)
    - Valid email (+15)
    - Long message (+10)
    Total = 45 -> warm
    """
    payload = {
        "name": "Priya Sharma",
        "email": "priya@example.com",
        "company": "Bright SaaS",
        "requested_service": "SaaS operations",
        "message": "We would like to learn more about improving our onboarding workflow."
    }
    # Note: 'workflow' in message triggers +10 for message length, but let's check service
    response = client.post("/analyze-lead", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["classification"] == "warm"
    assert 40 <= data["score"] < 70
    assert "discovery call" in data["next_action"].lower()


def test_cold_lead_scoring():
    """
    Profile 3: Amit Kumar
    - No urgency (0)
    - General service (0)
    - No company (0)
    - Valid email (+15)
    - Short message < 30 chars (0)
    Total = 15 -> cold
    """
    payload = {
        "name": "Amit Kumar",
        "email": "amit@example.com",
        "company": "",
        "requested_service": "General inquiry",
        "message": "Please send info."
    }
    response = client.post("/analyze-lead", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["classification"] == "cold"
    assert data["score"] == 15
    assert "nurture sequence" in data["next_action"].lower()


def test_invalid_email_validation_error():
    """Validation test: Invalid email format should return 422."""
    payload = {
        "name": "Test User",
        "email": "invalid-email-address",
        "company": "Test Co",
        "requested_service": "Automation",
        "message": "Testing message here."
    }
    response = client.post("/analyze-lead", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert data["status"] == "error"
    assert data["error_type"] == "VALIDATION_ERROR"
    assert any("email" in err.lower() for err in data["details"])


def test_missing_name_validation_error():
    """Validation test: Missing name or name too short should return 422."""
    payload = {
        "name": "A",
        "email": "valid@example.com",
        "company": "Test Co",
        "requested_service": "Automation",
        "message": "Testing message here."
    }
    response = client.post("/analyze-lead", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert data["status"] == "error"
    assert any("name" in err.lower() for err in data["details"])


def test_missing_message_validation_error():
    """Validation test: Message shorter than 5 chars should return 422."""
    payload = {
        "name": "Valid Name",
        "email": "valid@example.com",
        "company": "Test Co",
        "requested_service": "Automation",
        "message": "Hi"
    }
    response = client.post("/analyze-lead", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert data["status"] == "error"
    assert any("message" in err.lower() for err in data["details"])


def test_missing_requested_service_validation_error():
    """Validation test: Empty requested service should return 422."""
    payload = {
        "name": "Valid Name",
        "email": "valid@example.com",
        "company": "Test Co",
        "requested_service": "",
        "message": "Testing message here."
    }
    response = client.post("/analyze-lead", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert data["status"] == "error"
    assert any("requested_service" in err.lower() for err in data["details"])
