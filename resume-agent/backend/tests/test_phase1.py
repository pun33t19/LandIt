"""
Phase 1 smoke tests — run with: pytest tests/ -v
"""
import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_resume_health():
    r = client.get("/api/resume/health")
    assert r.status_code == 200


def test_jobs_health():
    r = client.get("/api/jobs/health")
    assert r.status_code == 200


def test_upload_wrong_filetype():
    """Should reject non-PDF/DOCX files."""
    r = client.post(
        "/api/resume/upload",
        files={"file": ("test.exe", b"fake binary", "application/octet-stream")}
    )
    assert r.status_code == 415
