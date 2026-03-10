import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient
from api.app import app

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "ok"

def test_doctor():
    response = client.get("/doctor")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "checks" in body["data"]
    assert "SQLite" in body["data"]["checks"]

def test_list_workflows():
    response = client.get("/workflows")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert isinstance(body["data"], list)
    names = [w["name"] for w in body["data"]]
    assert "project-update" in names

def test_workflow_run_validation():
    response = client.post("/workflows/run", json={"workflow_name": "project-update"})
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "validation_error"

def test_workflow_run_async():
    response = client.post("/workflows/run", json={"workflow_name": "devops", "goal": "list files"})
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "task_id" in body["data"]
    assert body["data"]["status"] == "pending"

def test_list_runs():
    response = client.get("/runs")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert isinstance(body["data"], list)

def test_recent_memory():
    response = client.get("/memory/recent")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert isinstance(body["data"], list)

def test_response_envelope():
    """Tests that every endpoint returns the standard {success, message, data, error} envelope."""
    endpoints = ["/health", "/doctor", "/workflows", "/runs", "/memory/recent"]
    for ep in endpoints:
        response = client.get(ep)
        body = response.json()
        assert "success" in body, f"{ep} missing 'success'"
        assert "message" in body, f"{ep} missing 'message'"
        assert "data" in body or "error" in body, f"{ep} missing 'data' or 'error'"

def test_tracing_header():
    """Tests that the tracing middleware injects X-Request-ID and X-Process-Time headers."""
    response = client.get("/health")
    assert "x-request-id" in response.headers
    assert "x-process-time" in response.headers
