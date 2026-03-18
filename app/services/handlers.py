from app.core.schemas import RequestPayload
from app.services.scenarios import execute_scenario


async def primary_handler(payload: RequestPayload, attempt: int = 1) -> dict:
    return await execute_scenario(payload.scenario, attempt)


async def optional_handler(payload: RequestPayload, attempt: int = 1) -> dict:
    return await execute_scenario(payload.optional_scenario, attempt)
