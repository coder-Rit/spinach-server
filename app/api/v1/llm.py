from fastapi import Depends, APIRouter
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_core.messages import HumanMessage
from langchain.agents import create_agent

from app.schemas.chat import LlmPayload
from app.clients.OpenaiClient import OpenaiClient
from app.api.v1.auth import get_current_user
from app.models.users import User
from app.models.chat import ChatRole
from app.db.session import get_async_session
from app.services.chat_service import ChatService
from app.services.chat_session_service import ChatSessionService
from app.services.project_service import ProjectService
from app.helpers.chat_helpers import (
    generate_session_name,
    build_message_history,
    retrieve_rag_context,
    select_tool_keys,
    build_system_prompt,
    save_context_to_file,
)

from app.tools.work_items import create_work_item, delete_work_item, update_work_item
from app.tools.users import find_users, get_my_info
from app.tools.projects import (
    find_projects,
    create_project,
    update_project,
    delete_project,
)
from app.tools.tasks import find_tasks
from app.tools.comments import add_comment, list_comments, delete_comment
from app.tools.analytics import (
    get_project_summary,
    get_user_workload,
    get_overdue_items,
)
from app.tools.workflow import (
    reassign_work_item,
    link_work_items,
    bulk_update_status,
    move_work_item,
)

chat_router = APIRouter(prefix="/llm")


AGENT_TOOLS = [
    # Work item CRUD
    create_work_item,
    delete_work_item,
    update_work_item,
    # Project CRUD
    create_project,
    update_project,
    delete_project,
    # Query tools
    find_users,
    get_my_info,
    find_projects,
    find_tasks,
    # Comments
    add_comment,
    list_comments,
    delete_comment,
    # Analytics
    get_project_summary,
    get_user_workload,
    get_overdue_items,
    # Workflow
    reassign_work_item,
    link_work_items,
    bulk_update_status,
    move_work_item,
]


async def _resolve_session(
    payload: LlmPayload, session_service: ChatSessionService, user_id, llm
):
    """Return an existing session or create a new one with an AI-generated name."""
    if payload.session_id is not None:
        session = await session_service.get(payload.session_id)
        if session:
            return session

    name = await generate_session_name(payload.message, llm)
    return await session_service.create(name=name, user_id=user_id)


@chat_router.post("")
async def chat_llm(
    payload: LlmPayload,
    client: OpenaiClient = Depends(OpenaiClient),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    chat_service = ChatService(db)
    session_service = ChatSessionService(db)

    # 1. Resolve or create session
    session = await _resolve_session(
        payload, session_service, current_user.user_id, client.llm
    )
    session_id = session.session_id

    # 2. Load history & persist user message
    history_items = await chat_service.get_recent(session_id=session_id, limit=10)
    history = build_message_history(history_items)

    await chat_service.create(
        session_id=session_id,
        message=payload.message,
        role=ChatRole.USER,
        user_id=current_user.user_id,
    )

    # 3. Retrieve RAG context
    context_keywords, context = retrieve_rag_context(payload.message)

    project = None
    if payload.project_id:
        project_service = ProjectService(db)
        project = await project_service.get_by_id(payload.project_id)

    # 4. Select only the tool keys relevant to this message, then build system prompt
    tool_keys = await select_tool_keys(payload.message, client.llm)
    system_prompt = build_system_prompt(
        context, tool_keys=tool_keys, current_user=current_user, project=project
    )

    # 5. Save full context to a temp file for token inspection
    save_context_to_file(system_prompt, history, payload.message)

    # 6. Run agent and return response
    agent_executor = create_agent(client.llm, AGENT_TOOLS, system_prompt=system_prompt)
    current_messages = history + [HumanMessage(content=payload.message)]

    result = await agent_executor.ainvoke({"messages": current_messages})
    final_message = result["messages"][-1]
    response_text = (
        final_message.content
        if hasattr(final_message, "content")
        else str(final_message)
    )

    await chat_service.create(
        session_id=session_id,
        message=response_text,
        role=ChatRole.AI,
        user_id=current_user.user_id,
    )

    return {
        "session_id": str(session_id),
        "response": response_text,
        "tool_keys_used": tool_keys,
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
