import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Enum, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import IndexingStatus


class Repository(Base):
    __tablename__ = "repositories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    path: Mapped[str] = mapped_column(String(1024), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    status: Mapped[IndexingStatus] = mapped_column(
        Enum(IndexingStatus), default=IndexingStatus.PENDING, nullable=False
    )
    indexed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    file_count: Mapped[int] = mapped_column(default=0)
    symbol_count: Mapped[int] = mapped_column(default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    nodes: Mapped[list["Node"]] = relationship(  # noqa: F821
        back_populates="repository", cascade="all, delete-orphan"
    )
