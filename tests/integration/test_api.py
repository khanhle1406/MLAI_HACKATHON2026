"""API integration tests."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)


class TestHealthEndpoint:
    def test_health(self):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "healthy"

    def test_root(self):
        r = client.get("/")
        assert r.status_code == 200
        assert "DataGuard" in r.json()["name"]


class TestDatasetsAPI:
    def test_upload_csv(self):
        with open("verify/fixtures/v1_whitespace.csv", "rb") as f:
            r = client.post("/api/datasets", files={"file": ("test.csv", f, "text/csv")})
        assert r.status_code == 201
        data = r.json()
        assert data["status"] == "COMPLETED"
        assert data["summary"]["auto_count"] >= 1

    def test_list_datasets(self):
        r = client.get("/api/datasets")
        assert r.status_code == 200
        assert "datasets" in r.json()

    def test_unsupported_format(self):
        r = client.post(
            "/api/datasets",
            files={"file": ("test.txt", b"hello world", "text/plain")},
        )
        assert r.status_code == 400


class TestVerifyAPI:
    def test_verify_endpoint_exists(self):
        # Note: POST /api/verify runs all fixtures
        r = client.post("/api/verify")
        assert r.status_code == 200
        data = r.json()
        assert "cases" in data
        assert "total" in data


class TestReviewsAPI:
    def test_list_reviews(self):
        r = client.get("/api/reviews")
        assert r.status_code == 200
        assert "queue" in r.json()


class TestAuditAPI:
    def test_query_audit(self):
        r = client.get("/api/audit")
        assert r.status_code == 200
        assert "events" in r.json()


class TestStatsAPI:
    def test_stats(self):
        r = client.get("/api/stats")
        assert r.status_code == 200
        data = r.json()
        assert "datasets_count" in data
        assert "llm_cost" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
