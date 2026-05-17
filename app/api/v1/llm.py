import asyncio
import json
import logging
import uuid
from typing import Any, Dict, List

from fastapi import Depends, APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.chat import LlmPayload
from app.api.v1.auth import get_current_user
from app.models.users import User
from app.models.chat import ChatRole
from app.db.session import AsyncSessionLocal, get_async_session
from app.services.chat_service import ChatService
from app.services.chat_session_service import ChatSessionService
from app.helpers.chat_helpers import (
    build_message_history,
    generate_session_name,
    get_rag_context,
)
from langchain_core.messages import HumanMessage

from app.services.agent_service import (
    classify_tool_and_rag,
    get_tool_context,
)
from app.clients.OpenaiClient import AiClient
from app.context.final_response_prompt import final_response_prompt_raw
from app.context.tools import call_tools_prompt_raw
from app.helpers.tool_helpers import MAX_TOOL_ROUNDS, execute_tool, safe_json_loads

chat_router = APIRouter(prefix="/llm")
logger = logging.getLogger(__name__)


async def _persist_session_and_user_message(
    session_id: uuid.UUID,
    message: str,
    user_id: uuid.UUID,
) -> None:
    """Ensure session exists, save the user message, and name new sessions via LLM."""
    llm = AiClient.get_chat_llm()
    try:
        async with AsyncSessionLocal() as db:
            session_service = ChatSessionService(db)
            chat_service = ChatService(db)

            session = await session_service.get(session_id)
            if session is None:
                placeholder = message[:60].strip() or "New Chat"
                await session_service.create(
                    name=placeholder,
                    user_id=user_id,
                    session_id=session_id,
                )
                name = await generate_session_name(message, llm)
                await session_service.update_name(session_id, name)

            await chat_service.create(
                session_id=session_id,
                message=message,
                role=ChatRole.USER,
                user_id=user_id,
            )
    except Exception:
        logger.exception(
            "Background session/user-message persist failed for session %s",
            session_id,
        )


def _with_current_user_message(history: list, message: str) -> list:
    """Include the in-flight user turn when the background save has not committed yet."""
    if (
        history
        and isinstance(history[-1], HumanMessage)
        and history[-1].content == message
    ):
        return history
    return [*history, HumanMessage(content=message)]


@chat_router.post("")
async def chat_llm(
    payload: LlmPayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    chat_service = ChatService(db)
    llm = AiClient.get_chat_llm()
    session_id = payload.session_id

    # 1–2. Resolve session and save user message without blocking the LLM pipeline
    asyncio.create_task(
        _persist_session_and_user_message(
            session_id=session_id,
            message=payload.message,
            user_id=current_user.user_id,
        )
    )

    # 3. Load recent chat history
    recent_10_chats = await chat_service.get_recent(
        session_id=session_id,
        limit=10,
        chat_types=[ChatRole.USER, ChatRole.AI],
    )

    recent_10_history = _with_current_user_message(
        build_message_history(recent_10_chats), payload.message
    )
    recent_5_history = recent_10_history[:5]
    built_messages = [msg.content for msg in recent_5_history]


 

    tools_context = get_tool_context(built_messages, llm=llm)

    _, rag_context = get_rag_context(payload.message)

    # 5. Manual tool orchestration loop
    tool_outputs: List[Dict[str, Any]] = []
    current_prompt_context = "\n".join(
        f"USER: {msg.content}"
        if isinstance(msg, HumanMessage)
        else f"AI: {msg.content}"
        for msg in recent_10_history
    )

    for _ in range(MAX_TOOL_ROUNDS):
         
        call_tools_prompt = call_tools_prompt_raw.format(
            tools_context=tools_context,
            rag_context=rag_context,
            prioritized_messages=current_prompt_context,
            my_uuid=current_user.user_id
        )

        tool_decision_msg = await llm.ainvoke([HumanMessage(content=call_tools_prompt)])
        tool_decision_text = getattr(
            tool_decision_msg, "content", str(tool_decision_msg)
        )

        try:
            tool_decision = safe_json_loads(tool_decision_text)
        except Exception as exc:
            tool_outputs.append(
                {
                    "success": False,
                    "tool": "router_parse_error",
                    "error": f"Invalid tool-selection JSON: {str(exc)}",
                    "raw": tool_decision_text,
                }
            )
            break

        tool_name = tool_decision.get("tool")
        params = tool_decision.get("params", {}) or {}

        if not tool_name or tool_name in ("final_answer", "none", "null"):
            break

     
        tool_result = await execute_tool(
            tool_name=tool_name,
            params=params,
            db=db,
            current_user=current_user,
            session_id=session_id,
        )

        tool_outputs.append(
            {
                "requested_tool": tool_name,
                "params": params,
                "result": tool_result,
            }
        )

        # Feed tool result back into the next loop iteration
        current_prompt_context = (
            f"{current_prompt_context}\n\n"
            f"TOOL OUTPUTS SO FAR:\n{json.dumps(tool_outputs, default=str, indent=2)}"
        )

        # Optional: stop early if tool failed in a way that cannot be recovered
        if not tool_result.get("success", False):
            break

    # 6. Final response generation
    final_prompt = final_response_prompt_raw.format(
        rag_context=rag_context,
        prioritized_messages=current_prompt_context,
        outputs=json.dumps(tool_outputs, default=str, indent=2),
    )

    final_msg = await llm.ainvoke([HumanMessage(content=final_prompt)])
    final_text = getattr(final_msg, "content", str(final_msg))

    # 7. Save assistant response
    await chat_service.create(
        session_id=session_id,
        message=final_text,
        role=ChatRole.AI,
        user_id=current_user.user_id,
    )

    return {
        "session_id": session_id,
        "response": final_text,
        "tool_outputs": tool_outputs,
    }


# @chat_router.post("/semantic-search")
# async def semantic_search(
#     payload: SemanticSearchPayload, current_user: User = Depends(get_current_user)
# ):
#     results = query_collection(query_text=payload.query)
#     return results["documents"][0]


# @chat_router.post("/add-document")
# async def add_document(payload: AddDocumentPayload):
#     doc_id = add_to_collection(payload.content, payload.metadata)
#     return {
#         "status": "success",
#         "message": "Document added successfully",
#         "doc_id": doc_id,
#     }
