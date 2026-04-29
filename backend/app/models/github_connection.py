from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, JSON, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class GitHubConnection(Base):
    __tablename__ = "github_connections"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_github_connections_user_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    encrypted_token: Mapped[str] = mapped_column(String(512), nullable=False)
    tracked_repos: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
