# Import all models here so that Flask-Migrate can detect them
# when building migration scripts.

from app.models.ai import (  # noqa: F401
    AIConversation,
    AIMessage,
    AIMessageDecision,
    RecyclingAuditAttempt,
    RecyclingCase,
    WasteAnalysisRecord,
)
from app.models.forum import ForumComment, ForumPost, ForumPostChunk, Like  # noqa: F401
from app.models.ledger import Transaction  # noqa: F401
from app.models.map import RecyclingStation  # noqa: F401
from app.models.market import MarketItem, Order  # noqa: F401
from app.models.memory import UserMemoryItem  # noqa: F401
from app.models.notification import Notification  # noqa: F401
from app.models.project import Project, ProjectContribution  # noqa: F401
from app.models.recommendation import (  # noqa: F401
    ContentTopicAssignment,
    UserBehaviorEvent,
    UserPreferenceProfile,
)
from app.models.user import User  # noqa: F401
