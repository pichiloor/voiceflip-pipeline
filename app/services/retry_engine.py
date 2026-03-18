import asyncio
import random
import time


def is_retryable_error(exc: Exception) -> bool:
    return isinstance(exc, (asyncio.TimeoutError, ConnectionError, ConnectionRefusedError))


def _format_error(exc: Exception) -> str:
    msg = str(exc)
    return type(exc).__name__ if not msg else f"{type(exc).__name__}: {msg}"


async def retry_with_backoff(
    func,
    payload,
    max_attempts: int = 3,
    timeout: float = 5.0,
    base_delay: float = 0.5,
    max_delay: float = 10.0,
) -> dict:
    attempts = []
    delay = 0.0
    wall_start = time.monotonic()

    for attempt_num in range(1, max_attempts + 1):
        start = time.monotonic()
        try:
            result = await asyncio.wait_for(
                func(payload, attempt_num), timeout=timeout
            )
            latency = round(time.monotonic() - start, 3)
            attempts.append({
                "attempt": attempt_num,
                "delay_applied": round(delay, 3),
                "error": None,
                "latency_s": latency,
            })
            return {
                "success": True,
                "result": result,
                "attempts": attempts,
                "total_latency_s": round(time.monotonic() - wall_start, 3),
            }

        except Exception as e:
            latency = round(time.monotonic() - start, 3)
            attempts.append({
                "attempt": attempt_num,
                "delay_applied": round(delay, 3),
                "error": _format_error(e),
                "latency_s": latency,
            })
            if not is_retryable_error(e):
                return {
                    "success": False,
                    "result": None,
                    "attempts": attempts,
                    "last_error": _format_error(e),
                    "total_latency_s": round(time.monotonic() - wall_start, 3),
                }

        if attempt_num < max_attempts:
            delay = min(
                base_delay * (2 ** (attempt_num - 1)) + random.uniform(0, 1.0),
                max_delay,
            )
            await asyncio.sleep(delay)

    last_error = attempts[-1]["error"] if attempts else "unknown"
    return {
        "success": False,
        "result": None,
        "attempts": attempts,
        "last_error": last_error,
        "total_latency_s": round(time.monotonic() - wall_start, 3),
    }
