import os
import tempfile

_db = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_db}"
os.environ["ENABLE_SCHEDULER"] = "false"
os.environ["REDIS_URL"] = "redis://127.0.0.1:1/0"  # unreachable -> exercises the no-cache fallback

from datetime import timedelta  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import seed  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import utcnow  # noqa: E402
from app.scheduler import apply_due_schedules  # noqa: E402

API = "/api/v1"


@pytest.fixture(scope="module")
def client():
    Base.metadata.create_all(engine)
    seed.run()
    with TestClient(app) as c:
        yield c


def login(client, user="admin", pw="Admin@12345"):
    r = client.post(f"{API}/auth/login", data={"username": user, "password": pw})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_auth_and_rbac(client):
    assert client.post(f"{API}/auth/login", data={"username": "admin", "password": "bad"}).status_code == 401
    assert client.get(f"{API}/flags").status_code == 401
    admin = login(client)
    roles = {r["name"]: r["id"] for r in client.get(f"{API}/roles", headers=admin).json()}
    for name in ("developer", "viewer"):
        r = client.post(f"{API}/users", headers=admin, json={
            "email": f"{name}@example.com", "username": name, "password": "Passw0rd!", "role_id": roles[name]})
        assert r.status_code == 201, r.text
    viewer, dev = login(client, "viewer", "Passw0rd!"), login(client, "developer", "Passw0rd!")
    assert client.get(f"{API}/flags", headers=viewer).status_code == 200
    assert client.post(f"{API}/flags", headers=viewer, json={"key": "x1", "name": "X1"}).status_code == 403
    assert client.get(f"{API}/users", headers=dev).status_code == 403
    envs = client.get(f"{API}/environments", headers=dev).json()
    assert all(e["sdk_key"] is None for e in envs)


def test_flag_lifecycle_rollout_rollback_and_sdk(client):
    admin, dev = login(client), login(client, "developer", "Passw0rd!")
    flag = client.post(f"{API}/flags", headers=dev, json={"key": "beta-ui", "name": "Beta UI"}).json()
    assert len(flag["rollouts"]) == 3 and not any(r["enabled"] for r in flag["rollouts"])
    ro = {r["environment_key"]: r for r in flag["rollouts"]}

    # developers cannot touch production, but can use development
    assert client.put(f"{API}/rollouts/{ro['production']['id']}", headers=dev, json={"enabled": True}).status_code == 403
    dev_id = ro["development"]["id"]
    assert client.put(f"{API}/rollouts/{dev_id}", headers=dev, json={"enabled": True, "rollout_percentage": 50}).status_code == 200

    sdk_key = next(e["sdk_key"] for e in client.get(f"{API}/environments", headers=admin).json() if e["key"] == "development")
    sdk = {"X-SDK-Key": sdk_key}
    results = [client.post(f"{API}/sdk/evaluate", headers=sdk, json={"flag_key": "beta-ui", "user_id": f"u{i}"}).json()["enabled"]
               for i in range(200)]
    assert 60 < sum(results) < 140  # roughly 50%
    again = [client.post(f"{API}/sdk/evaluate", headers=sdk, json={"flag_key": "beta-ui", "user_id": f"u{i}"}).json()["enabled"]
             for i in range(200)]
    assert results == again  # sticky bucketing

    # user-specific access
    out = next(f"u{i}" for i, v in enumerate(results) if not v)
    inn = next(f"u{i}" for i, v in enumerate(results) if v)
    env_id = ro["development"]["environment_id"]
    client.post(f"{API}/flags/{flag['id']}/assignments", headers=dev, json={"environment_id": env_id, "user_identifier": out, "access": "allow"})
    client.post(f"{API}/flags/{flag['id']}/assignments", headers=dev, json={"environment_id": env_id, "user_identifier": inn, "access": "deny"})
    ev = lambda u: client.post(f"{API}/sdk/evaluate", headers=sdk, json={"flag_key": "beta-ui", "user_id": u}).json()
    assert ev(out)["reason"] == "user_allowed" and ev(inn)["reason"] == "user_denied"

    # rollback restores the previous state
    client.put(f"{API}/rollouts/{dev_id}", headers=dev, json={"rollout_percentage": 100})
    r = client.post(f"{API}/rollouts/{dev_id}/rollback", headers=dev, json={})
    assert r.status_code == 200 and r.json()["rollout_percentage"] == 50
    actions = [h["action"] for h in client.get(f"{API}/flags/{flag['id']}/history", headers=dev).json()]
    assert "rollback" in actions and "create_flag" in actions

    # invalid SDK key
    assert client.post(f"{API}/sdk/evaluate", headers={"X-SDK-Key": "nope"}, json={"flag_key": "beta-ui"}).status_code == 401

    # analytics counted the evaluations
    u = client.get(f"{API}/analytics/usage?flag_id={flag['id']}", headers=dev).json()
    assert u["total_evaluations"] >= 400
    d = client.get(f"{API}/analytics/dashboard", headers=dev).json()
    assert d["totals"]["flags"] >= 4 and len(d["environments"]) == 3


def test_scheduled_activation(client):
    admin = login(client)
    flag = client.post(f"{API}/flags", headers=admin, json={"key": "timed", "name": "Timed"}).json()
    rid = flag["rollouts"][0]["id"]
    past = (utcnow() - timedelta(minutes=1)).isoformat() + "Z"
    bad = client.put(f"{API}/rollouts/{rid}", headers=admin, json={
        "scheduled_enable_at": "2030-01-02T00:00:00Z", "scheduled_disable_at": "2030-01-01T00:00:00Z"})
    assert bad.status_code == 422
    assert client.put(f"{API}/rollouts/{rid}", headers=admin, json={"scheduled_enable_at": past}).status_code == 200
    with SessionLocal() as db:
        assert apply_due_schedules(db) == 1
    got = client.get(f"{API}/flags/{flag['id']}", headers=admin).json()["rollouts"][0]
    assert got["enabled"] is True and got["scheduled_enable_at"] is None
    actions = [h["action"] for h in client.get(f"{API}/audit-logs?flag_id={flag['id']}", headers=admin).json()["items"]]
    assert "scheduled_activation" in actions
