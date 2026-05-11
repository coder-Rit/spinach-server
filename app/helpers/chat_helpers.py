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
        name = response.content.strip().strip('"').strip("'")
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


def retrieve_rag_context(message: str) -> tuple[str, list]:
    """Extract keywords from the message and query ChromaDB for relevant context."""
    keywords = extract_keywords(message)
    results = query_collection(query_text=keywords)
    context = results["documents"][0]
    return keywords, context


async def select_tool_keys(message: str, llm) -> list[str]:
    """Ask the LLM to select only the relevant tool keys from tools.json for the given user message."""
    tools = _load_tools_json()
    available = sorted(tools.keys())
    prompt = (
        "You are a tool router. Given a user message, select which tool groups "
        "are needed to handle the request.\n\n"
        "Available tool groups:\n"
        + "\n".join(f"- {k}" for k in available)
        + "\n\nNaming convention: {{entity}}_{{operation}}\n"
        "  get = read/search/list  |  create = insert new  |  update = modify  |  delete = soft-delete\n\n"
        f'User message: "{message}"\n\n'
        "Return ONLY a comma-separated list of the relevant group keys, nothing else."
    )
    try:
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        selected = [k.strip() for k in response.content.strip().split(",")]
        # Keep only keys that actually exist
        return [k for k in selected if k in available]
    except Exception:
        return available  # fall back to all keys on error


def build_system_prompt(
    context: list, tool_keys: list[str], current_user=None, project=None
) -> str:
    """Load the system prompt template and inject retrieved context and current user info."""
    context_dir = Path(__file__).parent.parent / "context"
    system_prompt_path = context_dir / "SYSTEM.md"
    with open(system_prompt_path, "r", encoding="utf-8") as f:
        template = f.read()

    # Build tool documentation block from selected keys in tools.json
    tools_data = _load_tools_json()
    tools_sections = []
    for key in sorted(tool_keys):
        group = tools_data.get(key)
        if not group:
            continue
        lines = [f"### {group['label']}"]
        for tool in group["tools"]:
            params = ", ".join(tool["params"])
            lines.append(f"\n**{tool['name']}({params})**")
            lines.append(tool["description"])
            for note in tool.get("notes", []):
                lines.append(f"- {note}")
        tools_sections.append("\n".join(lines))
    if tools_sections:
        tools_block = "\n\n## Available Tools\n\n" + "\n\n---\n\n".join(tools_sections)
        template = template.replace(
            "## Decision Rules", tools_block + "\n\n---\n\n## Decision Rules"
        )

    prompt = template.replace("{context}", str(context))
    if current_user is not None:
        user_block = (
            f"\n\n## Current User (YOU are acting on behalf of this user)\n"
            f"- user_id: {current_user.user_id}\n"
            f"- name: {current_user.name}\n"
            f"- email: {current_user.email}\n"
            "Use this user_id as `user_id`, `created_by`, `assigned_by`, or any other "
            "caller-identity field in every tool call unless the user explicitly specifies someone else."
        )
        prompt = prompt + user_block
    if project is not None:
        project_block = (
            f"\n\n## Active Project Context\n"
            f"The user has selected the following project as their active context. "
            f"Assume all work items, tasks, and queries relate to this project unless stated otherwise.\n"
            f"- project_id: {project.project_id}\n"
            f"- title: {project.title}\n"
            f"- status: {project.status.value if hasattr(project.status, 'value') else project.status}\n"
            f"- managed_by: {project.managed_by}\n"
        )
        if project.description:
            project_block += f"- description: {project.description}\n"
        prompt = prompt + project_block
    else:
        no_project_block = (
            "\n\n## Project Context\n"
            "The user has NOT selected any active project. "
            "Do not assume any specific project is in scope. "
            "If the user's request requires a project (e.g. creating work items, listing tasks, "
            "querying project-specific data), ask the user to specify which project they are referring to "
            "before proceeding with any tool call that needs a project_id."
        )
        prompt = prompt + no_project_block
    return prompt


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
