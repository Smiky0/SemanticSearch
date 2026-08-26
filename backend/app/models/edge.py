import uuid

from sqlalchemy import Enum, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import EdgeType


class Edge(Base):
    __tablename__ = "edges"
    __table_args__ = (
        Index("ix_edges_source", "source_id"),
        Index("ix_edges_target", "target_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("nodes.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("nodes.id", ondelete="CASCADE"),
        nullable=False,
    )
    edge_type: Mapped[EdgeType] = mapped_column(Enum(EdgeType), nullable=False)

    source: Mapped["Node"] = relationship(  # noqa: F821
        foreign_keys=[source_id], back_populates="outgoing_edges"
    )
    target: Mapped["Node"] = relationship(  # noqa: F821
        foreign_keys=[target_id], back_populates="incoming_edges"
    )
