import json
import re


def parse_llm_json(text: str) -> dict:
    """Robustly extract a JSON object from an LLM response.

    Handles:
    - ```json ... ``` code fences (Claude's default)
    - ``` ... ``` without language tag
    - Raw JSON with no fencing
    - Prose before/after the JSON block
    """
    # 1. Try ```json ... ``` fence
    m = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if m:
        return json.loads(m.group(1))

    # 2. Try ``` ... ``` fence (no language tag)
    m = re.search(r"```\s*(.*?)\s*```", text, re.DOTALL)
    if m:
        candidate = m.group(1).strip()
        if candidate.startswith("{"):
            return json.loads(candidate)

    # 3. Extract the outermost { ... } block
    start = text.find("{")
    if start != -1:
        depth = 0
        for i, ch in enumerate(text[start:], start):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return json.loads(text[start:i + 1])

    # 4. Last resort: try the whole string
    return json.loads(text)
