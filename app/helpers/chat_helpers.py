import json
from datetime import datetime
from pathlib import Path

from langchain_core.messages import HumanMessage, AIMessage

from app.db.cromadb import query_collection
from app.helpers.common import extract_keywords
from app.models.chat import ChatRole

_TOOLS_JSON_PATH = Path(__file__).parent.parent / "context" / "tools.json"


def _load_tools_json() -> dict:
    """Load tools.json once and return the parsed dict."""
    with open(_TOOLS_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


async def generate_session_name(message: str, llm) -> str:
    """Use the LLM to generate a concise chat session name from the first user message."""
    prompt = (
        "Generate a short, descriptive chat session title (3-6 words, no punctuation) "
        f'for a conversation that starts with this message:\n\n"{message}"\n\n'
        "Return only the title, nothing else."
    )
    try:
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        raw = getattr(response, "content", str(response))
        if not isinstance(raw, str):
            raw = str(raw)
        name = raw.strip().strip('"').strip("'")
        return name[:80] or "New Chat"
    except Exception:
        return message[:60].strip() or "New Chat"


def build_message_history(history_items) -> list:
    """Convert DB chat history records into LangChain message objects."""
    messages = []
    for h in history_items:
        if h.role == ChatRole.USER:
            messages.append(HumanMessage(content=h.message))
        elif h.role == ChatRole.AI:
            messages.append(AIMessage(content=h.message))
    return messages


def get_rag_context(message: str) -> tuple[str, list]:
    """Extract keywords from the message and query ChromaDB for relevant context."""
    keywords = extract_keywords(message)
    results = query_collection(query_text=keywords)
    context = results["documents"][0]
    return keywords,f""" 
        Additional context that may help resolve entities or intent:    
        {context}
        """


def extract_tool_calls(messages: list) -> list:
    """Extract tool call metadata from agent response messages."""
    tool_calls = []
    for msg in messages:
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls.append({"name": tc.get("name"), "args": tc.get("args")})
    return tool_calls


_CONTEXT_TEMP_DIR = Path(__file__).parent.parent / "context" / "temp"


def save_context_to_file(
    system_prompt: str, history: list, current_message: str
) -> None:
    """Write the full LLM input context to a timestamped file for token inspection."""
    from app.core.config import settings

    if settings.environment == "prod":
        return
    _CONTEXT_TEMP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filepath = _CONTEXT_TEMP_DIR / f"context_{timestamp}.txt"

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("=== SYSTEM PROMPT ===\n")
        f.write(system_prompt)
        f.write("\n\n=== MESSAGE HISTORY ===\n")
        for msg in history:
            role = "USER" if isinstance(msg, HumanMessage) else "AI"
            f.write(f"[{role}]: {msg.content}\n")
        f.write("\n=== CURRENT MESSAGE ===\n")
        f.write(current_message)
        f.write("\n")
