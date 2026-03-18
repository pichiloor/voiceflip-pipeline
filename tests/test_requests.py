import asyncio
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.store import store
from app.observability.metrics import metrics


@pytest.fixture(autouse=True)
async def reset_state():
    await store.clear()
    await metrics.reset()


async def poll_until_done(client, request_id, timeout=15):
    for _ in range(timeout * 10):
        r = await client.get(f"/requests/{request_id}")
        data = r.json()
        if data.get("status") not in ("pending", "running"):
            return data
        await asyncio.sleep(0.1)
    return data


async def test_ok_scenario():
    """Both handlers succeed -> completed, not degraded."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post("/requests", json={"input": "test", "scenario": "ok", "optional_scenario": "ok"})
        assert r.status_code == 200
        assert r.json()["status"] == "pending"
        request_id = r.json()["id"]

        data = await poll_until_done(client, request_id)

        assert data["status"] == "completed"
        assert data["degraded"] is False
        assert data["degradation_reason"] is None
        assert data["handlers"]["primary"]["success"] is True
        assert data["handlers"]["optional"]["success"] is True


async def test_primary_hard_fail():
    """Primary fails with non-retryable error -> request fails immediately."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post("/requests", json={"input": "test", "scenario": "hard_fail", "optional_scenario": "ok"})
        request_id = r.json()["id"]

        data = await poll_until_done(client, request_id)

        assert data["status"] == "failed"
        assert len(data["handlers"]["primary"]["attempts"]) == 1


async def test_optional_fail_degraded():
    """Primary succeeds, optional fails -> completed in degraded mode."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post("/requests", json={"input": "test", "scenario": "ok", "optional_scenario": "hard_fail"})
        request_id = r.json()["id"]

        data = await poll_until_done(client, request_id)

        assert data["status"] == "completed"
        assert data["degraded"] is True
        assert data["degradation_reason"] is not None
        assert data["handlers"]["primary"]["success"] is True
        assert data["handlers"]["optional"]["success"] is False


async def test_transient_fail_then_ok():
    """Primary fails twice then recovers -> completed with retry history."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post("/requests", json={"input": "test", "scenario": "transient_fail_then_ok", "optional_scenario": "ok"})
        request_id = r.json()["id"]

        data = await poll_until_done(client, request_id, timeout=30)

        assert data["status"] == "completed"
        assert data["degraded"] is False
        primary_attempts = data["handlers"]["primary"]["attempts"]
        assert len(primary_attempts) == 3
        assert primary_attempts[0]["error"] is not None
        assert primary_attempts[1]["error"] is not None
        assert primary_attempts[2]["error"] is None


async def test_health_metrics_after_requests():
    """Health endpoint reflects correct counters after processing requests."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # One successful request
        r = await client.post("/requests", json={"input": "test", "scenario": "ok", "optional_scenario": "ok"})
        await poll_until_done(client, r.json()["id"])

        # One degraded request
        r = await client.post("/requests", json={"input": "test", "scenario": "ok", "optional_scenario": "hard_fail"})
        await poll_until_done(client, r.json()["id"])

        # One failed request
        r = await client.post("/requests", json={"input": "test", "scenario": "hard_fail", "optional_scenario": "ok"})
        await poll_until_done(client, r.json()["id"])

        health = await client.get("/health")
        assert health.status_code == 200
        data = health.json()

        assert data["status"] == "ok"
        assert data["total_requests"] == 3
        assert data["failed_requests"] == 1
        assert data["degraded_requests"] == 1
        assert data["handlers"]["primary"]["successes"] == 2
        assert data["handlers"]["primary"]["failures"] == 1
        assert data["handlers"]["optional"]["successes"] == 2
        assert data["handlers"]["optional"]["failures"] == 1


async def test_health_initial_state():
    """GET /health returns 200 with all counters at zero on fresh start."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["total_requests"] == 0
        assert data["failed_requests"] == 0
        assert data["degraded_requests"] == 0
        assert data["handlers"]["primary"]["successes"] == 0
        assert data["handlers"]["primary"]["failures"] == 0
        assert data["handlers"]["optional"]["successes"] == 0
        assert data["handlers"]["optional"]["failures"] == 0


async def test_get_request_not_found():
    """GET /requests/{id} returns 404 for unknown id."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/requests/nonexistent-id")
        assert r.status_code == 404


async def test_invalid_scenario_returns_422():
    """POST /requests with invalid scenario returns 422."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post("/requests", json={"input": "test", "scenario": "invalid_scenario"})
        assert r.status_code == 422
