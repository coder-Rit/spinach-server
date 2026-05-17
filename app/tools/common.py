from fastapi import HTTPException


def tool_error(action: str, exc: Exception) -> str:
    """Format an exception as a clear message for the LLM."""
    if isinstance(exc, HTTPException):
        detail = exc.detail
        if isinstance(detail, str):
            return detail
        return f"Error {action}: {detail}"
    if isinstance(exc, ValueError):
        return f"Validation error: {str(exc)}"
    return f"Error {action}: {str(exc)}"
