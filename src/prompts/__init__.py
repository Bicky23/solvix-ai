"""Prompt templates for AI operations."""

from .classification import CLASSIFY_EMAIL_SYSTEM, CLASSIFY_EMAIL_USER
from .draft_generation import GENERATE_DRAFT_SYSTEM, GENERATE_DRAFT_USER

__all__ = [
    "CLASSIFY_EMAIL_SYSTEM",
    "CLASSIFY_EMAIL_USER",
    "GENERATE_DRAFT_SYSTEM",
    "GENERATE_DRAFT_USER",
]
