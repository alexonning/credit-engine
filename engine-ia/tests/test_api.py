"""Testes de integracao do fluxo completo via FastAPI TestClient."""
from __future__ import annotations

from decimal import Decimal

from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app
from app.schemas.credit import Decision

# desabilita a dependencia de DB nos testes (roda sem Postgres)
def _no_db():
    yield None


app.dependency_overrides[get_db] = _no_db

client = TestClient(app)


def _payload(**overrides) -> dict:
    base = {
        "applicant": {
            "document": "12345678900",
            "name": "Maria Silva",
            "monthly_income": "6000",
            "existing_debt": "300",
            "credit_score": 720,
            "employment_status": "employed",
        },
        "product": {"product_code": "CDC", "amount": "20000", "term_months": 24},
    }
    base.update(overrides)
    return base


def test_health():
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_analyze_approved():
    r = client.post("/api/v1/credit/analyze", json=_payload())
    assert r.status_code == 200
    data = r.json()
    assert data["decision"] in {d.value for d in Decision}
    assert "explanation" in data
    assert len(data["agent_results"]) >= 4


def test_analyze_denied_blacklist():
    payload = _payload()
    payload["applicant"]["is_blacklisted"] = True
    r = client.post("/api/v1/credit/analyze", json=payload)
    assert r.status_code == 200
    assert r.json()["decision"] == Decision.DENIED.value


def test_analyze_denied_low_score():
    payload = _payload()
    payload["applicant"]["credit_score"] = 200
    r = client.post("/api/v1/credit/analyze", json=payload)
    assert r.status_code == 200
    assert r.json()["decision"] == Decision.DENIED.value


def test_analyze_stream_emits_decision_then_explanation():
    r = client.post("/api/v1/credit/analyze/stream", json=_payload())
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/event-stream")

    body = r.text
    # a decisao vem antes da explicacao, que vem antes do 'done'
    assert "event: decision" in body
    assert "event: explanation" in body
    assert "event: done" in body
    assert body.index("event: decision") < body.index("event: explanation")
    assert body.index("event: explanation") < body.index("event: done")

    # o primeiro frame ja carrega a decisao consolidada
    first = body.split("\n\n", 1)[0]
    assert '"decision"' in first
    assert '"agent_results"' in first
