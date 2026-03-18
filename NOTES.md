# Implementation Notes

## Python version

This project uses Python 3.14, the latest stable release. It provides native `asyncio` support, modern type hint syntax (`X | Y`), and `asyncio.Lock` — all used in this project.

## Why asyncio instead of Celery

`asyncio` runs both handlers in parallel inside a single process. No external broker, no Redis, no extra setup. `asyncio.create_task()` lets the POST endpoint return immediately while the work continues in the background.

Celery would make sense if we needed workers across multiple machines or a persistent job queue.

## Retry, backoff, and jitter

When a handler fails with a connection or timeout error, it retries. The wait time between retries grows exponentially (0.5s, 1s, 2s...) and has a small random offset (jitter) to avoid many requests retrying at the same time. There is also a maximum cap of 10s per wait.

Other errors (like `ValueError`) are not retried — they indicate a logic problem, not a temporary failure.

## Trade offs

- **State is lost on restart.** Everything is in memory. A real system would use a database.
- **Cannot run multiple instances.** Each process has its own memory, so requests created in one instance are not visible in another.
- **No queue limit.** If many requests arrive at once, they all run concurrently with no throttling. A real system would cap this.
- **Single threaded.** asyncio works well when handlers wait on I/O (network calls, etc.). For CPU-heavy work, it would not be the right choice.
