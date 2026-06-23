"""One-off MCP client smoke test for NLearn Sentinel tools."""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]


def _preview(result) -> str:
    parts = []
    for block in result.content:
        text = getattr(block, "text", None)
        if text is not None:
            parts.append(text)
    body = "\n".join(parts) if parts else repr(result)
    return body if len(body) <= 1200 else body[:1200] + "\n... (truncated)"


async def main() -> int:
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[str(ROOT / "server.py")],
        cwd=str(ROOT),
    )

    failures = 0

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            print(f"Connected: {init.serverInfo.name} v{init.serverInfo.version}")

            tools = await session.list_tools()
            names = [t.name for t in tools.tools]
            print(f"Tools ({len(names)}): {', '.join(names)}")

            calls = [
                ("get_upcoming_deadlines", {"days": 14}),
                ("get_past_deadlines", {"days": 60}),
                ("get_deadlines_for_sync", {"days": 14}),
                (
                    "get_assignment",
                    {"assignment_url": "https://evil.example/mod/assign/view.php?id=1"},
                ),
                ("refresh_session", {}),
            ]

            for name, args in calls:
                print(f"\n--- {name} {args} ---")
                try:
                    result = await session.call_tool(name, args)
                    if result.isError:
                        failures += 1
                        print("ERROR:", _preview(result))
                    else:
                        print(_preview(result))
                except Exception as exc:
                    failures += 1
                    print(f"EXCEPTION: {exc}")

    return failures


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
