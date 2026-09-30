from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RecyclingStation(Base):
    __tablename__ = "recycling_stations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    address: Mapped[str | None] = mapped_column(String(256))
    latitude: Mapped[float] = mapped_column()
    longitude: Mapped[float] = mapped_column()
