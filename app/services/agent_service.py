import json
import logging
from langchain_core.messages import HumanMessage, SystemMessage

from app.clients.OpenaiClient import AiClient
from app.context.tools import tools_metadata, tools_info
from app.context.vector_context import vector_context


logger = logging.getLogger(__name__)


def classify_tools(messages: list[str], llm=None) -> list[dict]:
    """
    Accepts last N user messages as a list of strings.
    Sends them as a single combined context to the classifier.
    """
    llm = llm or AiClient.get_default_llm()

    # Join messages as a numbered history block for better context
    history = "\n".join(f"{i + 1}. {msg.strip()}" for i, msg in enumerate(messages))

    system_content = str(tools_metadata).strip()
    user_content = f"Recent user messages:\n{history}"

    llm_messages = [
        SystemMessage(content=system_content),
        HumanMessage(content=user_content),
    ]

    try:
        response = llm.invoke(llm_messages)
        raw = response.content

        if not isinstance(raw, str):
            raw = str(raw)

        raw = raw.strip()

        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        parsed = json.loads(raw)

        if not isinstance(parsed, list):
            raise ValueError(f"Expected a list, got: {type(parsed)}")

        return parsed

    except json.JSONDecodeError as e:
        logger.error("Failed to parse LLM response as JSON: %s | Raw: %s", e, raw)
        return []
    except Exception as e:
        logger.error("classify_tools failed: %s", e)
        return []


def get_tool_context(messages: list[str], llm=None) -> dict:
    """
    Accepts last N user messages directly.
    Returns actual tool definitions from tools_info
    based on the classified entity-operation pairs.
    """
    pairs = classify_tools(messages, llm=llm)

    context = {}
    for pair in pairs:
        entity = pair.get("entity")
        operation = pair.get("operation")

        if not entity or not operation:
            continue

        if entity not in tools_info:
            logger.warning("Entity '%s' not found in tools_info", entity)
            continue

        if operation not in tools_info[entity]:
            logger.warning(
                "Operation '%s' not found under entity '%s'", operation, entity
            )
            continue

        context.setdefault(entity, {})
        context[entity].setdefault(operation, {})
        context[entity][operation].update(tools_info[entity][operation])

    return f"""
        You have access to the following tools based on the user's request:
        ```json
        {json.dumps(context, indent=2)}
        ```
    """


def classify_tool_and_rag(user_content: str) -> dict:
    """
    Returns:
    {
        "needs_rag": bool,
        "needs_tools": bool
    }
    """

    llm = AiClient.get_default_llm()

    llm_messages = [
        SystemMessage(content=vector_context.strip()),
        HumanMessage(content=user_content),
    ]

    default_response = {
        "needs_rag": True,
        "needs_tools": False,
    }

    try:
        response = llm.invoke(llm_messages)

        raw = (
            response.content
            if isinstance(response.content, str)
            else str(response.content)
        ).strip()

        if raw.startswith("```"):
            raw = raw.strip("`").strip()
            if raw.lower().startswith("json"):
                raw = raw[4:].strip()

        parsed = json.loads(raw)

        if (
            isinstance(parsed, dict)
            and isinstance(parsed.get("needs_rag"), bool)
            and isinstance(parsed.get("needs_tools"), bool)
        ):
            return {
                "needs_rag": parsed["needs_rag"],
                "needs_tools": parsed["needs_tools"],
            }

        logger.warning("Unexpected classifier output: %s", raw)
        return default_response

    except Exception as e:
        logger.error("classify_tool_or_rag failed: %s", e)
        return default_response


def prioritize_chat_message(messages: list[str]) -> list:
    """
    Builds chat messages for the classifier.

    Previous messages = supporting context
    Latest message = primary intent source
    """

    if not messages:
        raise ValueError("messages cannot be empty")

    previous_messages = messages[:-1]
    latest_message = messages[-1]

    context_block = "\n".join(
        f"{i + 1}. {msg}" for i, msg in enumerate(previous_messages)
    )

    return f"""
Previous conversation context:
{context_block if context_block else "None"}

Latest user message:
{latest_message}
"""

    return
