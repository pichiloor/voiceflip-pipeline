import asyncio
import pytest
from app.services.retry_engine import retry_with_backoff


class MockPayload:
    pass


async def test_success_first_attempt():
    """Handler succeeds immediately -> 1 attempt, success=True."""
    async def always_ok(payload, attempt):
        return {"message": "ok"}

    result = await retry_with_backoff(always_ok, MockPayload(), max_attempts=3, timeout=1.0)

    assert result["success"] is True
    assert len(result["attempts"]) == 1
    assert result["attempts"][0]["error"] is None


async def test_non_retryable_fails_immediately():
    """Non-retryable exception (ValueError) -> 1 attempt, no retries."""
    async def hard_fail(payload, attempt):
        raise ValueError("permanent error")

    result = await retry_with_backoff(hard_fail, MockPayload(), max_attempts=3, timeout=1.0)

    assert result["success"] is False
    assert len(result["attempts"]) == 1
    assert "ValueError" in result["attempts"][0]["error"]


async def test_retryable_exhausts_all_attempts():
    """ConnectionError is retryable -> exhausts max_attempts."""
    async def always_fails(payload, attempt):
        raise ConnectionError("connection refused")

    result = await retry_with_backoff(
        always_fails, MockPayload(),
        max_attempts=3, timeout=1.0,
        base_delay=0.01, max_delay=0.05,
    )

    assert result["success"] is False
    assert len(result["attempts"]) == 3
    assert all("ConnectionError" in a["error"] for a in result["attempts"])


async def test_transient_then_success():
    """Fails first 2 attempts, succeeds on 3rd -> success=True with retry history."""
    async def fail_twice(payload, attempt):
        if attempt < 3:
            raise ConnectionError("temporary")
        return {"message": "recovered"}

    result = await retry_with_backoff(
        fail_twice, MockPayload(),
        max_attempts=3, timeout=1.0,
        base_delay=0.01, max_delay=0.05,
    )

    assert result["success"] is True
    assert len(result["attempts"]) == 3
    assert result["attempts"][0]["error"] is not None
    assert result["attempts"][1]["error"] is not None
    assert result["attempts"][2]["error"] is None


async def test_timeout_retries():
    """Timeout is retryable -> retries up to max_attempts."""
    async def always_timeout(payload, attempt):
        await asyncio.sleep(10)

    result = await retry_with_backoff(
        always_timeout, MockPayload(),
        max_attempts=2, timeout=0.05,
        base_delay=0.01, max_delay=0.05,
    )

    assert result["success"] is False
    assert len(result["attempts"]) == 2
    assert all(a["error"] == "TimeoutError" for a in result["attempts"])


async def test_last_error_included_in_result():
    """Failed result includes last_error at top level."""
    async def always_fails(payload, attempt):
        raise ConnectionError("fail")

    result = await retry_with_backoff(
        always_fails, MockPayload(),
        max_attempts=2, timeout=1.0,
        base_delay=0.01, max_delay=0.05,
    )

    assert "last_error" in result
    assert result["last_error"] is not None
    assert "ConnectionError" in result["last_error"]


async def test_first_attempt_has_no_delay():
    """First attempt has no delay, subsequent ones do."""
    async def always_fails(payload, attempt):
        raise ConnectionError("fail")

    result = await retry_with_backoff(
        always_fails, MockPayload(),
        max_attempts=3, timeout=1.0,
        base_delay=0.01, max_delay=0.05,
    )

    assert result["attempts"][0]["delay_applied"] == 0.0
    assert result["attempts"][1]["delay_applied"] > 0.0
