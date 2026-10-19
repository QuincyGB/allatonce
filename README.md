# AllAtOnce — the dinner conductor

**Alexa+ doesn't just time dinner — it *lands* it.**

Tell Alexa+ who's eating, what's cooking, and when you want to sit down.
AllAtOnce builds the plan **backwards from serve time**, gives every cook
their next job, tracks progress by voice — and when the chicken runs late,
it **re-plans the whole landing** instead of letting three dishes die
waiting.

> Alexa already does timers. **Timers don't re-plan dinner when the
> chicken's late.**

Built for the **Alexa+ track** of *Build, Ship, Shape: Amazon Developer
Hackathon* (Devpost). Self-hosted MCP server, MCP spec **2025-11-25**,
Streamable HTTP, official Python MCP SDK.

---

## The demo scenario (one dinner, ~3 minutes)

> "Alexa, we're four for dinner at seven — roast chicken, garlic mash,
> green beans, and Maya's doing her gravy. Land it all at seven."

1. `plan_dinner` backward-schedules all four dishes to 7:00, reading
   household memory (Maya always does the gravy; chicken rests 10 minutes
   in this house). The Echo Show board appears: dish bars converging on
   one SERVE line.
2. Cooks check in by voice (`get_cook_brief`, `complete_step`). Maya
   finishes the mash and gets her next job.
3. **The payoff:** "Alexa, the chicken's running fifteen behind."
   `report_delay` → `replan_dinner` re-solves the landing: the chicken
   finishes at high heat and rests 7 instead of 10, tonight's guest Alex
   gets a job helping carve, the gravy moves from Maya to Dad and is
   served straight from the pan, the mash goes on hold and is rewhipped
   at the last call, and the beans switch to a single pan so Sam can set
   the table. Alexa+ reads the trade-off out loud and asks for a yes.
   **Dinner lands at 7:01** — one honest minute past seven, instead of
   7:15 with no re-plan.

Full script: [DEMO-SCRIPT.md](DEMO-SCRIPT.md). Full test run:
[test-output.txt](test-output.txt).

## How the re-plan actually works

This is a real recomputation, not a timer offset:

- **Backward planning.** Each dish is a step graph (durations,
  dependencies, cook assignments, active/passive steps, minimum
  compressible durations, freshness windows). Dishes are scheduled
  backwards from serve time; cross-dish dependencies are honoured —
  gravy cannot start before the chicken roast releases its drippings,
  and if a dependency pushes a dish late, the slip is reported, never
  hidden.
- **Forward repair.** A delay is reported mid-cook, so the delayed dish
  is re-scheduled *forward* from its real start (a backward-only planner
  would cheat by quietly moving the start earlier). Recovery actions
  apply in order: a high-heat finish recovers a modelled fraction of
  the slip, the rest trims to its minimum, carving is parallelised with
  a helper. Whatever cannot be absorbed becomes an **honest slip** —
  tell it the chicken is 30 minutes behind and AllAtOnce will tell you
  dinner lands at 7:16, not pretend otherwise (this is unit-tested).
- **Cascade.** Dependent dishes follow their inputs (gravy follows the
  drippings, compresses, and is served from the pan), flexible dishes
  extend their holds (the mash), and constrained dishes change method
  (the beans go single-pan). Cook conflicts are re-validated after
  every re-plan.
- **Household memory.** `household.json` holds remembered facts — who
  does the gravy, how long the chicken rests, who usually sets the
  table. `plan_dinner` genuinely reads them (change the rest to 12 in
  memory and the chicken starts 2 minutes earlier — also unit-tested),
  and every landing is written back as plan-vs-actual.

## Tools (MCP)

| Tool | What it does |
|---|---|
| `plan_dinner(dishes, serve_time, cooks, household_id)` | Backward-schedule the dinner from serve time using household memory; returns the plan + first jobs |
| `get_cook_brief(cook)` | One cook's current + next step only (voice-first brevity) |
| `complete_step(step_id)` | Mark a step done; returns that cook's next job |
| `report_delay(dish, minutes, now)` | Record a slip; returns the naive (un-repaired) projection |
| `replan_dinner(session_id)` | Recompute the whole landing; returns computed changes, honest projected serve time, and the spoken trade-off summary |
| `get_dinner_status(session_id, now)` | Full board state: timelines, phases, per-cook jobs, facts in play |

Plus plain HTTP on the same app: `GET /board` (the Echo Show board),
`GET /status` (the board's JSON), `GET /health`.

## Run it locally

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python server.py            # MCP at http://127.0.0.1:8000/mcp
                                      # board at http://127.0.0.1:8000/board
PORT=9000 .venv/bin/python server.py  # hosting platforms set $PORT
```

Test it:

```bash
.venv/bin/python test_schedule.py     # pure-logic engine tests (no server)
.venv/bin/python test_client.py       # full demo arc over Streamable HTTP
                                      # (server must be running)
```

Latest recorded run: **66 checks, ALL PASS** — see
[test-output.txt](test-output.txt).

## Layout

```
server.py        MCP wiring (6 tools) + /board, /status, /health routes
schedule.py      scheduling + re-planning engine (pure logic, tested)
household.json   household memory seed (facts the planner reads)
board.html       the Echo Show board (polls /status)
test_client.py   end-to-end MCP client driving the full demo arc
test_schedule.py unit tests for the engine, incl. honest-slip cases
state.json       runtime state (generated; gitignored)
```

## Honest limitations

- The recipe set is a small curated set of step graphs — by design.
  AllAtOnce is bring-your-own dishes: the step graph is the data model,
  not a recipe catalogue. Adding a dish means adding its steps, not
  scraping a cookbook site.
- There is no entrant-facing live Alexa+ test harness we could verify,
  so the demo path is a real MCP client (the test client) standing in
  for the Alexa+ host, plus the board a Show would render. The MCP
  server itself is the real thing, speaking spec 2025-11-25.
- The high-heat recovery is a modelled heuristic (recovers 60% of a
  slip, capped at 9 minutes) — stated in the recipe data, not hidden.
- One active dinner per server process; household state persists to
  `state.json` on disk.

## License

MIT — see [LICENSE](LICENSE).
