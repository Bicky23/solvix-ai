"""
Robust JSON extraction from LLM responses.

LLMs can return JSON in various formats:
- Clean JSON
- Markdown code blocks (```json ... ```)
- With extra text before/after
- With Unicode characters or BOM
- With trailing commas (invalid JSON but common)

This module handles all these cases.
"""

import json
import logging
import re
from typing import Any, Dict

logger = logging.getLogger(__name__)


class JSONExtractionError(Exception):
    """Raised when JSON extraction fails after all attempts."""

    def __init__(self, message: str, raw_content: str, attempts: list):
        super().__init__(message)
        self.raw_content = raw_content
        self.attempts = attempts


def extract_json(content: str) -> Dict[str, Any]:
    """
    Extract JSON from LLM response content.

    Tries multiple strategies in order:
    1. Direct parse (for clean JSON responses)
    2. Strip markdown code blocks
    3. Find JSON object/array in content
    4. Clean and retry (trailing commas, etc.)

    Args:
        content: Raw LLM response content

    Returns:
        Parsed JSON as dictionary

    Raises:
        JSONExtractionError: If all extraction attempts fail
    """
    if not content or not content.strip():
        raise JSONExtractionError(
            message="Empty content received from LLM",
            raw_content=content,
            attempts=["Content was empty or whitespace only"],
        )

    attempts = []

    # Strategy 1: Direct parse
    try:
        result = json.loads(content)
        if isinstance(result, dict):
            return result
        attempts.append(f"Direct parse returned {type(result).__name__}, not dict")
    except json.JSONDecodeError as e:
        attempts.append(f"Direct parse failed: {e}")

    # Strategy 2: Strip markdown code blocks
    stripped = _strip_markdown_code_blocks(content)
    if stripped != content:
        try:
            result = json.loads(stripped)
            if isinstance(result, dict):
                logger.debug("JSON extracted after stripping markdown code blocks")
                return result
            attempts.append(f"Stripped parse returned {type(result).__name__}, not dict")
        except json.JSONDecodeError as e:
            attempts.append(f"Stripped markdown parse failed: {e}")

    # Strategy 3: Find JSON object in content
    extracted = _find_json_object(content)
    if extracted:
        try:
            result = json.loads(extracted)
            if isinstance(result, dict):
                logger.debug("JSON extracted using regex object finder")
                return result
            attempts.append(f"Regex extracted parse returned {type(result).__name__}, not dict")
        except json.JSONDecodeError as e:
            attempts.append(f"Regex extraction parse failed: {e}")

    # Strategy 4: Clean content (trailing commas, etc.) and retry
    cleaned = _clean_json_content(stripped if stripped != content else content)
    if cleaned != content and cleaned != stripped:
        try:
            result = json.loads(cleaned)
            if isinstance(result, dict):
                logger.debug("JSON extracted after cleaning content")
                return result
            attempts.append(f"Cleaned parse returned {type(result).__name__}, not dict")
        except json.JSONDecodeError as e:
            attempts.append(f"Cleaned content parse failed: {e}")

    # All strategies failed
    logger.error(
        f"Failed to extract JSON after {len(attempts)} attempts. "
        f"Content preview: {content[:200]}..."
    )
    raise JSONExtractionError(
        message="Failed to parse JSON from LLM response after all extraction attempts",
        raw_content=content,
        attempts=attempts,
    )


def _strip_markdown_code_blocks(content: str) -> str:
    """
    Strip markdown code block markers from content.

    Handles:
    - ```json ... ```
    - ```JSON ... ```
    - ``` ... ```
    - Triple backticks with newlines
    """
    # Remove BOM if present
    content = content.lstrip("\ufeff")

    # Pattern for code blocks with optional language specifier
    # Matches: ```json, ```JSON, ```, etc.
    pattern = r"^```(?:json|JSON|javascript|JS)?\s*\n?(.*?)\n?```\s*$"
    match = re.match(pattern, content.strip(), re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # Try simpler pattern - just remove backticks at start/end
    stripped = content.strip()
    if stripped.startswith("```"):
        # Find first newline after opening backticks
        first_newline = stripped.find("\n")
        if first_newline != -1:
            stripped = stripped[first_newline + 1 :]

    if stripped.endswith("```"):
        # Find last occurrence and remove
        last_backticks = stripped.rfind("```")
        if last_backticks != -1:
            stripped = stripped[:last_backticks]

    return stripped.strip()


def _find_json_object(content: str) -> str | None:
    """
    Find a JSON object in content using brace matching.

    This is more reliable than regex for nested objects.
    """
    # Find first { that starts a JSON object
    start = -1
    for i, char in enumerate(content):
        if char == "{":
            start = i
            break

    if start == -1:
        return None

    # Match braces to find the end
    depth = 0
    in_string = False
    escape_next = False
    end = -1

    for i in range(start, len(content)):
        char = content[i]

        if escape_next:
            escape_next = False
            continue

        if char == "\\":
            escape_next = True
            continue

        if char == '"' and not escape_next:
            in_string = not in_string
            continue

        if in_string:
            continue

        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                end = i
                break

    if end == -1:
        return None

    return content[start : end + 1]


def _clean_json_content(content: str) -> str:
    """
    Clean common JSON issues from LLM responses.

    Fixes:
    - Trailing commas before } or ]
    - Single quotes instead of double quotes (risky, only for simple cases)
    """
    # Remove trailing commas before closing braces/brackets
    # This is a common LLM mistake
    content = re.sub(r",\s*([}\]])", r"\1", content)

    return content
