import pytest
from fastapi.testclient import TestClient

def test_health_endpoint(client):
    # Both root and v1 health should work
    response = client.get("/health")
    assert response.status_code == 200
    
    response_v1 = client.get("/api/v1/health")
    assert response_v1.status_code == 200
    assert response_v1.json()["status"] == "ok"

def test_status_endpoint(client):
    response = client.get("/api/v1/status")
    assert response.status_code == 200
    data = response.json()
    assert "agent" in data
    assert "tools" in data

def test_list_tools_endpoint(client):
    response = client.get("/api/v1/tools")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
