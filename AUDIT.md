# AllAtOnce — End-to-End Submission Audit

Date: **2026-10-19** (EDT). Auditor: Ren, at Quincy's order ("make sure
you've made this submission bullet proof end to end"). Scope: rules,
code, repo, docs, demo script, filing package. Out of scope (per
order): Devpost submission, video upload, Render deploy (blocked on
Quincy's Blueprint click — everything around it is ready).

Audited code HEAD: **9102366** (this AUDIT.md commit is docs-only on
top of it). Repo: https://github.com/QuincyGB/allatonce

Verdict per item: **PASS** / **FIXED** (what changed) / **FAIL-BLOCKED**.

---

## 1. Rules re-verification — PASS

Re-fetched TODAY (2026-10-19) via text fetch of the live pages:
`amazonappdev2026.devpost.com` and `amazonappdev2026.devpost.com/rules`.
Confirmed against FILING-PREP.md:

- Deadline: submission period ends Fri Oct 23, 2026, 12:00 PM PT
  (= 3:00 PM EDT); the Devpost event listing shows the window ending
  2026-10-23T15:00-04:00. Submission still open today.
- Alexa+ track: working self-hosted MCP server, MCP spec **2025-11-25
  minimum**, over **Streamable HTTP**; repo must call the track tech
  at runtime (ours does — `server.py` serves the tools at `/mcp`).
- Required: text description; GitHub repo with all source + run
  instructions, public with a **detectable open-source license** (or
  private + testing@devpost.com + the 6 named Amazon reviewers);
  demo video **< 3 minutes**, public on **YouTube or Vimeo**, English,
  no third-party trademarks/copyrighted music without permission;
  **product feedback for every tool/API/SDK used** (used-for / worked
  / needs-work / onboarding / build-again); track + mini-challenge
  selection; Open Source mini-challenge extra fields (contribution
  URL, repo URL, GitHub username, description); pre-existing-project
  explanation if applicable (n/a — new project); feature requests
  optional; friction log optional, worth up to a **10% judging bonus**.
- Eligibility: age of majority, Ontario fine (Quebec excluded);
  project must be free for judges until the judging period ends
  (Nov 9–20, 2026 PT); all materials in English. Judging: Stage 1
  pass/fail, Stage 2 four equally weighted criteria.
- **Diff vs FILING-PREP.md: no mismatches.** One rules note added to
  FILING-PREP for completeness: the AWS-credit request form closes
  Oct 21 but codes were exhausted Oct 7 (rules page, Oct 7 update) —
  irrelevant, no AWS service is used and the AWS Builder
  mini-challenge stays skipped.

## 2. Fresh-clone judge test — FIXED, then PASS

First pass friction (found and fixed before the final clone):

- `requirements.txt` was `mcp[cli]>=2.0` — **unpinned**. A future SDK
  3.x could break the v2 API this code uses (exactly the break that
  cost an hour in Round 1). **Pinned to `mcp[cli]==2.3.0`.**
- README test steps didn't say the client runs against a server in
  another terminal, and didn't mention `MCP_URL` for testing a
  deployed instance. **Both clarified.**

Final verification — anonymous `git clone` of
`https://github.com/QuincyGB/allatonce` into a temp dir at 9102366,
README followed exactly (`python3 -m venv .venv`,
`pip install -r requirements.txt` → mcp **2.3.0**,
`python server.py`, both suites):

- `test_schedule.py`: **56 PASS, 0 FAIL**, exit 0
- `test_client.py` (server on :8000): **35 PASS, 0 FAIL**, exit 0;
  `protocolVersion negotiated: 2025-11-25`; `/health` returned
  `{"status":"ok","service":"allatonce"}`; `/board` HTTP 200.

## 3. Claim-check — FIXED (3 drifts), rest verified

Every factual claim in README.md, DEMO-SCRIPT.md, and the FILING-PREP
description was extracted and checked against code + the fresh run
(91 checks) + the rules:

- **"66 checks"** — was true for the original build; after the
  robustness suite the real number is **91** (56 + 35). `test-output.txt`
  regenerated from the final code and **all documents updated to 91**.
- Demo script Beat 1 quoted the plan summary with "6:00" — the server
  said "18:00". Root cause fixed in code: the plan summary now speaks
  step times in 12-hour form (a voice assistant should never say
  "17:40"), and the script quotes the real output ("…at 6 o'clock"),
  **58 words** (annotation said 55 — fixed).
- Trade-off quote: script annotation said 72 words; the verbatim
  string (character-identical to the fresh run) is **73 words** — fixed.
- Verified exact: 7:01 landing after chicken +15 (naive 7:15);
  +30 → **19:16** honest slip, admitted in the spoken summary; +5 →
  fully absorbed (19:00); 6 tools; spec 2025-11-25; gravy Maya→Dad in
  the re-plan; mash hold 14→18 min; beans start 18:49→18:53;
  **9 computed changes** (also counted in the rendered board DOM);
  Alexa+ prizes/track statements in FILING-PREP match the live rules;
  "MIT" license statement matches GitHub's detection.

## 4. Robustness / judge-poking — FIXED (8 bugs), all re-tested

The running server was probed over real MCP calls + HTTP. Before the
fixes, this is what a judge could hit; every item now returns a
graceful, spoken-style error and **no** exception/500:

| Probe | Before | After |
|---|---|---|
| Re-plan the same delay twice | silently re-applied it (19:10 → 19:20, absorbed −10) | error: already re-planned; projected serve unchanged |
| `now="banana"` in `get_dinner_status` / `report_delay` | tool exception; **`/status` HTTP 500** | error dict; `/status` HTTP 200 with the error |
| `serve_time="banana"` / `"25:99"` | exception / accepted as 26:39 | error naming the accepted formats |
| Delay of −10 or 600 minutes | accepted (naive projection "29:00") | error: must be 1–240 |
| Plan with only an unknown dish ("pizza") | silently planned the default 4 dishes | error listing the dishes it can conduct |
| Brief for an unknown cook | empty brief (board would render "All done 🎉") | error listing this dinner's cooks |
| Completing a step twice | silent success | idempotent, flagged `already_completed: true` |
| Unknown cooks passed to `plan_dinner` | broken summary ("First jobs — .") | falls back to the assigned cooks |

Verified clean before and after fixes: calls before any plan exists,
unknown dish/step, delays on the **beans / mash / gravy** (each
re-plans without crashing — beans +10 → projected 19:10, 0 conflicts),
a second `plan_dinner` (replaces the active dinner — deliberate,
now disclosed in README's limitations). Per-dish recovery *strategies*
remain authored rules (chicken is the fully modelled path) — also
disclosed in README's limitations. 25 new checks were added to
`test_schedule.py` locking all of this in (31 → 56 engine checks);
post-fix probe run confirms every case above behaves as described.

## 5. Board reality check — PASS (actually rendered)

Rendered with headless Chromium
(`chromium_headless_shell-1248` on this box) against the running
server after the full demo arc, at `/board?now=18:50`:

- Screenshot inspected: "Dinner lands **19:01** (1 min past 19:00 —
  re-planned)", delay banner ("roast chicken is running 15 minutes
  behind — re-plan applied below"), all four dish bars with the SERVE
  line at the projected serve, mash bar amber/**holding**, cook chips
  for Dad / Maya / Sam / **Alex** (the guest appears after the
  re-plan — this required the status fix in item 4's batch), and the
  "Re-plan — what changed" list.
- DOM dump text-confirms the re-planned state: projected serve 19:01,
  gravy ready 19:01 with Dad on the roux, **9 `<li>` change items**,
  household facts footer.
- No JS errors encountered; the page's fetch/render logic ran against
  the real `/status` payload. The screenshot is committed as
  `project-image.png` (item 7).

## 6. Video readiness — FIXED (timing math), PASS

- Every Alexa+ line diffed against the fresh run: Beat 1 summary and
  Beat 4 trade-off are **verbatim** server output (after the item-3
  code fix); the `report_delay` quote is the message's first sentence
  and is now annotated as such; Beat 5 is now explicitly annotated as
  *rendered from `get_dinner_status` data* (the tool returns data, not
  speech — every job/time in the line checks against that data).
- Timing math recounted exactly: spoken lines total **247 words**
  ≈ **2:34** of speech at the stated 1.6 w/s — inside the 2:50 script
  and **under the 3:00 judging limit with ~26 s of margin**. (Script
  previously claimed ≈245 words ≈ 2:35 — close, now exact.)
- Beat windows rebalanced: Beat 1's window (0:00–0:35) could not hold
  its own 82 spoken words (~51 s); beats now run 0:00–0:52 / 0:52–1:07
  / 1:07–1:24 / 1:24–2:22 / 2:22–2:43 / end card 2:43–2:50 = 2:50.
- Required beats covered: plan from household memory → per-cook brief
  → voice progress → delay → re-plan with spoken trade-off → landing,
  with the anti-timer line in Beats 1 and the end card.

## 7. Filing completeness — FIXED (4 gaps), PASS

FILING-PREP.md is now a paste-ready package:

- Project name, one-liner, full Devpost description — present and
  claim-checked (item 3).
- **Built-with list added** (was missing).
- **Open Source mini-challenge fields drafted in full** (contribution
  URL, repo URL, username QuincyGB, description) — previously only
  summarised in the checklist.
- **Product feedback now covers every tool/SDK actually used:**
  MCP Python SDK, Alexa+ MCP/Agent Skills docs, MCP spec docs — plus
  **Starlette**, which `server.py` imports directly for the HTTP
  routes and was missing from the drafts (added as feedback item 3).
- Friction log (4 real entries), feature request (hosted Alexa+ MCP
  test harness, with priority framing), track (Alexa+) + mini-challenge
  (Open Source) selections — present.
- **[LIVE URL]** and **[VIDEO URL]** placeholders are explicit at the
  top of the file and in the step list.
- **Project image:** Devpost filing wants a project image; none
  existed. **Created `project-image.png`** — the real board screenshot
  from item 5 (1280×900) — committed to the repo root and referenced
  in FILING-PREP.
- **Exact remaining-steps sequence added** (7 steps, each marked
  Quincy vs Ren). The submission can be completed the moment Render +
  video exist; no build work remains.

## 8. Repo hygiene — PASS

- Tracked files: no `__pycache__`, no `state.json`, no `.venv`
  (`.gitignore` covers all three + `*.pyc`; verified via
  `git ls-files`).
- License: GitHub API re-confirmed after all pushes —
  `private: false`, `license: MIT` (detectable, as the rules require).
- `render.yaml`: parses as valid YAML; the non-standard `repo:` key
  was **removed** in this audit (the Blueprint spec doesn't define it;
  the repo is selected when Quincy connects it in Render). Contents:
  free web service `allatonce`, build `pip install -r requirements.txt`,
  start `python server.py`, health check `/health`, `PYTHON_VERSION
  3.12.0`, no env vars needed.
- Final state: working tree clean, everything pushed (see the report
  for the final HEAD hash; AUDIT.md itself is the last, docs-only
  commit).

## Still blocked (not failures of the submission package)

- **Render deploy** — Quincy's Blueprint click (Dashboard → New →
  Blueprint → `QuincyGB/allatonce` → Apply). No agent-accessible
  Render path exists on this box (checked again in the publish pass).
- **Demo video** — record from DEMO-SCRIPT.md, Quincy uploads to
  YouTube/Vimeo, final Devpost Submit click is Quincy's.
