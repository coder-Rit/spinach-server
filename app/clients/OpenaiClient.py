from app.core.config import settings
from app.helpers.log_helper import LLMLoggingCallback
from langchain_openai import ChatOpenAI


class OpenaiClient:
    llm = ChatOpenAI(
        model="openrouter/free",
        openai_api_key=settings.OPENROUTER_API_KEY,
        openai_api_base="https://openrouter.ai/api/v1",
        temperature=0.9,
        callbacks=[LLMLoggingCallback()],
    )
