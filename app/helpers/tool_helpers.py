import inspect
import json
import re
from typing import Any, Awaitable, Callable, Dict

from sqlalchemy.ext.asyncio import AsyncSession

from app.context.tools import get_tool_required_fields
from app.models.users import User
from app.tools.analytics import (
    get_overdue_items,
    get_project_summary,
    get_user_workload,
)
from app.tools.comments import add_comment, delete_comment, list_comments
from app.tools.projects import (
    create_project,
    delete_project,
    find_projects,
    update_project,
)
from app.tools.tasks import find_tasks
from app.tools.users import find_users, get_my_info
from app.tools.workflow import (
    bulk_update_status,
    link_work_items,
    move_work_item,
    reassign_work_item,
)
from app.tools.work_items import (
    create_work_item,
    delete_work_item,
    update_work_item,
)

MAX_TOOL_ROUNDS = 5

_RUNTIME_PARAMS = frozenset({"db", "current_user", "session_id"})

_FAILURE_PREFIXES = ("Error ", "Validation error")
_FAILURE_SUFFIXES = (" not found.", " not found")
_FAILURE_EXACT = frozenset(
    {
        "User not found.",
        "No items updated.",
    }
)


def _is_tool_failure_message(message: str) -> bool:
    """Treat explicit tool failures as errors for the orchestration loop."""
    if message in _FAILURE_EXACT:
        return True
    if message.startswith(_FAILURE_PREFIXES):
        return True
    if message.endswith(_FAILURE_SUFFIXES):
        return True
    if "Failed to find" in message:
        return True
    return False


def safe_json_loads(text: str) -> Dict[str, Any]:
    """
    Best-effort JSON parser for model output.
    Expects raw JSON, but can recover if the model wraps it in code fences.
    """
    if not text:
        raise ValueError("Empty LLM response")

    cleaned = text.strip()

    cleaned = re.sub(r"^```json\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^```\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    return json.loads(cleaned)


ToolHandler = Callable[..., Awaitable[Any]]


def normalize_tool_name(name: str) -> str:
    return name.strip().lower()


def _filter_handler_params(
    handler: ToolHandler, params: Dict[str, Any]
) -> Dict[str, Any]:
    sig = inspect.signature(handler)
    if any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()):
        return params
    return {key: value for key, value in params.items() if key in sig.parameters}


async def execute_tool(
    tool_name: str,
    params: Dict[str, Any],
    db: AsyncSession,
    current_user: User,
    session_id: str,
) -> Dict[str, Any]:
    tool_name = normalize_tool_name(tool_name)

    base_context = {
        "db": db,
        "current_user": current_user,
        "session_id": session_id,
    }

    tool_map: Dict[str, ToolHandler] = {
        "create_project": create_project,
        "update_project": update_project,
        "delete_project": delete_project,
        "find_projects": find_projects,
        "get_my_info": get_my_info,
        "find_users": find_users,
        "add_comment": add_comment,
        "list_comments": list_comments,
        "delete_comment": delete_comment,
        "get_project_summary": get_project_summary,
        "get_user_workload": get_user_workload,
        "get_overdue_items": get_overdue_items,
        "create_work_item": create_work_item,
        "delete_work_item": delete_work_item,
        "update_work_item": update_work_item,
        "find_tasks": find_tasks,
        "reassign_work_item": reassign_work_item,
        "link_work_items": link_work_items,
        "bulk_update_status": bulk_update_status,
        "move_work_item": move_work_item,
    }

    handler = tool_map.get(tool_name)

    if handler is None:
        return {
            "success": False,
            "tool": tool_name,
            "error": f"Unknown tool: {tool_name}",
        }

    try:
        llm_params = {
            k: v
            for k, v in (params or {}).items()
            if k not in _RUNTIME_PARAMS and v is not None
        }
        final_params = {**llm_params, **base_context}
        filtered_params = _filter_handler_params(handler, final_params)
        result = handler(**filtered_params)

        if inspect.isawaitable(result):
            result = await result

        payload: Dict[str, Any] = {
            "success": True,
            "tool": tool_name,
            "data": result,
        }
        if isinstance(result, str) and _is_tool_failure_message(result):
            payload["success"] = False
            payload["error"] = result
        return payload

    except Exception as exc:
        return {
            "success": False,
            "tool": tool_name,
            "error": str(exc),
        }

 