import asyncio


class InMemoryRequestStore:
    def __init__(self):
        self._data: dict = {}
        self._lock = asyncio.Lock()

    async def create(self, request_id: str, data: dict) -> None:
        async with self._lock:
            self._data[request_id] = data

    async def update(self, request_id: str, updates: dict) -> None:
        async with self._lock:
            if request_id not in self._data:
                raise KeyError(f"request {request_id!r} not found in store")
            self._data[request_id].update(updates)

    async def get(self, request_id: str) -> dict | None:
        async with self._lock:
            return self._data.get(request_id)

    async def clear(self) -> None:
        async with self._lock:
            self._data.clear()


store = InMemoryRequestStore()
