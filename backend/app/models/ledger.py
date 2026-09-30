from datetime import UTC, datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    # earn | spend
    type: Mapped[str] = mapped_column(String(16))
    # Absolute value (always positive). Use `type` to determine direction.
    points_delta: Mapped[int] = mapped_column()
    # 0 if not a carbon-related transaction.
    co2_delta_kg: Mapped[float] = mapped_column(default=0.0)
    # waste_analysis | project | market_order
    source_type: Mapped[str] = mapped_column(String(32))
    source_id: Mapped[int | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
