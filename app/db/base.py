from app.db.base_class import Base  # noqa: F401
# Need all models here so alembic could do migration

# Optional models (avoid optional dependency import failures in Alembic env)
try:  # pragma: no cover
    from app.models.api_keys import ApiKeysModel  # noqa: F401
except Exception:  # pragma: no cover
    ApiKeysModel = None  # type: ignore[assignment]

# Work management models
from app.models.users import User  # noqa: F401
from app.models.projects import Project  # noqa: F401
from app.models.work_items import WorkItem  # noqa: F401
from app.models.comments import Comment  # noqa: F401
from app.models.chat_session import ChatSession  # noqa: F401
from app.models.chat import Chat  # noqa: F401
