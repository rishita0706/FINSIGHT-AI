import os, tempfile
os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/t.db"
import pytest
from fastapi.testclient import TestClient
from app.main import app

H = {"X-Requested-With": "FinSight"}
def make_client(): return TestClient(app, headers=H)

@pytest.fixture
def client(): return make_client()

def signup(c, email, pw="correct-horse-battery"):
    assert c.post("/api/v1/auth/register", json={"email": email, "password": pw}).status_code == 201
    assert c.post("/api/v1/auth/login", json={"email": email, "password": pw}).status_code == 200
    return c
