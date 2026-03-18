import asyncio
from datetime import datetime, timezone

from app.core.enums import RequestStatus
from app.core.schemas import RequestPayload
from app.core.store import store
from app.services.handlers import primary_handler, optional_handler
from app.services.retry_engine import retry_with_backoff
from app.observability.metrics import metrics
from app.core.config import (
    PRIMARY_TIMEOUT, PRIMARY_MAX_ATTEMPTS, PRIMARY_BASE_DELAY, PRIMARY_MAX_DELAY,
    OPTIONAL_TIMEOUT, OPTIONAL_MAX_ATTEMPTS, OPTIONAL_BASE_DELAY, OPTIONAL_MAX_DELAY,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize(result: object) -> dict:
    if isinstance(result, Exception):
        error = f"{type(result).__name__}: {result}"
        return {
            "success": False,
            "result": None,
            "attempts": [],
            "last_error": error,
            "total_latency_s": 0.0,
        }
    return result


async def process_request(request_id: str, payload: RequestPayload) -> None:
    await metrics.inc_total()

    await store.update(request_id, {
        "status": RequestStatus.RUNNING,
        "started_at": _now(),
    })

    primary_result, optional_result = await asyncio.gather(
        retry_with_backoff(
            primary_handler, payload,
            max_attempts=PRIMARY_MAX_ATTEMPTS,
            timeout=PRIMARY_TIMEOUT,
            base_delay=PRIMARY_BASE_DELAY,
            max_delay=PRIMARY_MAX_DELAY,
        ),
        retry_with_backoff(
            optional_handler, payload,
            max_attempts=OPTIONAL_MAX_ATTEMPTS,
            timeout=OPTIONAL_TIMEOUT,
            base_delay=OPTIONAL_BASE_DELAY,
            max_delay=OPTIONAL_MAX_DELAY,
        ),
        return_exceptions=True,
    )

    primary_result = _normalize(primary_result)
    optional_result = _normalize(optional_result)

    # Update per-handler metrics
    if primary_result["success"]:
        await metrics.primary.record_success(primary_result["total_latency_s"])
    else:
        await metrics.primary.record_failure(primary_result["total_latency_s"])

    if optional_result["success"]:
        await metrics.optional.record_success(optional_result["total_latency_s"])
    else:
        await metrics.optional.record_failure(optional_result["total_latency_s"])

    # Determine final status
    finished_at = _now()

    if not primary_result["success"]:
        await metrics.inc_failed()
        await store.update(request_id, {
            "status": RequestStatus.FAILED,
            "degraded": False,
            "degradation_reason": None,
            "finished_at": finished_at,
            "handlers": {
                "primary": primary_result,
                "optional": optional_result,
            },
        })
        return

    degraded = not optional_result["success"]
    if degraded:
        await metrics.inc_degraded()
        degradation_reason = f"optional handler failed: {optional_result['last_error']}"
    else:
        degradation_reason = None

    await store.update(request_id, {
        "status": RequestStatus.COMPLETED,
        "degraded": degraded,
        "degradation_reason": degradation_reason,
        "finished_at": finished_at,
        "handlers": {
            "primary": primary_result,
            "optional": optional_result,
        },
    })
