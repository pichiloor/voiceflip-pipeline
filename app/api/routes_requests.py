import uuid
import asyncio
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from app.core.schemas import RequestPayload
from app.core.enums import RequestStatus
from app.core.store import store
from app.services.orchestrator import process_request

router = APIRouter()


async def _run_process_request(request_id: str, payload: RequestPayload) -> None:
    try:
        await process_request(request_id, payload)
    except Exception as e:
        await store.update(request_id, {
            "status": RequestStatus.FAILED,
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "degraded": False,
            "degradation_reason": None,
            "handlers": {"system_error": {"error": f"{type(e).__name__}: {e}"}},
        })


@router.post("/requests")
async def create_request(payload: RequestPayload) -> dict:
    request_id = str(uuid.uuid4())

    await store.create(request_id, {
        "id": request_id,
        "payload": payload.model_dump(),
        "status": RequestStatus.PENDING,
        "degraded": False,
        "degradation_reason": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "started_at": None,
        "finished_at": None,
        "handlers": {},
    })

    asyncio.create_task(_run_process_request(request_id, payload))

    return {"id": request_id, "status": RequestStatus.PENDING}


@router.get("/requests/{request_id}")
async def get_request(request_id: str) -> dict:
    request = await store.get(request_id)
    if not request:
        raise HTTPException(status_code=404, detail="request not found")
    return request
