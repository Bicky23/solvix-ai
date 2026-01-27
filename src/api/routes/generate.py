"""
Draft generation API endpoint.

POST /generate-draft - Generate a collection email draft.

Security:
- Rate limited: configurable via settings (default 100/minute for internal service calls)
"""

import logging

from fastapi import APIRouter, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.api.errors import ErrorResponse
from src.api.models.requests import GenerateDraftRequest
from src.api.models.responses import GenerateDraftResponse
from src.config.settings import settings
from src.engine.generator import generator

logger = logging.getLogger(__name__)
router = APIRouter()

# Rate limiter (uses app.state.limiter from main.py)
limiter = Limiter(key_func=get_remote_address)


@router.post(
    "/generate-draft",
    response_model=GenerateDraftResponse,
    responses={
        429: {"description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "LLM or internal error"},
        503: {"model": ErrorResponse, "description": "LLM provider unavailable"},
    },
)
@limiter.limit(settings.rate_limit_generate)
async def generate_draft(
    request: Request, generate_request: GenerateDraftRequest
) -> GenerateDraftResponse:
    """
    Generate a collection email draft.

    Returns subject, body, and metadata about the generated draft.
    """
    logger.info(f"Generating draft for party: {generate_request.context.party.party_id}")
    result = await generator.generate(generate_request)
    logger.info(f"Generated draft with tone: {result.tone_used}")
    return result
