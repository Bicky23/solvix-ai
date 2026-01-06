"""
Draft generation API endpoint.

POST /generate-draft - Generate a collection email draft.
"""
import logging
from fastapi import APIRouter, HTTPException

from src.api.models.requests import GenerateDraftRequest
from src.api.models.responses import GenerateDraftResponse
from src.engine.generator import generator

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/generate-draft", response_model=GenerateDraftResponse)
async def generate_draft(request: GenerateDraftRequest) -> GenerateDraftResponse:
    """
    Generate a collection email draft.
    
    Returns subject, body, and metadata about the generated draft.
    """
    try:
        logger.info(f"Generating draft for party: {request.context.party.party_id}")
        result = generator.generate(request)
        logger.info(f"Generated draft with tone: {result.tone_used}")
        return result
    except Exception as e:
        logger.error(f"Draft generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
