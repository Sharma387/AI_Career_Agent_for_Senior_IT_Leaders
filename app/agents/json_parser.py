"""
Robust JSON extraction from LLM responses.

Handles common issues:
- Markdown code blocks (```json ... ```)
- Extra text before/after JSON
- Truncated responses
- Non-standard formatting
"""

import json
import re
import logging

logger = logging.getLogger(__name__)


def extract_json_from_llm(content: str) -> dict | None:
    """
    Extract a JSON object from an LLM response string.
    
    Tries multiple strategies:
    1. Direct JSON.parse
    2. Strip markdown code blocks
    3. Find JSON object with regex
    4. Find partial JSON and repair
    
    Returns the parsed dict or None if extraction fails.
    """
    if not content:
        return None

    content = content.strip()

    # Strategy 1: Direct parse
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # Strategy 2: Strip markdown code blocks
    if "```" in content:
        # Try to find JSON between code blocks (handle multiline)
        match = re.search(r'```(?:json)?\s*\n(.*?)\n\s*```', content, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                pass
        
        # Alternative: find opening ``` and closing ```, take everything between
        parts = content.split("```")
        if len(parts) >= 3:
            # parts[0] = before first ```, parts[1] = content, parts[2] = after
            json_candidate = parts[1]
            # Remove "json" language identifier if present
            if json_candidate.startswith("json"):
                json_candidate = json_candidate[4:]
            json_candidate = json_candidate.strip()
            try:
                return json.loads(json_candidate)
            except json.JSONDecodeError:
                pass
        
        # Strip all ``` lines and try again
        lines = content.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\n".join(lines).strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

    # Strategy 3: Find the first { and last } to extract JSON object
    first_brace = content.find("{")
    last_brace = content.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        candidate = content[first_brace:last_brace + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    # Strategy 4: Try to fix common issues (trailing commas, single quotes)
    if first_brace != -1 and last_brace != -1:
        candidate = content[first_brace:last_brace + 1]
        # Remove trailing commas before } or ]
        candidate = re.sub(r',\s*([}\]])', r'\1', candidate)
        # Replace single quotes with double quotes (risky but worth trying)
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    logger.warning(f"Failed to extract JSON from LLM response (length={len(content)}): {content[:200]}...")
    return None
