"""Data types shared by the Campus Customs agent team."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from backend.audit import AuditLog

AgentName = Literal["boss", "inventory", "accounting", "facilities", "customer_service"]
AGENT_NAMES: tuple[AgentName, ...] = ("boss", "inventory", "accounting", "facilities", "customer_service")
TicketStatus = Literal["open", "in_progress", "awaiting_approval", "escalated", "resolved"]


class AgentReport(BaseModel):
    """What a specialist (Inventory, Accounting, Facilities, Customer Service)
    hands back to whoever asked."""

    summary: str = Field(description="Two or three sentences answering the question asked, in your own voice.")
    facts: list[str] = Field(
        default_factory=list,
        description="Key facts, each with the tool it came from, e.g. 'S on hand: 0 (check_stock)'.",
    )
    actions_taken: list[str] = Field(
        default_factory=list,
        description="Board writes made, e.g. 'payment request #1 filed', 'draft #2 saved'.",
    )
    needs_human: bool = Field(description="True if a person must approve or decide something.")
    open_questions: list[str] = Field(
        default_factory=list, description="Anything still unknown or unconfirmed."
    )


class TicketDecision(BaseModel):
    """The Boss's final call on one ticket."""

    ticket_id: int
    status: TicketStatus = Field(description="The status set on the board with set_ticket_status.")
    decision: str = Field(description="What the Boss decided, in plain language and the Boss's own few words.")
    findings: list[str] = Field(default_factory=list, description="What the team found, with sources.")
    waiting_on_human: list[str] = Field(
        default_factory=list, description="Approvals or decisions only a person can make."
    )
    drafts_created: list[str] = Field(
        default_factory=list, description="Drafts and payment requests on the board, by id."
    )


@dataclass
class TeamDeps:
    """Per-run context passed to every agent and tool call."""

    run_id: str
    ticket_id: int | None
    agent: AgentName
    audit: AuditLog
    depth: int = 0
    chain: list[str] = field(default_factory=list)  # who is waiting on whom
    # Shared across the whole ticket run (same object in every delegated run):
    delegation_count: dict[str, int] = field(default_factory=lambda: {"n": 0})
    answer_cache: dict[tuple[str, str], str] = field(default_factory=dict)

    def for_teammate(self, teammate: AgentName) -> TeamDeps:
        return TeamDeps(
            run_id=self.run_id,
            ticket_id=self.ticket_id,
            agent=teammate,
            audit=self.audit,
            depth=self.depth + 1,
            chain=[*self.chain, teammate],
            delegation_count=self.delegation_count,
            answer_cache=self.answer_cache,
        )


class AuditEvent(BaseModel):
    """One entry in output/audit_trail.json."""

    timestamp: str
    run_id: str
    ticket_id: int | None
    agent: str
    depth: int
    chain: list[str]
    step: int | None = None
    event: str  # run_start | user_prompt | model_response | tool_results | delegation | run_end | run_error
    model: str | None = None
    detail: dict[str, Any] = Field(default_factory=dict)
    usage: dict[str, Any] | None = None


class TicketRunResult(BaseModel):
    run_id: str
    ticket_id: int
    decision: TicketDecision | None
    error: str | None = None
    usage: dict[str, Any]
