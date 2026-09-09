"""
PramaanX — Health Check Endpoint
"""

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str
    pipeline_version: str
    environment: str


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description=(
        "Returns the current health status of the PramaanX backend. "
        "Use this endpoint to verify the server is running before "
        "submitting document verification requests."
    ),
    tags=["Health"],
)
def health_check() -> HealthResponse:
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        version=settings.app_version,
        pipeline_version=settings.pipeline_version,
        environment=settings.environment,
    )
