# AllAtOnce — Devpost Filing Prep (DRAFT — do not file yet)

Hackathon: **Build, Ship, Shape: Amazon Developer Hackathon** (Devpost)
Deadline: **Fri Oct 23, 2026, 3:00 PM EDT** (rules: 12:00 PM PT)
Entrant: Quincy Goertz-Brown, solo, participant 51,993.
**Track: Alexa+** · **Mini-challenge: Open Source** (this repo is new,
MIT-licensed, public — matches its required fields). AWS Builder
mini-challenge: **skip** — no AWS service is used; adding one for the
badge is exactly the "obvious" pattern the rules contrast against.

**Repo:** https://github.com/QuincyGB/allatonce — PUBLIC, MIT license
detected by GitHub, anonymous access verified (HTTP 200) 2026-10-19.
**Live URL:** **[LIVE URL]** — not deployed yet. Render Blueprint
(`render.yaml` is in the repo) still needs Quincy to apply it from his
Render account: Render Dashboard → New → Blueprint → connect
`QuincyGB/allatonce` → Apply. Expected URL pattern:
`https://allatonce.onrender.com` (name-dependent; NOT live as of this
update — `/health` returned 404). No environment variables are needed:
the app only reads `$PORT` (Render sets it) and an optional state-path
override with a default.
**Video URL:** **[VIDEO URL]** — to be recorded per DEMO-SCRIPT.md and
uploaded public to YouTube/Vimeo by Quincy.
**Project image:** `project-image.png` in the repo root — a screenshot
of the real Echo Show board after the demo re-plan (projected serve
19:01, delay banner, 9 computed changes), captured 2026-10-19 with
headless Chromium against the running server. Devpost asks for a
project image at filing; use this file.
**Rules re-verification (audit, 2026-10-19):** the live Devpost page
and official rules were re-fetched and diffed against this file the
same day — deadline Fri Oct 23, 2026 12:00 PM PT (= 3:00 PM EDT),
video < 3 min public YouTube/Vimeo in English, product feedback
mandatory per tool/API/SDK, repo public with detectable license (or
private + named reviewers), Alexa+ = MCP spec 2025-11-25+ over
Streamable HTTP, Open Source mini-challenge fields (contribution URL,
repo URL, GitHub username, description), project free for judges until
the judging period ends (Nov 9–20 PT), Ontario eligible (Quebec
excluded). **No mismatches found.** The rules' AWS-credit request
form closes Oct 21 but codes were exhausted Oct 7 — irrelevant here,
no AWS service is used.

---

## Open Source mini-challenge fields (draft)

- **Contribution URL:** https://github.com/QuincyGB/allatonce
- **Project repository URL:** https://github.com/QuincyGB/allatonce
- **GitHub username:** QuincyGB
- **Description:** AllAtOnce is a brand-new open-source project (MIT),
  created during the hackathon window: a self-hosted MCP server
  (spec 2025-11-25, Streamable HTTP) that plans a multi-dish,
  multi-cook dinner backwards from serve time and re-plans the whole
  landing when a dish runs late. It matters because it is a complete,
  tested reference for the pattern this track asks for — a *stateful,
  agentic* MCP workflow (91 automated checks, including honest-slip
  and robustness suites) rather than a stateless API wrapper — and any
  developer can clone it, run it in minutes, and adapt the scheduling
  engine to their own multi-step household workflow.

## Built with

- Python 3.12
- MCP Python SDK (`mcp[cli]` == 2.3.0, pinned) — MCP spec 2025-11-25,
  Streamable HTTP transport
- Starlette (via the SDK's `custom_route` — the board/status/health
  HTTP routes in `server.py`)
