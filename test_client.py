"""End-to-end test: talks to a running AllAtOnce server over Streamable
HTTP exactly the way an MCP host (Alexa+) would — initialize, list tools,
then drive the FULL demo arc turn by turn:

  1. plan_dinner          -> backward plan for 7:00, household facts applied
  2. get_cook_brief       -> Maya's jobs (hers include the gravy)
  3. complete_step        -> Maya finishes the mash, gets her next job
  4. report_delay         -> "the chicken's running fifteen behind"
  5. replan_dinner        -> serve protected (19:01), beans pushed,
                             mash on hold, gravy reassigned, trade-off spoken
  6. get_dinner_status    -> board state at 18:50 shows the mash holding
  7. get_cook_brief again -> Dad now owns the gravy; Maya no longer does

Usage: start `python server.py` first, then `python test_client.py`.
Exits non-zero if any expectation fails.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

URL = os.environ.get("MCP_URL", "http://127.0.0.1:8000/mcp")
failures: list[str] = []


def check(label: str, cond: bool, detail: str = "") -> None:
    print(f"  [{'PASS' if cond else 'FAIL'}] {label} {detail}")
    if not cond:
        failures.append(label)


def payload(result) -> dict:
    structured = getattr(result, "structured_content", None) or getattr(
        result, "structuredContent", None)
    if structured:
        return structured
    for block in result.content:
        if getattr(block, "type", None) == "text":
            return json.loads(block.text)
    raise RuntimeError(f"No parseable payload in result: {result!r}")


def dish(status: dict, dish_id: str) -> dict:
    return next(d for d in status["dishes"] if d["dish_id"] == dish_id)


def step_of(status: dict, dish_id: str, step_id: str) -> dict:
    return next(s for s in dish(status, dish_id)["steps"]
                if s["step_id"] == step_id)


async def main() -> int:
    async with streamable_http_client(URL) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            proto = getattr(init, "protocol_version", None) or getattr(
                init, "protocolVersion")
            print(f"protocolVersion negotiated: {proto}")
            check("protocol >= 2025-11-25", proto >= "2025-11-25",
                  f"({proto})")
            info = getattr(init, "server_info", None) or getattr(
                init, "serverInfo")
            print(f"server: {info.name} {info.version}")
            check("server is AllAtOnce", info.name == "AllAtOnce")

            tools = await session.list_tools()
            names = [t.name for t in tools.tools]
            print(f"tools: {names}")
            for expected in ("plan_dinner", "get_cook_brief", "complete_step",
                             "report_delay", "replan_dinner",
                             "get_dinner_status"):
                check(f"tool exposed: {expected}", expected in names)

            print("\nTurn 1 — 'Alexa, we're four for dinner at seven — roast "
                  "chicken, garlic mash, green beans, and Maya's doing her "
                  "gravy. Land it all at seven.'")
            r = payload(await session.call_tool("plan_dinner", {
                "dishes": ["roast chicken", "garlic mash", "green beans",
                           "gravy"],
                "serve_time": "19:00",
                "cooks": ["Dad", "Maya", "Sam"]}))
            print(json.dumps(r, indent=2))
            check("serve time 19:00", r["serve_time"] == "19:00")
            check("chicken starts 17:40 (backward plan)",
                  r["dishes"]["roast_chicken"]["starts"] == "17:40",
                  r["dishes"]["roast_chicken"]["starts"])
            check("household facts were used",
                  any("gravy" in f for f in r["household_facts_used"]))
            check("no cook conflicts in plan", r["cook_conflicts"] == [])

            print("\nTurn 2 — 'Alexa, what should Maya be doing?'")
            r = payload(await session.call_tool(
                "get_cook_brief", {"cook": "Maya"}))
            print(json.dumps(r, indent=2))
            check("Maya's current job is the potatoes",
                  r["current"]["step_id"] == "mash_peel")

            st = payload(await session.call_tool("get_dinner_status", {}))
            gravy_cook = step_of(st, "gravy", "gravy_roux")["cook"]
            check("gravy belongs to Maya in the plan (household fact)",
                  gravy_cook == "Maya", gravy_cook)
            beans_cook_start = step_of(
                st, "green_beans", "beans_steam")["start"]

            print("\nTurn 3 — Maya checks in as she goes: 'Alexa, the mash "
                  "is done.'")
            r = None
            for sid in ("mash_peel", "mash_boil", "mash_mash"):
                r = payload(await session.call_tool(
                    "complete_step", {"step_id": sid}))
            print(json.dumps(r, indent=2))
            check("mash marked complete", r["completed"] == "mash_mash")
            check("Maya's next job is the mash hold",
                  r["next_job_for_cook"]["step_id"] == "mash_hold",
                  str(r["next_job_for_cook"]))
            check("then the gravy at 18:45",
                  r["then"]["step_id"] == "gravy_roux", str(r["then"]))

            print("\nTurn 4 — Dad: 'Alexa, the chicken's running fifteen "
                  "behind.'")
            r = payload(await session.call_tool("report_delay", {
                "dish": "roast chicken", "minutes": 15, "now": "18:30"}))
            print(json.dumps(r, indent=2))
            check("delay recorded", r["delay_minutes"] == 15)
            check("naive projection slips to 19:15",
                  r["naive_projection"] == "19:15")

            print("\nTurn 5 — replan_dinner: re-solve the whole landing")
            r = payload(await session.call_tool("replan_dinner", {}))
            print(json.dumps(r, indent=2))
            check("serve time protected (19:01, slip <= 1)",
                  r["projected_serve_time"] == "19:01"
                  and r["serve_slip_minutes"] <= 1,
                  f"{r['projected_serve_time']} slip "
                  f"{r['serve_slip_minutes']}")
            check("at least 5 computed changes", len(r["changes"]) >= 5,
                  f"({len(r['changes'])})")
            actions = {(c["dish"], c["action"]) for c in r["changes"]}
            check("beans pushed via method switch",
                  ("green_beans", "method_switch") in actions)
            check("mash put on hold", ("garlic_mash", "hold") in actions)
            check("gravy reassigned", ("gravy", "reassign") in actions)
            check("spoken trade-off present, names 7:01",
                  "7:01" in r["trade_off_spoken"])
            check("confirmation requested", r["requires_confirmation"]
                  is True)
            check("no cook conflicts after re-plan",
                  r["cook_conflicts"] == [])

            print("\nTurn 6 — board state at 18:50, after the re-plan")
            st = payload(await session.call_tool(
                "get_dinner_status", {"now": "18:50"}))
            print(json.dumps(st, indent=2))
            check("projected serve on the board is 19:01",
                  st["projected_serve"] == "19:01")
            check("mash phase at 18:50 is holding",
                  dish(st, "garlic_mash")["phase"] == "holding",
                  dish(st, "garlic_mash")["phase"])
            check("mash hold stretched to 18 min",
                  step_of(st, "garlic_mash", "mash_hold")["duration"] == 18)
            check("beans cooking start pushed later",
                  step_of(st, "green_beans", "beans_pan_saute")["start"]
                  > beans_cook_start,
                  f"{step_of(st, 'green_beans', 'beans_pan_saute')['start']}"
                  f" > {beans_cook_start}")
            check("gravy cook is now Dad",
                  step_of(st, "gravy", "gravy_roux")["cook"] == "Dad")
            check("household memory recorded the landing",
                  st["household_last_dinner"]["projected_serve"] == "19:01")

            print("\nTurn 7 — briefs after the re-plan (chicken is out and "
                  "resting, so Dad checks in his first two steps)")
            for sid in ("chicken_prep", "chicken_roast"):
                await session.call_tool("complete_step", {"step_id": sid})
            dad = payload(await session.call_tool(
                "get_cook_brief", {"cook": "Dad"}))
            maya = payload(await session.call_tool(
                "get_cook_brief", {"cook": "Maya"}))
            print("Dad:", json.dumps(dad))
            print("Maya:", json.dumps(maya))
            dad_jobs = {dad["current"]["step_id"] if dad["current"] else "",
                        dad["next"]["step_id"] if dad["next"] else ""}
            check("Dad's queue now includes a gravy step",
                  any("gravy" in j for j in dad_jobs), str(dad_jobs))
            maya_jobs = {maya["current"]["step_id"] if maya["current"]
                         else "", maya["next"]["step_id"] if maya["next"]
                         else ""}
            check("Maya's queue no longer includes the gravy",
                  not any("gravy" in j for j in maya_jobs), str(maya_jobs))

    print("\nRESULT:", "ALL PASS" if not failures
          else f"{len(failures)} FAILURES: {failures}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
