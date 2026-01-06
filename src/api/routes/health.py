"""
Health check API endpoint.

GET /health - Check service health and configuration.
"""
from fastapi import APIRouter

from src.api.models.responses import HealthResponse
from src.config.settings import settings

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        version="0.1.0",
        model=settings.openai_model
    )
