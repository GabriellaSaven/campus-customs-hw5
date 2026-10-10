"""Append-only audit trail at output/audit_trail.json.

The file is one JSON array. Each event is appended to the end; existing
entries are never removed or rewritten, and the file is never wiped between
runs. Writes go through a temp file + rename so a crash can't corrupt it.
"""

import asyncio
import fcntl
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from backend.config import AUDIT_PATH, AUDIT_TEXT_LIMIT
from backend.models import AuditEvent, TeamDeps


def clip(value: Any, limit: int = AUDIT_TEXT_LIMIT) -> Any:
    """Keep audit entries a readable size."""
    if isinstance(value, str):
        return value if len(value) <= limit else value[:limit] + f"... [+{len(value) - limit} chars]"
    if isinstance(value, dict):
        return {k: clip(v, limit) for k, v in value.items()}
    if isinstance(value, list):
        return [clip(v, limit) for v in value]
    return value


class AuditLog:
    def __init__(self, path: Path = AUDIT_PATH):
        self.path = path
        self._lock = asyncio.Lock()

    def _append(self, entry: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        lock_path = self.path.with_name(f".{self.path.stem}.lock")  # hidden, next to the file
        with open(lock_path, "w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)  # also safe if two processes run at once
            events: list = []
            if self.path.exists() and self.path.stat().st_size:
                events = json.loads(self.path.read_text())
                if not isinstance(events, list):
                    raise ValueError(f"{self.path} is not a JSON array; refusing to overwrite it.")
            events.append(entry)
            tmp = self.path.with_name(f".{self.path.name}.tmp")
            tmp.write_text(json.dumps(events, indent=2, default=str) + "\n")
            os.replace(tmp, self.path)

    async def record(
        self,
        deps: TeamDeps,
        event: str,
        *,
        step: int | None = None,
        model: str | None = None,
        detail: dict | None = None,
        usage: dict | None = None,
    ) -> None:
        entry = AuditEvent(
            timestamp=datetime.now().isoformat(timespec="milliseconds"),
            run_id=deps.run_id,
            ticket_id=deps.ticket_id,
            agent=deps.agent,
            depth=deps.depth,
            chain=deps.chain,
            step=step,
            event=event,
            model=model,
            detail=clip(detail or {}),
            usage=usage,
        ).model_dump()
        async with self._lock:
            await asyncio.to_thread(self._append, entry)

    async def record_system(self, event: str, detail: dict | None = None) -> None:
        """A non-agent event (e.g. a human reset of the shop), so the trail shows it too."""
        entry = AuditEvent(
            timestamp=datetime.now().isoformat(timespec="milliseconds"),
            run_id="system",
            ticket_id=None,
            agent="human",
            depth=0,
            chain=[],
            event=event,
            detail=clip(detail or {}),
        ).model_dump()
        async with self._lock:
            await asyncio.to_thread(self._append, entry)
