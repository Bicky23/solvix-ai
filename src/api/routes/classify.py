"""
Email classification API endpoint.

POST /classify - Classify an inbound email from a debtor.

Security:
- Rate limited: 20 requests/minute per IP (prevents abuse)
"""

import logging

from fastapi import APIRouter, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.api.errors import ErrorResponse
from src.api.models.requests import ClassifyRequest
from src.api.models.responses import ClassifyResponse
from src.engine.classifier import classifier

logger = logging.getLogger(__name__)
router = APIRouter()

# Rate limiter (uses app.state.limiter from main.py)
limiter = Limiter(key_func=get_remote_address)


@router.post(
    "/classify",
    response_model=ClassifyResponse,
    responses={
        429: {"description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "LLM or internal error"},
        503: {"model": ErrorResponse, "description": "LLM provider unavailable"},
    },
)
@limiter.limit("20/minute")
async def classify_email(request: Request, classify_request: ClassifyRequest) -> ClassifyResponse:
    """
    Classify an inbound email from a debtor.

    Returns classification (COOPERATIVE, PROMISE, DISPUTE, etc.),
    confidence score, and any extracted data.
    """
    logger.info(f"Classifying email for party: {classify_request.context.party.party_id}")
    result = await classifier.classify(classify_request)
    logger.info(f"Classification: {result.classification} ({result.confidence:.2f})")
    return result
