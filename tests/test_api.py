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
    assert "message" in response.json()

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "antigravity"}

def test_doctor():
    response = client.get("/doctor")
    assert response.status_code == 200
    assert "doctor" in response.json()
    assert "SQLite"  in response.json()["doctor"]

def test_list_workflows():
    response = client.get("/workflows")
    assert response.status_code == 200
    assert "workflows" in response.json()
    assert "project-update" in response.json()["workflows"]

def test_workflow_run_validation():
    # Test missing target/goal
    response = client.post("/workflows/run", json={"workflow_name": "project-update"})
    assert response.status_code == 400
    assert "requires 'target' and 'goal'" in response.json()["detail"]

def test_list_runs():
    response = client.get("/runs")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_recent_memory():
    response = client.get("/memory/recent")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
