"""
Robust JSON extraction from LLM responses.

Handles common issues:
- Markdown code blocks (```json ... ```)
- Extra text before/after JSON
- Truncated responses (most common with local models)
- Non-standard formatting
- Think/reasoning blocks wrapping JSON
"""

import json
import re
import logging

logger = logging.getLogger(__name__)


def _strip_thinking_blocks(content: str) -> str:
    """Remove <think>...</think> blocks that some models emit."""
    return re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()


def _extract_from_markdown(content: str) -> str | None:
    """Extract content from markdown code blocks."""
    # Match ```json ... ``` or ``` ... ```
    pattern = r'```(?:json|JSON)?\s*\n?(.*?)```'
    matches = re.findall(pattern, content, re.DOTALL)
    for match in matches:
        cleaned = match.strip()
        if cleaned.startswith('{') or cleaned.startswith('['):
            return cleaned
    
    # Fallback: manual split approach for cases where closing ``` is missing (truncated)
    markers = ['```json\n', '```json\r\n', '```JSON\n', '```\n']
    for marker in markers:
        idx = content.find(marker)
        if idx != -1:
            after = content[idx + len(marker):]
            # Find the closing ``` if present
            end_idx = after.find('```')
            if end_idx != -1:
                return after[:end_idx].strip()
            else:
                # No closing ``` — truncated response, return everything after marker
                return after.strip()
    
    return None


def _repair_truncated_json(text: str) -> dict | None:
    """
    Attempt to repair truncated JSON by:
    1. Removing incomplete trailing values
    2. Closing all open brackets/braces
    """
    if not text or not text.strip().startswith('{'):
        return None
    
    text = text.strip()
    
    # Remove everything after the last complete value
    # Strategy: progressively trim from the end until we can close brackets
    
    # First, try to find a clean truncation point
    # Remove trailing incomplete string (unclosed quote)
    # Count quotes — if odd, we have an unclosed string
    in_string = False
    escape_next = False
    last_safe_pos = 0
    
    for i, ch in enumerate(text):
        if escape_next:
            escape_next = False
            continue
        if ch == '\\' and in_string:
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            if not in_string:
                # Just closed a string — this is a safe position
                last_safe_pos = i + 1
        elif not in_string:
            if ch in '{}[]:,':
                last_safe_pos = i + 1
    
    # If we ended inside a string, truncate to last safe position
    if in_string and last_safe_pos > 0:
        text = text[:last_safe_pos]
    
    # Now remove trailing incomplete elements
    # Remove trailing comma
    text = re.sub(r',\s*$', '', text)
    # Remove trailing colon with no value
    text = re.sub(r':\s*$', ': null', text)
    # Remove trailing key without value (e.g., "key_name after last comma)
    text = re.sub(r',\s*"[^"]*"\s*$', '', text)
    # Remove incomplete key-value pair at end
    text = re.sub(r',\s*"[^"]*"\s*:\s*$', '', text)
    
    # Count unclosed braces and brackets
    open_braces = text.count('{') - text.count('}')
    open_brackets = text.count('[') - text.count(']')
    
    if open_braces < 0 or open_brackets < 0:
        return None  # More closing than opening — malformed
    
    # Close arrays first, then objects
    text += ']' * open_brackets + '}' * open_braces
    
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # More aggressive repair: try trimming back further
    # Find the last successfully parseable prefix
    for trim_chars in [50, 100, 200, 500, 1000]:
        if len(text) <= trim_chars:
            break
        trimmed = text[:-(trim_chars)]
        # Remove trailing incomplete elements
        trimmed = re.sub(r',\s*"[^"]*"?\s*:?\s*"?[^"]*$', '', trimmed)
        trimmed = re.sub(r',\s*$', '', trimmed)
        
        open_braces = trimmed.count('{') - trimmed.count('}')
        open_brackets = trimmed.count('[') - trimmed.count(']')
        
        if open_braces >= 0 and open_brackets >= 0:
            trimmed += ']' * open_brackets + '}' * open_braces
            try:
                return json.loads(trimmed)
            except json.JSONDecodeError:
                continue
    
    return None


def extract_json_from_llm(content: str) -> dict | None:
    """
    Extract a JSON object from an LLM response string.
    
    Handles all common LLM output patterns:
    - Clean JSON
    - ```json ... ``` wrapped
    - <think>...</think> blocks before JSON
    - Truncated JSON (most common failure with local models)
    - Extra text before/after JSON
    
    Returns the parsed dict or None if extraction fails.
    """
    if not content:
        return None

    content = content.strip()
    
    # Pre-process: remove thinking blocks
    content = _strip_thinking_blocks(content)
    if not content:
        return None

    # Strategy 1: Direct parse (content is already clean JSON)
    try:
        result = json.loads(content)
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        pass

    # Strategy 2: Extract from markdown code blocks
    extracted = _extract_from_markdown(content)
    if extracted:
        try:
            result = json.loads(extracted)
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            # The extracted content is truncated JSON — try repair
            repaired = _repair_truncated_json(extracted)
            if repaired:
                return repaired

    # Strategy 3: Find JSON object between first { and last }
    first_brace = content.find("{")
    last_brace = content.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        candidate = content[first_brace:last_brace + 1]
        try:
            result = json.loads(candidate)
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass

    # Strategy 4: Repair truncated JSON (no closing brace found, or parse failed)
    if first_brace != -1:
        candidate = content[first_brace:]
        repaired = _repair_truncated_json(candidate)
        if repaired:
            return repaired

    logger.warning(f"Failed to extract JSON from LLM response (length={len(content)}): {content[:300]}...")
    return None
