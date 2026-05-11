import datetime
import json
import re

from fastapi.responses import JSONResponse


def get_utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def create_json_error_response(
    message: str,
    status_code: int,
    error_details: list = [],
) -> JSONResponse:
    response_data = {
        "message": message,
        "error_details": error_details,
    }
    if error_details:
        response_data["error_details"] = error_details

    return create_json_response(response_data, status_code)


def create_json_response(
    response_message: dict,
    status_code: int,
) -> JSONResponse:
    response_message = json.loads(json.dumps(response_message, default=str))
    return JSONResponse(
        status_code=status_code,
        content=response_message,
        media_type="application/json",
    )


def format_message(message: str) -> str:
    if not message:
        return ""

    # Convert escaped newlines to real newlines
    message = message.replace("\\n", "\n")

    # Normalize multiple blank lines (max 2)
    message = re.sub(r"\n{3,}", "\n\n", message)

    # Clean bullet formatting (only at start of lines or after whitespace)
    # Supports *, -, + as bullet points, preserving indentation
    message = re.sub(r"^([ \t]*)[*+-][ \t]+", r"\1• ", message, flags=re.MULTILINE)

    # Strip leading/trailing whitespace
    return message.strip()


from langchain_community.chat_message_histories import ChatMessageHistory

# store per-session history (temporary)
store = {}


def get_session_history(session_id: str):
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]


def extract_keywords(text: str) -> str:
    """
    Best-effort keyword extraction.

    This module is imported at app startup; avoid hard-failing if the spaCy model
    isn't present in the environment.
    """
    try:
        import spacy  # noqa: PLC0415

        nlp = spacy.load("en_core_web_sm")
        doc = nlp(text)
        keywords = [token.text for token in doc if token.pos_ in ["NOUN", "PROPN"]]
        return " ".join(keywords)
    except Exception:
        return text