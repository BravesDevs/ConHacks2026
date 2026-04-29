from __future__ import annotations

import enum


class RunStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    suggestion_ready = "suggestion_ready"
    pr_opened = "pr_opened"
    failed = "failed"
