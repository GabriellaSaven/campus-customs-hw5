"""Check that every tool named in backend/prompts/*.md really exists and that
each agent is actually given the tools its prompt tells it to use.

- Lists the tools from the live MCP server (launched from .mcp.json).
- Pulls every `backticked_name` out of each prompt.
- Each name must be an MCP tool, the backend's `ask_agent`, or a known
  non-tool term (ticket statuses, field names).
- Each tool a prompt names must be in that agent's allowlist, and every
  allowlisted tool must exist on the server. No agent may get a money tool.
"""

import asyncio
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.agents import ROLES  # noqa: E402
from backend.config import AGENT_TOOLS, HUMAN_ONLY_TOOLS, PROMPTS_DIR  # noqa: E402
from backend.mcp_client import mcp_client  # noqa: E402

BACKEND_TOOLS = {"ask_agent"}
NON_TOOL_TERMS = {"in_progress", "awaiting_approval", "escalated", "resolved", "lead_days"}


async def main() -> int:
    async with mcp_client() as client:
        server_tools = {t.name for t in await client.list_tools()}
    problems = []
    print(f"MCP server tools ({len(server_tools)}): {', '.join(sorted(server_tools))}\n")

    for agent, allowed in AGENT_TOOLS.items():
        if missing := allowed - server_tools:
            problems.append(f"{agent}: allowlisted tools missing from MCP server: {sorted(missing)}")
        if money := allowed & HUMAN_ONLY_TOOLS:
            problems.append(f"{agent}: has human-only tools {sorted(money)}")

    for agent, role in ROLES.items():
        text = (PROMPTS_DIR / role.prompt_file).read_text()
        named = set(re.findall(r"`([a-z][a-z0-9_]*)`", text)) - NON_TOOL_TERMS
        unknown = named - server_tools - BACKEND_TOOLS
        not_given = (named & server_tools) - AGENT_TOOLS[agent]
        print(f"{role.prompt_file:<22} names {len(named):>2} tools: {', '.join(sorted(named))}")
        if unknown:
            problems.append(f"{role.prompt_file}: names tools that don't exist: {sorted(unknown)}")
        if not_given:
            problems.append(f"{role.prompt_file}: names tools the agent isn't given: {sorted(not_given)}")

    print()
    if problems:
        print("PROBLEMS:\n- " + "\n- ".join(problems))
        return 1
    print("OK: every tool named in the prompts exists on the MCP server and is given to that agent.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
