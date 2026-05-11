import json
import logging
import logging.handlers
import sys
import warnings
from pathlib import Path
from typing import Any, List

from app.core.config import settings

import tiktoken
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d [+] %(message)s"
_LOG_DIR = Path(__file__).parent.parent.parent / "logs"
_LOG_FILE = _LOG_DIR / "llm.log"


# ---------------------------------------------------------------------------
# Token counting
# ---------------------------------------------------------------------------


def _get_encoding() -> tiktoken.Encoding:
    try:
        return tiktoken.encoding_for_model("gpt-4o")
    except Exception:
        return tiktoken.get_encoding("cl100k_base")


def _count_chat_tokens(openai_messages: list[dict]) -> int:
    """Count tokens for the exact OpenAI chat-completion payload.

    Uses the same formula as the OpenAI cookbook:
    https://github.com/openai/openai-cookbook/blob/main/examples/How_to_count_tokens_with_tiktoken.ipynb
    """
    enc = _get_encoding()
    total = 3  # every reply is primed with <|start|>assistant<|message|>
    for msg in openai_messages:
        total += 4  # every message has role/content/sep overhead
        total += len(enc.encode(msg.get("role", "")))
        content = msg.get("content", "")
        if isinstance(content, str):
            total += len(enc.encode(content))
        elif isinstance(content, list):
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    total += len(enc.encode(part.get("text", "")))
    return total


def _msg_to_openai(msg: BaseMessage) -> dict:
    if isinstance(msg, SystemMessage):
        role = "system"
    elif isinstance(msg, HumanMessage):
        role = "user"
    elif isinstance(msg, AIMessage):
        role = "assistant"
    else:
        role = getattr(msg, "type", "user")
    return {"role": role, "content": msg.content}


# ---------------------------------------------------------------------------
# LangChain callback
# ---------------------------------------------------------------------------


class LLMLoggingCallback(BaseCallbackHandler):
    """Logs every chat-completion request/response to the single LLM log file."""

    def __init__(self) -> None:
        super().__init__()
        self._log = logging.getLogger("llm.requests")

    # -- request -------------------------------------------------------------

    def on_chat_model_start(
        self,
        serialized: dict,
        messages: List[List[BaseMessage]],
        **kwargs: Any,
    ) -> None:
        model = (serialized or {}).get("kwargs", {}).get("model_name", "unknown")
        for batch in messages:
            openai_msgs = [_msg_to_openai(m) for m in batch]
            token_count = _count_chat_tokens(openai_msgs)
            payload_json = json.dumps(openai_msgs, ensure_ascii=False, indent=2)
            self._log.info(
                "LLM REQUEST | model=%s | input_tokens=%d\nPayload:\n%s",
                model,
                token_count,
                payload_json,
            )

    # -- response ------------------------------------------------------------

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        try:
            usage = getattr(response, "llm_output", None) or {}
            token_usage = usage.get("token_usage") or usage.get("usage") or {}
            preview_parts = []
            for gen_list in response.generations:
                for gen in gen_list:
                    text = getattr(gen, "text", None)
                    if text is None:
                        msg = getattr(gen, "message", None)
                        text = getattr(msg, "content", "") if msg else ""
                    preview_parts.append(str(text)[:300])
            self._log.info(
                "LLM RESPONSE | usage=%s | preview=%.600s",
                token_usage,
                " | ".join(preview_parts),
            )
        except Exception as exc:
            self._log.warning("LLM RESPONSE logging failed: %s", exc)

    # -- error ---------------------------------------------------------------

    def on_llm_error(self, error: Exception, **kwargs: Any) -> None:
        self._log.error("LLM ERROR: %s", error, exc_info=error)


# ---------------------------------------------------------------------------
# App logger setup
# ---------------------------------------------------------------------------


def get_logger() -> logging.Logger:
    logger = logging.getLogger()
    if logger.hasHandlers():
        logger.handlers.clear()

    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(_LOG_FORMAT)

    # Console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Rotating file — only in non-prod environments
    if settings.environment != "prod":
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            _LOG_FILE,
            maxBytes=10 * 1024 * 1024,  # 10 MB per file
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    warnings.filterwarnings(
        "ignore", category=UserWarning, message="Pydantic serializer warnings"
    )

    return logger