- Plain HTML/CSS/JS (the Echo Show board, `board.html`)
- Render free tier (hosting, via the committed `render.yaml`
  Blueprint) — **[planned; LIVE URL pending Quincy's Blueprint click]**
- GitHub (public repo, MIT)

---

## Project name

**AllAtOnce — the dinner conductor**

## One-liner

Alexa+ plans a multi-dish, multi-cook dinner backwards from serve time,
gives every cook their next job, and re-plans the whole landing when
something runs late.

## Description (draft)

Alexa already does timers. Timers don't re-plan dinner when the chicken's
late.

AllAtOnce is a self-hosted MCP server (MCP spec 2025-11-25, Streamable
HTTP, official Python MCP SDK) that turns Alexa+ into a dinner
conductor. You say: *"We're four for dinner at seven — roast chicken,
garlic mash, green beans, and Maya's doing her gravy. Land it all at
seven."* AllAtOnce backward-schedules every dish from serve time —
steps, dependencies, cook assignments, freshness windows — reading
household memory as it plans (who always does the gravy, how long the
chicken rests in this house). Each cook hears only their own next job.
The Echo Show board shows every dish bar converging on one SERVE line.

Then life happens: *"The chicken's running fifteen behind."* A
backward-only planner would cheat by quietly moving the start time.
AllAtOnce re-schedules the delayed dish **forward** from its real start,
applies real recovery actions (a high-heat finish, a trimmed rest, a
parallelised carve with tonight's guest), then cascades: the gravy
follows its drippings to the cook at the stove and is served straight
from the pan, the mash extends its hold and is rewhipped at the last
call, the beans switch to a single-pan method so their cook can set the
table. Alexa+ reads the trade-off out loud and asks for a yes. Dinner
lands at **7:01** instead of 7:15 — and when a delay is too big to
absorb, AllAtOnce says so honestly (unit-tested: +30 minutes lands
7:16, admitted in the spoken summary).

**Tools:** `plan_dinner`, `get_cook_brief`, `complete_step`,
`report_delay`, `replan_dinner`, `get_dinner_status` — plus the Show
board at `/board` on the same app.

**What's real:** the scheduling/re-planning engine is genuine
constraint recomputation (91 automated checks pass: backward plans,
dependency shifts, honest slips at +5/+15/+30 minutes, household-memory
mutation, and a robustness suite for off-script inputs). The recipe data is a small curated step-graph set by design —
AllAtOnce is bring-your-own dishes; the step graph is the data model.
The demo's MCP client stands in for the Alexa+ host because no
entrant-facing Alexa+ test harness was available to verify against.

## Mandatory product feedback (draft, per tool/SDK used)

### 1. MCP Python SDK (`mcp[cli]` 2.3.0)
- **Used for:** the entire server — six tools over Streamable HTTP, plus
  `/board`, `/status`, `/health` routes on the same app.
- **What worked:** one decorator per tool; protocol 2025-11-25
  negotiated cleanly with the SDK's own client; stateless JSON mode made
  local testing and the recorded end-to-end test trivial; `custom_route`
  let the Show board live on the same port/app as `/mcp`, which matters
  on single-port free hosting.
- **What needs work:** (a) SDK 2.x renamed `FastMCP` → `MCPServer` and
  moved the module — nearly every tutorial and search result still
  teaches the v1 API, so the first hour of this build was archaeology
  (see friction log 1). (b) Building a *stateful* workflow (a dinner
  that mutates across calls) on the *stateless* HTTP transport has no
  documented pattern — we managed session state server-side and
  persisted it to JSON ourselves; a short "stateful tools on stateless
  transport" guide would help every agentic-workflow entrant. (c) Which
  protocol versions the installed SDK supports is not surfaced in the
  README; we confirmed 2025-11-25 by grepping the installed package.
- **Would I build again?** Yes — once on the v2 API, it was fast and
  the client/server symmetry made testing honest.

### 2. Alexa+ MCP / Agent Skills documentation (hackathon resources page)
- **Used for:** the track requirement itself — self-hosted MCP server,
  spec 2025-11-25+, Streamable HTTP; the resources page's links to the
  MCP open-standard docs.
- **What worked:** the requirement is crisply stated, and pointing at
  the open standard (rather than a proprietary SDK) let us build and
  test everything locally with the reference client.
- **What needs work:** there is no entrant-facing way to test an MCP
  server against real Alexa+ before judging — no Preview harness or
  hosted simulator was linked from the resources page that we could
  verify. Our demo therefore uses a real MCP client standing in for the
  Alexa+ host (the sanctioned simulated-experience fallback covers the
  conversation view). **Feature request:** a hosted "Alexa+ MCP test
  harness" — paste an endpoint URL, run scripted turns, see the exact
  requests Alexa+ would send. It would raise the floor for the whole
  track.
- **Would I build again?** Yes — the MCP-first direction is right; the
  missing piece is the test loop, not the model.

### 3. Starlette (used directly in `server.py` for the HTTP routes)
- **Used for:** `Request`/`HTMLResponse`/`JSONResponse` behind the
  SDK's `custom_route` — the Echo Show board (`/board`), its data
  (`/status`), and `/health`, all on the same app/port as `/mcp`.
- **What worked:** it disappeared into the SDK's routing; the three
  routes took a few lines each and the board could poll plain JSON.
- **What needs work:** nothing hit in this build; the only friction
  was discovering the pattern (friction log 4, filed under the SDK).
- **Would I build again?** Yes — for a single-port demo surface next
  to an MCP endpoint, it's the obvious fit.

### 4. MCP specification / Streamable HTTP transport docs (modelcontextprotocol.io)
- **Used for:** transport semantics, tool schema shape, session behaviour.
- **What worked:** the spec is precise; the stateless + JSON-response
  mode is well-defined and our client/server agreed on the first run.
- **What needs work:** the docs' examples skew to v1-era SDK APIs (see
  friction log 1); a "current version" banner would save every new
  entrant the same hour.

## Friction log (for the optional bonus section)

1. **Task:** install the Python MCP SDK and write a first server.
   Steps: `pip install mcp[cli]`, followed current tutorials using
   `from mcp.server.fastmcp import FastMCP`. Expected: import works.
   Actual: SDK 2.x removed that module — FastMCP renamed to `MCPServer`
   (`mcp.server.mcpserver`), client now yields 2 streams not 3, result
   fields are snake_case. Severity: medium. Workaround: read the
   installed package + its migration note and rewrote to the v2 API.
   Suggestion: pin a "current version" banner + v2-first examples on
   the MCP getting-started docs the hackathon links to.
2. **Task:** confirm which protocol versions the installed SDK supports.
   Expected: a documented constant. Actual: had to grep the installed
   package (`mcp/shared/dispatcher.py`) to confirm 2025-11-25 support.
   Severity: low. Suggestion: surface supported protocol versions in
   the SDK README.
3. **Task:** keep dinner state across tool calls on the stateless
   Streamable HTTP transport (the recommended hosting-friendly mode).
   Expected: a session pattern in the SDK docs. Actual: stateless mode
   has no server-side session to hang state on; we kept the session in
   the server process and persisted household memory to a JSON file
   ourselves. Severity: medium for any stateful/agentic entry — which
   is what the track asks for. Suggestion: document the pattern
   (process state + durable store + session id argument) in the SDK's
   Streamable HTTP guide.
4. **Task:** serve the Echo Show board from the same app/port as the
   MCP endpoint. Expected: routing docs. Actual: `custom_route` exists
   and works with `run()`, but we confirmed that by reading the SDK's
   method list/source, not from docs. Severity: low. Suggestion: one
   docs page — "adding plain HTTP routes next to /mcp".

## Remaining checklist

- [x] Concept locked by Quincy (AllAtOnce, 2026-10-19)
- [x] Working MCP server + engine + board, tested end-to-end (91 checks)
- [x] End-to-end audit passed (2026-10-19, see AUDIT.md in the repo)
- [x] Project image created (`project-image.png`, real board screenshot)
- [x] Demo script written from real server output (DEMO-SCRIPT.md)
- [ ] Deploy server to Render (free tier) at a public HTTPS URL;
      re-run `test_client.py` against the public URL (`MCP_URL=...`).
      `render.yaml` Blueprint is committed; **Quincy:** apply it in
      Render (Dashboard → New → Blueprint → `QuincyGB/allatonce`).
- [ ] Record demo video < 3 min per DEMO-SCRIPT.md; slow pacing
- [x] Public GitHub repo created and pushed (2026-10-19, with Quincy's
      approval — Ren via `gh`, repo `QuincyGB/allatonce`, MIT LICENSE
      in place, anonymous HTTP 200 + GitHub license detection verified)
- [ ] **Quincy:** upload the demo video, public, to YouTube/Vimeo
- [ ] Paste description + product feedback (above) into the Devpost form
- [ ] **Track selected: Alexa+** · Mini-challenge: **Open Source**
      (+ its fields: contribution URL = repo, GitHub username,
      description)
- [ ] Paste friction log (above) in the optional section
- [ ] Feature request field: hosted Alexa+ MCP test harness (above)
- [ ] "New project" — no pre-existing-project explanation needed
- [ ] **Quincy: final Submit click** before Fri Oct 23, 2026 3:00 PM EDT
      (file in the morning); screenshot the submitted page

## Exact remaining steps, in order (the moment Render + video exist,
## the submission can be completed with no further build work)

1. **Quincy:** Render Dashboard → New → Blueprint → connect
   `QuincyGB/allatonce` → Apply. (No env vars to set.)
2. **Ren:** verify the live deployment — `GET /health`, run
   `MCP_URL=[LIVE URL]/mcp python test_client.py` (expect ALL PASS),
   load `[LIVE URL]/board`; record results in the repo.
3. **Ren:** record the demo video from DEMO-SCRIPT.md (< 3 min;
   247 spoken words ≈ 2:34 of speech at the house pacing).
4. **Quincy:** upload the video, public, to YouTube or Vimeo →
   **[VIDEO URL]**.
5. **Ren (draft) / Quincy (logged-in paste):** create the Devpost
   project: name + one-liner + description (above), repo URL,
   **[LIVE URL]**, **[VIDEO URL]**, project image
   (`project-image.png`), built-with list (above).
6. **Same form:** track = **Alexa+**; mini-challenge = **Open Source**
   (contribution URL = repo URL = https://github.com/QuincyGB/allatonce,
   GitHub username = QuincyGB, description from the Open Source fields
   above); product feedback (all four tools, above); friction log
   (above); feature request (hosted Alexa+ MCP test harness, marked
   Important); "existed before the hackathon" = No / new project.
7. **Quincy: final Submit click** — Fri Oct 23, 2026, file in the
   morning, hard deadline 3:00 PM EDT. Screenshot the submitted page.
