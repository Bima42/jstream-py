from pydantic_core import from_json


def parse_partial(accumulated: str) -> dict | None:
    """Parse a partial JSON string; return completed fields as a dict, or None."""
    if not accumulated.strip():
        return None
    try:
        result = from_json(accumulated, allow_partial=True)
        if not isinstance(result, dict) or not result:
            return None
        return result
    except Exception:
        return None
