from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import RunStatus


class OptimizationRun(Base):
    __tablename__ = "optimization_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    repo: Mapped[str] = mapped_column(String(256), index=True, nullable=False)

    terraform_snapshot_id: Mapped[int | None] = mapped_column(ForeignKey("terraform_snapshots.id"), nullable=True)
    metrics_snapshot_id: Mapped[int | None] = mapped_column(ForeignKey("metrics_snapshots.id"), nullable=True)

    status: Mapped[RunStatus] = mapped_column(Enum(RunStatus), default=RunStatus.queued, nullable=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    constraints: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    suggested_config: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    pr_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    terraform_snapshot = relationship("TerraformSnapshot")
    metrics_snapshot = relationship("MetricsSnapshot")
