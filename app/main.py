from fastapi import FastAPI
from app.api.routes_requests import router as requests_router
from app.api.routes_health import router as health_router

app = FastAPI(title="VoiceFlip Pipeline")

app.include_router(requests_router)
app.include_router(health_router)
