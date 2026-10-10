"""Connect to the Campus Customs MCP server exactly as .mcp.json describes it.

All shop facts reach the agents through this connection; there is no second,
direct path to the database.
"""

import json
import os
import re

from fastmcp import Client

from backend.config import MCP_CONFIG, MCP_SERVER_NAME, ROOT


def _expand(value: str, env: dict) -> str:
    """Expand ${VAR} and ${VAR:-default} the same way Claude Code does in .mcp.json."""
    return re.sub(
        r"\$\{(\w+)(?::-([^}]*))?\}",
        lambda m: env.get(m.group(1)) or (m.group(2) or ""),
        value,
    )


def server_config() -> dict:
    """The .mcp.json entry for our server, resolved for this machine."""
    entry = json.loads(MCP_CONFIG.read_text())["mcpServers"][MCP_SERVER_NAME]
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(ROOT)}
    return {
        **entry,
        "command": _expand(entry["command"], env),
        "args": [_expand(a, env) for a in entry.get("args", [])],
        "env": {**entry.get("env", {}), "CLAUDE_PROJECT_DIR": str(ROOT)},
        "cwd": str(ROOT),
    }


def mcp_client() -> Client:
    """A FastMCP client that launches the server over stdio."""
    return Client({"mcpServers": {MCP_SERVER_NAME: server_config()}})
