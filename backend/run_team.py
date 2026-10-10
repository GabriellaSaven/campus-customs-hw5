"""Command-line runner for the Campus Customs team.

    .venv/bin/python -m backend.run_team --ticket 101
    .venv/bin/python -m backend.run_team --all --reset      # full run from the original data
    .venv/bin/python -m backend.run_team --ask inventory "Do we have CC-TEE-WHITE in S?" --ticket 101
    .venv/bin/python -m backend.run_team --reset            # reset only
"""

import argparse
import asyncio
import json

from backend.agents import CampusCustomsTeam
from backend.models import AGENT_NAMES


async def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--reset", action="store_true", help="restore the working DB from the original first")
    p.add_argument("--ticket", type=int, help="ticket id to run (or context for --ask)")
    p.add_argument("--all", action="store_true", help="run every open ticket, oldest first")
    p.add_argument("--ask", nargs=2, metavar=("AGENT", "QUESTION"), help="ask one agent directly")
    args = p.parse_args()

    async with CampusCustomsTeam() as team:
        if args.reset:
            print(json.dumps(await team.human_call("reset_shop_database", {"confirm": True}), indent=2))
        if args.ask:
            agent, question = args.ask
            if agent not in AGENT_NAMES:
                p.error(f"agent must be one of {AGENT_NAMES}")
            print((await team.ask(agent, question, args.ticket)).model_dump_json(indent=2))
        elif args.all:
            for result in await team.run_open_tickets():
                print(result.model_dump_json(indent=2))
        elif args.ticket is not None:
            print((await team.run_ticket(args.ticket)).model_dump_json(indent=2))
        elif not args.reset:
            p.print_help()


if __name__ == "__main__":
    asyncio.run(main())
