import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_frontend_loads():
    response = client.get("/")
    assert response.status_code == 200


def test_analyze_missing_fields():
    # Pydantic should reject incomplete profile with 422
    response = client.post("/analyze", json={"business_name": "Test"})
    assert response.status_code == 422


def test_analyze_valid_profile():
    # Valid profile should be accepted and start streaming
    response = client.post("/analyze", json={
        "business_name": "Test Co",
        "business_type": "Restaurant",
        "state": "Kerala",
        "employee_count": 10,
        "annual_turnover_lakhs": 40.0,
        "industry_sector": "Food & beverage",
        "has_gst": False,
        "additional_info": None
    })
    # 200 means endpoint accepted it — actual agent output needs real API credits
    assert response.status_code == 200


def test_analyze_invalid_employee_count():
    # employee_count must be an integer not a string
    response = client.post("/analyze", json={
        "business_name": "Test Co",
        "business_type": "Restaurant",
        "state": "Kerala",
        "employee_count": "ten",
        "annual_turnover_lakhs": 40.0,
        "industry_sector": "Food & beverage",
        "has_gst": False
    })
    assert response.status_code == 422