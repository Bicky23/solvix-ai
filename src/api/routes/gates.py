"""
Gate evaluation API endpoint.

POST /evaluate-gates - Evaluate gates before allowing a collection action.

Security:
- Rate limited: 30 requests/minute per IP (less expensive than generation)
"""

import logging

from fastapi import APIRouter, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.api.errors import ErrorResponse
from src.api.models.requests import EvaluateGatesRequest
from src.api.models.responses import EvaluateGatesResponse
from src.engine.gate_evaluator import gate_evaluator

logger = logging.getLogger(__name__)
router = APIRouter()

# Rate limiter (uses app.state.limiter from main.py)
limiter = Limiter(key_func=get_remote_address)


@router.post(
    "/evaluate-gates",
    response_model=EvaluateGatesResponse,
    responses={
        429: {"description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "LLM or internal error"},
        503: {"model": ErrorResponse, "description": "LLM provider unavailable"},
    },
)
@limiter.limit("30/minute")
async def evaluate_gates(
    request: Request, gates_request: EvaluateGatesRequest
) -> EvaluateGatesResponse:
    """
    Evaluate gates before allowing a collection action.

    Returns whether action is allowed and individual gate results.
    """
    logger.info(f"Evaluating gates for action: {gates_request.proposed_action}")
    result = await gate_evaluator.evaluate(gates_request)
    logger.info(f"Gates evaluation: allowed={result.allowed}")
    return result
