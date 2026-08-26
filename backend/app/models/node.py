import uuid

from sqlalchemy import Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import SymbolType


class Node(Base):
    __tablename__ = "nodes"
    __table_args__ = (
        Index("ix_nodes_repo_path", "repository_id", "file_path"),
        Index("ix_nodes_repo_symbol", "repository_id", "symbol_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
    )
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    language: Mapped[str] = mapped_column(String(64), nullable=False)
    symbol_name: Mapped[str] = mapped_column(String(512), nullable=False)
    symbol_type: Mapped[SymbolType] = mapped_column(Enum(SymbolType), nullable=False)
    parent_symbol_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("nodes.id", ondelete="SET NULL"),
        nullable=True,
    )
    start_line: Mapped[int] = mapped_column(nullable=False)
    end_line: Mapped[int] = mapped_column(nullable=False)
    source_code: Mapped[str] = mapped_column(Text, nullable=False)
    docstring: Mapped[str | None] = mapped_column(Text, nullable=True)
    qdrant_point_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

    repository: Mapped["Repository"] = relationship(back_populates="nodes")  # noqa: F821
    parent: Mapped["Node | None"] = relationship(
        remote_side="Node.id", foreign_keys=[parent_symbol_id]
    )
    outgoing_edges: Mapped[list["Edge"]] = relationship(  # noqa: F821
        foreign_keys="Edge.source_id", back_populates="source"
    )
    incoming_edges: Mapped[list["Edge"]] = relationship(  # noqa: F821
        foreign_keys="Edge.target_id", back_populates="target"
    )
