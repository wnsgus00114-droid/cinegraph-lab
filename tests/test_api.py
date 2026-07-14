import os
import pytest

pytest.importorskip("fastapi")
if not os.path.exists("data/movies.csv"):
    pytest.skip("run `make data` first", allow_module_level=True)

from fastapi.testclient import TestClient
from back.app.main import app

def test_health_and_recommendation():
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        response = client.post("/recommend", json={"liked_movie_ids": [1], "model": "fusion", "top_k": 3})
        assert response.status_code == 200
        assert len(response.json()["recommendations"]) == 3

