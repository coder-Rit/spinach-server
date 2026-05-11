import uuid
from typing import Optional
from pydantic import BaseModel


class LlmPayload(BaseModel):
    message: str
    session_id: uuid.UUID
    project_id: Optional[uuid.UUID] = None


class SemanticSearchPayload(BaseModel):
    query: str


class AddDocumentPayload(BaseModel):
    content: str
    metadata: dict = {}
