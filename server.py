"""AllAtOnce — self-hosted MCP server for the Alexa+ track.

Build, Ship, Shape: Amazon Developer Hackathon (Devpost).
Track requirement: a self-hosted MCP server implementing MCP spec
2025-11-25 or later over Streamable HTTP, with the MCP technology actually
called at runtime — this file serves the six dinner-conductor tools at
POST /mcp using the official Python MCP SDK.

It also serves the Echo Show board on the same app:
    GET /board   — the glanceable dinner board (HTML)
    GET /status  — the board's data as JSON (same model as get_dinner_status)

Run:
    python server.py            # http://127.0.0.1:8000/mcp + /board
    PORT=9000 python server.py  # hosting platforms set $PORT

Test against it:
    python test_client.py
"""

from __future__ import annotations

import os

from mcp.server.mcpserver import MCPServer
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse

import schedule

mcp = MCPServer(
    "AllAtOnce",
    instructions=(
        "AllAtOnce is a dinner conductor for Alexa+. It plans a multi-dish, "
        "multi-cook dinner backwards from the serve time, gives each cook "
        "their next job, tracks progress by voice, and re-plans the whole "
        "landing when something runs late. Use plan_dinner to build the "
        "plan, get_cook_brief for one cook's next job, complete_step when "
        "a cook finishes a step, report_delay when something slips, "
        "replan_dinner to re-solve the landing, and get_dinner_status for "
        "the board."
    ),
    version="0.1.0",
)


@mcp.tool()
def plan_dinner(dishes: list[str] | None = None, serve_time: str = "19:00",
                cooks: list[str] | None = None,
                household_id: str = "") -> dict:
    """Plan a dinner backwards from serve time.

    dishes: dish names, e.g. ['roast chicken', 'garlic mash', 'green
    beans', 'gravy'] (default: the household's four demo dishes).
    serve_time: '19:00' or '7:00 PM'.
    cooks: who is cooking (default: the household members on file).
    Reads household memory (who always does the gravy, how long the
    chicken rests) and returns the backward schedule + first jobs.
    """
    return schedule.plan_dinner(dishes, serve_time, cooks, household_id)


@mcp.tool()
def get_cook_brief(cook: str) -> dict:
    """One cook's current and next step only — voice-first brevity."""
    return schedule.get_cook_brief(cook)


@mcp.tool()
def complete_step(step_id: str) -> dict:
    """Mark a step done (e.g. 'mash_mash') and get that cook's next job."""
    return schedule.complete_step(step_id)


@mcp.tool()
def report_delay(dish: str, minutes: int, now: str = "18:30") -> dict:
    """Record that a dish (e.g. 'roast chicken') is running `minutes` late.

    `now` is the current kitchen time for the demo scenario.
    Follow with replan_dinner to re-solve the landing.
    """
    return schedule.report_delay(dish, minutes, now)


@mcp.tool()
def replan_dinner(session_id: str = "") -> dict:
    """Recompute the whole dinner after a reported delay.

    Applies the delayed dish's recovery actions, reassigns steps to
    protect the landing, extends holds, switches methods where needed,
    and returns the changes, the honest projected serve time, and the
    spoken trade-off summary Alexa+ reads out to get a yes.
    """
    return schedule.replan_dinner(session_id)


@mcp.tool()
def get_dinner_status(session_id: str = "", now: str = "") -> dict:
    """The full board state: per-dish timelines, phases, each cook's next
    job, household facts in play, and (after a re-plan) the changes."""
    return schedule.get_dinner_status(session_id, now)


@mcp.custom_route("/status", methods=["GET"])
async def status_route(request: Request) -> JSONResponse:
    """Plain-JSON twin of get_dinner_status for the Show board."""
    return JSONResponse(
        schedule.get_dinner_status("", request.query_params.get("now", "")))


@mcp.custom_route("/board", methods=["GET"])
async def board_route(request: Request) -> HTMLResponse:
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "board.html")) as f:
        return HTMLResponse(f.read())


@mcp.custom_route("/health", methods=["GET"])
async def health_route(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok", "service": "allatonce"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=port,
        stateless_http=True,
        json_response=True,
    )
