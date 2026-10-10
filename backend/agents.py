"""The Campus Customs agent team: Boss, Inventory, Accounting, Facilities and
Customer Service, built with PydanticAI.

- Every agent runs on gpt-6-luna through Portkey (see backend/config.py).
- Every agent reads its system prompt from backend/prompts/<name>.md.
- Every shop fact comes from the MCP server (launched from .mcp.json). Each
  agent only sees the MCP tools its job needs; no agent sees the money tools.
- Full connectivity: every agent has `ask_agent` and can delegate to any
  teammate. Delegation is guarded against loops, repeats and runaway cost.
- Every loop step is appended to output/audit_trail.json.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, replace
from typing import Any

from openai import AsyncOpenAI
from pydantic_ai import Agent, RunContext, Tool
from pydantic_ai.exceptions import UsageLimitExceeded
from pydantic_ai.mcp import MCPToolset
from pydantic_ai.messages import RetryPromptPart, TextPart, ToolCallPart, ToolReturnPart
from pydantic_ai.models.openai import OpenAIResponsesModel, OpenAIResponsesModelSettings
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.tools import ToolDefinition
from pydantic_ai.usage import RunUsage, UsageLimits

from backend.audit import AuditLog
from backend.config import (
    AGENT_RETRIES,
    AGENT_TOOLS,
    AUTHOR_TOOLS,
    DASHBOARD_READ_TOOLS,
    HUMAN_ONLY_TOOLS,
    MAX_DELEGATION_DEPTH,
    MAX_DELEGATIONS_PER_TICKET,
    MAX_OUTPUT_TOKENS,
    MODEL_NAME,
    PORTKEY_BASE_URL,
    PORTKEY_PROVIDER,
    PROMPTS_DIR,
    REASONING_EFFORT,
    REQUEST_LIMIT,
    TOOL_CALLS_LIMIT,
    TOTAL_TOKENS_LIMIT,
    portkey_api_key,
)
from backend.mcp_client import mcp_client
from backend.models import AGENT_NAMES, AgentName, AgentReport, TeamDeps, TicketDecision, TicketRunResult


@dataclass(frozen=True)
class Role:
    title: str
    prompt_file: str
    output_type: type
    ask_me_about: str  # shown to teammates in the ask_agent tool description


ROLES: dict[AgentName, Role] = {
    "boss": Role(
        "Boss (shift manager)",
        "boss.md",
        TicketDecision,
        "final calls, priorities when cash is tight, discount decisions, unclear ownership, escalation",
    ),
    "inventory": Role(
        "Inventory (stockroom lead)",
        "inventory.md",
        AgentReport,
        "stock by SKU and size, shortfalls, in-stock alternatives, which vendor restocks and its lead time",
    ),
    "accounting": Role(
        "Accounting (bookkeeper)",
        "accounting.md",
        AgentReport,
        "invoices, overdue bills, cash position, margins and discounts, payment requests, purchase orders",
    ),
    "facilities": Role(
        "Facilities (space and building lead)",
        "facilities.md",
        AgentReport,
        "lease, rent amount and due date, landlord, building and maintenance issues",
    ),
    "customer_service": Role(
        "Customer Service (voice of the shop)",
        "customer_service.md",
        AgentReport,
        "drafting replies to customers and requesters (drafts only, never sent)",
    ),
}

def new_run_id() -> str:
    return uuid.uuid4().hex[:12]


USAGE_LIMITS = UsageLimits(
    request_limit=REQUEST_LIMIT,
    tool_calls_limit=TOOL_CALLS_LIMIT,
    total_tokens_limit=TOTAL_TOKENS_LIMIT,
)


def build_model() -> OpenAIResponsesModel:
    """gpt-6-luna through Portkey. The only model used anywhere in this project.

    Uses OpenAI's Responses API: gpt-6-luna rejects tool calls with reasoning on
    the older Chat Completions endpoint. Portkey reports the deployment as
    'gpt-6-luna-global' (the provider's name for the same model)."""
    key = portkey_api_key()
    client = AsyncOpenAI(
        api_key=key,
        base_url=PORTKEY_BASE_URL,
        default_headers={"x-portkey-api-key": key, "x-portkey-provider": PORTKEY_PROVIDER},
    )
    return OpenAIResponsesModel(MODEL_NAME, provider=OpenAIProvider(openai_client=client))


def usage_dict(usage: RunUsage) -> dict[str, int]:
    return {
        "requests": usage.requests,
        "tool_calls": usage.tool_calls,
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "total_tokens": usage.input_tokens + usage.output_tokens,
    }


async def _hide_author(ctx: RunContext[TeamDeps], tool_defs: list[ToolDefinition]) -> list[ToolDefinition]:
    """Remove `author` from tool schemas; the backend fills it in, so agents can't spoof it."""
    out = []
    for td in tool_defs:
        if td.name in AUTHOR_TOOLS:
            schema = json.loads(json.dumps(td.parameters_json_schema))
            schema.get("properties", {}).pop("author", None)
            if "required" in schema:
                schema["required"] = [r for r in schema["required"] if r != "author"]
            td = replace(td, parameters_json_schema=schema)
        out.append(td)
    return out


class CampusCustomsTeam:
    """Use as `async with CampusCustomsTeam() as team:` so the MCP server starts once."""

    def __init__(self, audit: AuditLog | None = None, client=None):
        self.audit = audit or AuditLog()
        self.model = build_model()
        self.mcp = MCPToolset(
            client or mcp_client(),
            id="campus-customs",
            process_tool_call=self._inject_author,
            max_retries=AGENT_RETRIES,
        )
        self.agents: dict[AgentName, Agent[TeamDeps, Any]] = {
            name: self._build_agent(name) for name in AGENT_NAMES
        }

    async def __aenter__(self) -> CampusCustomsTeam:
        await self.mcp.__aenter__()
        return self

    async def __aexit__(self, *exc) -> None:
        await self.mcp.__aexit__(*exc)

    # ------------------------------------------------------------------ building

    def _build_agent(self, name: AgentName) -> Agent[TeamDeps, Any]:
        role = ROLES[name]
        allowed = AGENT_TOOLS[name]
        assert not allowed & HUMAN_ONLY_TOOLS, f"{name} must not get money tools"
        toolset = self.mcp.filtered(lambda ctx, td, allowed=allowed: td.name in allowed).prepared(
            _hide_author
        )
        teammates = "\n".join(
            f"- {other}: {ROLES[other].ask_me_about}" for other in AGENT_NAMES if other != name
        )
        ask_tool = Tool(
            self._ask_agent,
            name="ask_agent",
            description=(
                "Ask a Campus Customs teammate for help and wait for their answer. Give a specific "
                "question plus the facts you already have. Teammates:\n" + teammates
            ),
        )
        return Agent(
            self.model,
            name=name,
            instructions=(PROMPTS_DIR / role.prompt_file).read_text(),
            output_type=role.output_type,
            deps_type=TeamDeps,
            toolsets=[toolset],
            tools=[ask_tool],
            model_settings=OpenAIResponsesModelSettings(
                max_tokens=MAX_OUTPUT_TOKENS, openai_reasoning_effort=REASONING_EFFORT
            ),
            retries=AGENT_RETRIES,
        )

    async def _inject_author(self, ctx: RunContext[TeamDeps], call_tool, name: str, args: dict) -> Any:
        if name in HUMAN_ONLY_TOOLS:  # belt and braces: agents never see these anyway
            return {"error": f"{name} is for humans only."}
        if name in AUTHOR_TOOLS:
            args = {**args, "author": ctx.deps.agent}
        return await call_tool(name, args)

    # ------------------------------------------------------------------ delegation

    async def _ask_agent(self, ctx: RunContext[TeamDeps], teammate: AgentName, question: str) -> str:
        deps = ctx.deps
        refusal = None
        if teammate == deps.agent:
            refusal = "You can't delegate to yourself. Answer with your own tools."
        elif teammate in deps.chain:
            refusal = (
                f"{teammate} is already waiting on you (chain: {' -> '.join(deps.chain)}). "
                "Answer with what you have instead of asking them back."
            )
        elif deps.depth >= MAX_DELEGATION_DEPTH:
            refusal = "Delegation depth limit reached. Answer with what you have, or flag it for the Boss."
        elif deps.delegation_count["n"] >= MAX_DELEGATIONS_PER_TICKET:
            refusal = "This ticket has used its delegation budget. Wrap up with what you have."
        if refusal:
            await self.audit.record(deps, "delegation_refused", detail={"to": teammate, "question": question, "reason": refusal})
            return refusal

        key = (teammate, " ".join(question.lower().split()))
        if key in deps.answer_cache:
            await self.audit.record(deps, "delegation_cached", detail={"to": teammate, "question": question})
            return deps.answer_cache[key]

        deps.delegation_count["n"] += 1
        child = deps.for_teammate(teammate)
        await self.audit.record(deps, "delegation", detail={"to": teammate, "question": question})
        prompt = (
            f"Ticket #{deps.ticket_id}. Your teammate {deps.agent} asks:\n{question}\n\n"
            "Answer within your role, using your tools for every fact."
        )
        output = await self._run_agent(teammate, prompt, child, ctx.usage)
        answer = output.model_dump_json()
        deps.answer_cache[key] = answer
        return answer

    # ------------------------------------------------------------------ the agent loop

    async def _run_agent(self, name: AgentName, prompt: str, deps: TeamDeps, usage: RunUsage) -> Any:
        agent = self.agents[name]
        await self.audit.record(
            deps,
            "run_start",
            model=MODEL_NAME,
            detail={
                "prompt_file": f"backend/prompts/{ROLES[name].prompt_file}",
                "user_prompt": prompt,
                "tools": sorted(AGENT_TOOLS[name] | {"ask_agent"}),
            },
            usage=usage_dict(usage),
        )
        step = 0
        try:
            async with agent.iter(
                prompt, deps=deps, usage=usage, usage_limits=USAGE_LIMITS
            ) as run:
                async for node in run:
                    step += 1
                    await self._audit_step(deps, step, node, usage)
            output = run.result.output
        except Exception as exc:
            await self.audit.record(
                deps, "run_error", step=step, detail={"error": f"{type(exc).__name__}: {exc}"}, usage=usage_dict(usage)
            )
            raise
        await self.audit.record(
            deps, "run_end", step=step, detail={"output": output.model_dump()}, usage=usage_dict(usage)
        )
        return output

    async def _audit_step(self, deps: TeamDeps, step: int, node: Any, usage: RunUsage) -> None:
        if Agent.is_call_tools_node(node):
            resp = node.model_response
            await self.audit.record(
                deps,
                "model_response",
                step=step,
                model=MODEL_NAME,
                detail={
                    "provider_model": resp.model_name,
                    "tool_calls": [
                        {"tool": p.tool_name, "args": p.args_as_dict(), "call_id": p.tool_call_id}
                        for p in resp.parts
                        if isinstance(p, ToolCallPart)
                    ],
                    "text": " ".join(p.content for p in resp.parts if isinstance(p, TextPart)) or None,
                    "finish_reason": resp.finish_reason,
                    "response_tokens": {"input": resp.usage.input_tokens, "output": resp.usage.output_tokens},
                },
                usage=usage_dict(usage),
            )
        elif Agent.is_model_request_node(node):
            results = [
                {"tool": p.tool_name, "call_id": p.tool_call_id, "result": p.model_response_str()}
                for p in node.request.parts
                if isinstance(p, ToolReturnPart)
            ]
            retries = [
                {"tool": p.tool_name, "retry": p.model_response()}
                for p in node.request.parts
                if isinstance(p, RetryPromptPart)
            ]
            await self.audit.record(
                deps,
                "tool_results" if (results or retries) else "model_request",
                step=step,
                detail={"results": results, "retries": retries} if (results or retries) else {},
                usage=usage_dict(usage),
            )
        elif Agent.is_user_prompt_node(node):
            await self.audit.record(deps, "user_prompt", step=step, usage=usage_dict(usage))
        elif Agent.is_end_node(node):
            await self.audit.record(deps, "end", step=step, usage=usage_dict(usage))

    # ------------------------------------------------------------------ entry points

    def _new_deps(self, agent: AgentName, ticket_id: int | None, run_id: str | None = None) -> TeamDeps:
        return TeamDeps(
            run_id=run_id or new_run_id(), ticket_id=ticket_id, agent=agent, audit=self.audit, chain=[agent]
        )

    async def run_ticket(self, ticket_id: int, run_id: str | None = None) -> TicketRunResult:
        """The Boss takes one ticket from start to final decision."""
        deps = self._new_deps("boss", ticket_id, run_id)
        usage = RunUsage()
        prompt = (
            f"Handle ticket #{ticket_id}. Start with get_today and get_ticket, delegate the specialist "
            "work, set the final status with set_ticket_status, and return your decision."
        )
        try:
            decision = await self._run_agent("boss", prompt, deps, usage)
            return TicketRunResult(run_id=deps.run_id, ticket_id=ticket_id, decision=decision, usage=usage_dict(usage))
        except UsageLimitExceeded as exc:
            return TicketRunResult(
                run_id=deps.run_id, ticket_id=ticket_id, decision=None,
                error=f"Stopped by cost guardrail: {exc}", usage=usage_dict(usage),
            )

    async def open_ticket_ids(self) -> list[int]:
        """Read the board through MCP (no direct database access)."""
        result = await self.mcp.direct_call_tool("list_open_tickets", {})
        return [t["id"] for t in result["tickets"]]

    async def run_open_tickets(self) -> list[TicketRunResult]:
        """Run every open ticket, one at a time, oldest first (so cash decisions see earlier requests)."""
        return [await self.run_ticket(tid) for tid in await self.open_ticket_ids()]

    async def ask(self, agent: AgentName, question: str, ticket_id: int | None = None) -> Any:
        """Ask one agent a direct question (it may still delegate)."""
        deps = self._new_deps(agent, ticket_id)
        return await self._run_agent(agent, question, deps, RunUsage())

    async def read(self, tool: str, args: dict | None = None) -> Any:
        """For the dashboard: read-only lookups, via MCP."""
        if tool not in DASHBOARD_READ_TOOLS:
            raise ValueError(f"{tool} is not a dashboard read tool.")
        return await self.mcp.direct_call_tool(tool, args or {})

    async def human_call(self, tool: str, args: dict) -> Any:
        """For the human dashboard only: money and reset tools, via MCP."""
        if tool not in HUMAN_ONLY_TOOLS:
            raise ValueError(f"{tool} is not a human-only tool.")
        return await self.mcp.direct_call_tool(tool, args)
