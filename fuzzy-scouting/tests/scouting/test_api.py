from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from fuzzyscout.application.scouting_service import ScoutingService
from fuzzyscout.interfaces.api.app import create_app

from .conftest import STRIKER_STATS


@pytest.fixture
def client(memory_service: ScoutingService) -> TestClient:
    return TestClient(create_app(service=memory_service))


def test_health_and_reference_endpoints(client: TestClient) -> None:
    assert client.get("/health").json()["status"] == "ok"
    positions = client.get("/positions").json()
    assert {p["code"] for p in positions} >= {"attaquant", "gardien"}
    players = client.get("/players").json()
    assert [p["id"] for p in players] == ["S1", "S2", "S3"]
    assert client.get("/players/S1").json()["nom"] == "Buteur Fort"
    assert client.get("/players/zz").status_code == 404
    knowledge = client.get("/knowledge").json()
    assert all(item["nb_regles"] > 0 for item in knowledge)


def test_evaluation_endpoints(client: TestClient) -> None:
    response = client.post(
        "/evaluations", json={"position": "attaquant", "player_id": "S1", "trace": True}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["aptitude"] > 70 and body["etapes"][0]["systeme"] == "technique_attaquant"
    assert body["etapes"][0]["regles_declenchees"][0]["force"] > 0

    assert (
        client.post("/evaluations", json={"position": "attaquant", "player_id": "nope"}).status_code
        == 404
    )
    assert (
        client.post("/evaluations", json={"position": "libero", "player_id": "S1"}).status_code
        == 404
    )
    missing = client.post("/evaluations", json={"position": "attaquant", "player_id": "S3"})
    assert missing.status_code == 422 and "manquant" in missing.json()["detail"]

    ad_hoc = client.post(
        "/evaluations/ad-hoc",
        json={"position": "attaquant", "attributes": STRIKER_STATS, "name": "X"},
    )
    assert ad_hoc.status_code == 200 and ad_hoc.json()["joueur"]["nom"] == "X"
    assert ad_hoc.json()["etapes"] is None


def test_ranking_endpoint(client: TestClient) -> None:
    response = client.post("/rankings", json={"position": "attaquant", "limit": 5, "max_age": 30})
    assert response.status_code == 200
    body = response.json()
    assert body["classes"] == 1 and body["classement"][0]["rang"] == 1
    assert {s["id"] for s in body["exclus"]} == {"S2", "S3"}
    assert client.post("/rankings", json={"position": "attaquant", "limit": 0}).status_code == 422
