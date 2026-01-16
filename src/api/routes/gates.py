"""
Gate evaluation API endpoint.

POST /evaluate-gates - Evaluate gates before allowing a collection action.
"""
import logging

from fastapi import APIRouter, HTTPException

from src.api.models.requests import EvaluateGatesRequest
from src.api.models.responses import EvaluateGatesResponse
from src.engine.gate_evaluator import gate_evaluator

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/evaluate-gates", response_model=EvaluateGatesResponse)
async def evaluate_gates(request: EvaluateGatesRequest) -> EvaluateGatesResponse:
    """
    Evaluate gates before allowing a collection action.

    Returns whether action is allowed and individual gate results.
    """
    try:
        logger.info(f"Evaluating gates for action: {request.proposed_action}")
        result = gate_evaluator.evaluate(request)
        logger.info(f"Gates evaluation: allowed={result.allowed}")
        return result
    except Exception as e:
        logger.error(f"Gate evaluation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
