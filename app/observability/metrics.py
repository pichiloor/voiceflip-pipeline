import asyncio


class HandlerMetrics:
    def __init__(self):
        self.successes: int = 0
        self.failures: int = 0
        self.total_latency: float = 0.0
        self.samples: int = 0
        self._lock = asyncio.Lock()

    async def record_success(self, latency: float) -> None:
        async with self._lock:
            self.successes += 1
            self.total_latency += latency
            self.samples += 1

    async def record_failure(self, latency: float) -> None:
        async with self._lock:
            self.failures += 1
            self.total_latency += latency
            self.samples += 1

    async def reset(self) -> None:
        async with self._lock:
            self.successes = 0
            self.failures = 0
            self.total_latency = 0.0
            self.samples = 0

    @property
    def avg_latency(self) -> float:
        if not self.samples:
            return 0.0
        return round(self.total_latency / self.samples, 3)


class Metrics:
    def __init__(self):
        self.total_requests: int = 0
        self.failed_requests: int = 0
        self.degraded_requests: int = 0
        self.primary = HandlerMetrics()
        self.optional = HandlerMetrics()
        self._lock = asyncio.Lock()

    async def inc_total(self) -> None:
        async with self._lock:
            self.total_requests += 1

    async def inc_failed(self) -> None:
        async with self._lock:
            self.failed_requests += 1

    async def inc_degraded(self) -> None:
        async with self._lock:
            self.degraded_requests += 1

    async def reset(self) -> None:
        async with self._lock:
            self.total_requests = 0
            self.failed_requests = 0
            self.degraded_requests = 0
        await self.primary.reset()
        await self.optional.reset()

    async def snapshot(self) -> dict:
        async with self._lock:
            return {
                "total_requests": self.total_requests,
                "failed_requests": self.failed_requests,
                "degraded_requests": self.degraded_requests,
                "handlers": {
                    "primary": {
                        "successes": self.primary.successes,
                        "failures": self.primary.failures,
                        "avg_latency_s": self.primary.avg_latency,
                    },
                    "optional": {
                        "successes": self.optional.successes,
                        "failures": self.optional.failures,
                        "avg_latency_s": self.optional.avg_latency,
                    },
                },
            }


metrics = Metrics()
