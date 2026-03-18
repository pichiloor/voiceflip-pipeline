from fastapi import APIRouter
from app.observability.metrics import metrics

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    data = await metrics.snapshot()
    return {"status": "ok", **data}
