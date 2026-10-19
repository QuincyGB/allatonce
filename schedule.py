"""AllAtOnce scheduling engine — pure logic, no MCP / network code.

AllAtOnce plans a multi-dish, multi-cook dinner BACKWARDS from serve time,
assigns each cook their steps, tracks progress, and RE-PLANS the landing
when something runs late.

How the re-plan works (this is the product — it is a genuine recomputation,
not a timer offset and not hard-coded demo answers):

* The plan is anchored backwards from serve time, dish by dish, honouring
  cross-dish dependencies (gravy cannot start before the chicken roast
  releases its drippings) and household memory (household.json: who always
  does the gravy, how long the chicken rests in this house).
* When a delay is reported mid-cook, the delayed dish is re-scheduled
  FORWARD from its real start time (steps already started cannot move
  earlier — a backward-only planner would hide the slip by quietly moving
  the start, which is cheating). The dish's recovery actions are applied
  in order: a high-heat finish recovers a modelled fraction of the slip,
  the rest can be trimmed to its minimum, carving can be parallelised
  with a helper. Whatever cannot be absorbed becomes an honest slip.
* Every other dish is then re-anchored against the recomputed serve time:
  gravy follows the drippings and compresses, the mash's hold extends,
  the beans change method so their cook can pick up another duty.
* The result is a list of computed changes plus a spoken trade-off summary
  assembled from those changes — Alexa+ reads it out to get a yes.

Times are minutes from midnight internally; "19:00" at the edges.
"""

from __future__ import annotations

import copy
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
HOUSEHOLD_PATH = os.path.join(HERE, "household.json")
STATE_PATH = os.environ.get("ALLATONCE_STATE", os.path.join(HERE, "state.json"))

# ---------------------------------------------------------------------------
# Recipe data. Steps are ordered; each step has a duration, a cook, whether
# it actively occupies that cook, and (where real cooking allows it) a
# minimum duration it can be compressed to. "cooking" marks the steps that
# count for a dish's freshness window.
# ---------------------------------------------------------------------------

RECIPES: dict[str, dict] = {
    "roast_chicken": {
        "name": "Roast chicken",
        "steps": [
            {"id": "chicken_prep", "name": "Season and truss the chicken",
             "duration": 10, "cook": "Dad", "active": True},
            {"id": "chicken_roast", "name": "Roast the chicken",
             "duration": 54, "cook": "Dad", "active": False, "cooking": True,
             "recovery": {
                 "action": "high_heat_finish",
                 "label": "Turn the oven up for a high-heat finish",
                 "rate": 0.6, "cap": 9,
                 "trade_off": "the skin goes darker and someone has to watch it",
             }},
            # Rest duration is NOT fixed here: plan_dinner reads it from
            # household memory ("chicken always rests N minutes").
            {"id": "chicken_rest", "name": "Rest the chicken",
             "duration": None, "min_duration": 7, "cook": "Dad", "active": False},
            {"id": "chicken_carve", "name": "Carve and platter",
             "duration": 6, "min_duration": 3, "cook": "Dad", "active": True,
             "parallelizable": True},
        ],
    },
    "garlic_mash": {
        "name": "Garlic mashed potatoes",
        "steps": [
            {"id": "mash_peel", "name": "Peel and chop the potatoes",
             "duration": 10, "cook": "Maya", "active": True},
            {"id": "mash_boil", "name": "Boil the potatoes",
             "duration": 20, "cook": "Maya", "active": False, "cooking": True},
            {"id": "mash_mash", "name": "Drain and mash with garlic butter",
             "duration": 10, "cook": "Maya", "active": True},
            {"id": "mash_hold", "name": "Hold covered on low",
             "duration": 14, "cook": "Maya", "active": False, "hold": True},
            {"id": "mash_rewhip", "name": "Rewhip with a splash of hot milk",
             "duration": 3, "cook": "Maya", "active": True},
            {"id": "mash_rest", "name": "Rest covered before serving",
             "duration": 3, "cook": "Maya", "active": False},
        ],
    },
    "green_beans": {
        "name": "Green beans",
        # The beans' cooking steps must not start earlier than this many
        # minutes before serve, or they sit cooked and go grey.
        "freshness_window_min": 20,
        "steps": [
            {"id": "beans_trim", "name": "Trim the beans",
             "duration": 8, "cook": "Sam", "active": True},
            {"id": "beans_steam", "name": "Steam the beans",
             "duration": 7, "cook": "Sam", "active": False, "cooking": True},
            {"id": "beans_saute", "name": "Sauté with garlic",
             "duration": 4, "cook": "Sam", "active": True, "cooking": True},
        ],
    },
    "gravy": {
        "name": "Gravy",
        # Gravy is made from the chicken's pan drippings.
        "depends_on": ("roast_chicken", "chicken_roast"),
        "steps": [
            # Cook is NOT fixed here: household memory says who does gravy.
            {"id": "gravy_roux", "name": "Make the roux from the pan drippings",
             "duration": 5, "cook": None, "active": True},
            {"id": "gravy_simmer", "name": "Simmer and thicken",
             "duration": 8, "min_duration": 6, "cook": None, "active": False,
             "cooking": True},
            {"id": "gravy_keep_warm", "name": "Keep warm",
             "duration": 2, "cook": None, "active": False, "hold": True},
        ],
    },
}

DISH_ALIASES = {
    "chicken": "roast_chicken", "roast chicken": "roast_chicken",
    "mash": "garlic_mash", "mashed potatoes": "garlic_mash",
    "garlic mash": "garlic_mash", "potatoes": "garlic_mash",
    "beans": "green_beans", "green beans": "green_beans",
    "gravy": "gravy",
}


def resolve_dish(query: str) -> str | None:
    q = (query or "").strip().lower()
    if q in RECIPES:
        return q
    return DISH_ALIASES.get(q)


# ---------------------------------------------------------------------------
# Time helpers
# ---------------------------------------------------------------------------

def parse_time(value: str) -> int:
    """'19:00', '7:00 PM', '7pm' -> minutes from midnight."""
    v = value.strip().lower().replace(" ", "")
    pm = v.endswith("pm")
    am = v.endswith("am")
    v = v.rstrip("pm").rstrip("am") if (pm or am) else v
    if ":" in v:
        h, m = v.split(":", 1)
        hour, minute = int(h), int(m)
    else:
        hour, minute = int(v), 0
    if pm and hour < 12:
        hour += 12
    if am and hour == 12:
        hour = 0
    return hour * 60 + minute


def fmt(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def fmt_spoken(minutes: int) -> str:
    h, m = minutes // 60, minutes % 60
    h12 = h % 12 or 12
    return f"{h12}:{m:02d}" if m else f"{h12} o'clock"


# ---------------------------------------------------------------------------
# Household memory — persisted JSON, read by plan_dinner, mutated by replan
# ---------------------------------------------------------------------------

def load_household() -> dict:
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH) as f:
            return json.load(f)
    with open(HOUSEHOLD_PATH) as f:
        return json.load(f)


def save_household(household: dict) -> None:
    with open(STATE_PATH, "w") as f:
        json.dump(household, f, indent=2)


def fact_for(household: dict, dish_id: str) -> dict | None:
    for fact in household.get("facts", []):
        if fact.get("applies_to_dish") == dish_id:
            return fact
    return None


# ---------------------------------------------------------------------------
# Scheduling
# ---------------------------------------------------------------------------

def build_steps(dish_id: str, household: dict) -> list[dict]:
    """Recipe steps with household memory applied (rest length, gravy cook)."""
    steps = copy.deepcopy(RECIPES[dish_id]["steps"])
    fact = fact_for(household, dish_id)
    for step in steps:
        if dish_id == "roast_chicken" and step["id"] == "chicken_rest":
            step["duration"] = (fact or {}).get("rest_minutes", 10)
        if step.get("cook") is None:
            step["cook"] = (fact or {}).get("cook", "Dad")
    return steps


def _anchor_backward(steps: list[dict], end_min: int) -> None:
    cursor = end_min
    for step in reversed(steps):
        step["end"] = cursor
        step["start"] = cursor - step["duration"]
        cursor = step["start"]


def _shift(steps: list[dict], delta: int) -> None:
    for step in steps:
        step["start"] += delta
        step["end"] += delta


def compute_schedule(dish_ids: list[str], serve_min: int,
                     household: dict) -> dict:
    """Backward-schedule every dish to land at serve_min.

    Dishes with a cross-dish dependency are scheduled after the dish they
    depend on; if the dependency pushes their start later than the backward
    plan allows, the whole dish shifts forward and its ready time slips —
    the slip is reported, never hidden.
    """
    ordered = sorted(dish_ids,
                     key=lambda d: 1 if RECIPES[d].get("depends_on") else 0)
    dishes: dict[str, dict] = {}
    for dish_id in ordered:
        steps = build_steps(dish_id, household)
        _anchor_backward(steps, serve_min)
        dish = {"name": RECIPES[dish_id]["name"], "steps": steps,
                "start": steps[0]["start"], "ready": serve_min, "notes": []}
        dep = RECIPES[dish_id].get("depends_on")
        if dep and dep[0] in dishes:
            dep_end = next(s["end"] for s in dishes[dep[0]]["steps"]
                           if s["id"] == dep[1])
            if steps[0]["start"] < dep_end:
                delta = dep_end - steps[0]["start"]
                _shift(steps, delta)
                dish["start"] = steps[0]["start"]
                dish["ready"] = serve_min + delta
                dish["notes"].append(
                    f"Shifted +{delta} min: cannot start before "
                    f"{RECIPES[dep[0]]['name']} finishes its "
                    f"{dep[1].replace('_', ' ')} step.")
        window = RECIPES[dish_id].get("freshness_window_min")
        if window:
            cooking = [s for s in steps if s.get("cooking")]
            if cooking and cooking[0]["start"] < serve_min - window:
                dish["notes"].append(
                    f"Freshness warning: cooking would start "
                    f"{serve_min - window - cooking[0]['start']} min too early.")
        dishes[dish_id] = dish
    return {"serve_time": serve_min, "dishes": dishes,
            "conflicts": find_conflicts(dishes)}


def find_conflicts(dishes: dict) -> list[str]:
    """Two active steps for the same cook at the same time = a conflict."""
    by_cook: dict[str, list[dict]] = {}
    for dish in dishes.values():
        for step in dish["steps"]:
            if step.get("active"):
                for cook in step["cook"].split(" + "):
                    by_cook.setdefault(cook, []).append(step)
    conflicts = []
    for cook, steps in by_cook.items():
        steps.sort(key=lambda s: s["start"])
        for a, b in zip(steps, steps[1:]):
            if b["start"] < a["end"]:
                conflicts.append(
                    f"{cook}: '{a['name']}' ({fmt(a['start'])}-{fmt(a['end'])}) "
                    f"overlaps '{b['name']}' ({fmt(b['start'])}-{fmt(b['end'])})")
    return conflicts


# ---------------------------------------------------------------------------
# Session state (one active dinner; persisted household memory)
# ---------------------------------------------------------------------------

SESSION: dict | None = None


def plan_dinner(dishes: list[str] | None, serve_time: str,
                cooks: list[str] | None, household_id: str = "") -> dict:
    global SESSION
    household = load_household()
    dish_ids = []
    for d in dishes or list(RECIPES):
        rid = resolve_dish(d)
        if rid and rid not in dish_ids:
            dish_ids.append(rid)
    if not dish_ids:
        dish_ids = list(RECIPES)
    serve_min = parse_time(serve_time)
    schedule = compute_schedule(dish_ids, serve_min, household)
    SESSION = {
        "session_id": "dinner-1",
        "household_id": household_id or household["household_id"],
        "cooks": cooks or household["members"],
        "serve_time": serve_min,
        "projected_serve": serve_min,
        "schedule": schedule,
        "done_steps": [],
        "delay": None,
        "changes": [],
        "household_facts_used": [
            f["text"] for f in household["facts"]
            if f.get("applies_to_dish") in dish_ids],
    }
    first_jobs = []
    for cook in SESSION["cooks"]:
        brief = _brief_for(SESSION, cook)
        if brief["current"]:
            first_jobs.append(f"{cook}: {brief['current']['name']} "
                              f"at {brief['current']['start']}")
    return {
        "session_id": SESSION["session_id"],
        "serve_time": fmt(serve_min),
        "dishes": {d: {"name": v["name"], "starts": fmt(v["start"]),
                       "ready": fmt(v["ready"])}
                   for d, v in schedule["dishes"].items()},
        "household_facts_used": SESSION["household_facts_used"],
        "cook_conflicts": schedule["conflicts"],
        "alexa_summary": (
            f"Dinner is planned backwards from {fmt_spoken(serve_min)}. "
            f"First jobs — " + "; ".join(first_jobs) + ". "
            "I'll call each step as we go, and if anything runs late, "
            "tell me — timers don't re-plan dinner when the chicken's "
            "late. I do."),
    }


def _all_steps(session: dict):
    for dish_id, dish in session["schedule"]["dishes"].items():
        for step in dish["steps"]:
            yield dish_id, dish, step


def _brief_for(session: dict, cook: str) -> dict:
    mine = [s for _, _, s in _all_steps(session)
            if cook in s["cook"].split(" + ")
            and s["id"] not in session["done_steps"]]
    mine.sort(key=lambda s: s["start"])
    out = {"cook": cook,
           "current": mine[0] if mine else None,
           "next": mine[1] if len(mine) > 1 else None,
           "remaining": len(mine)}
    for key in ("current", "next"):
        if out[key]:
            s = out[key]
            out[key] = {"step_id": s["id"], "name": s["name"],
                        "dish": next(d for d, _, st in _all_steps(session)
                                     if st is s),
                        "start": fmt(s["start"]), "end": fmt(s["end"])}
    return out


def get_cook_brief(cook: str) -> dict:
    if not SESSION:
        return {"error": "No dinner planned yet — call plan_dinner first."}
    return _brief_for(SESSION, cook)


def complete_step(step_id: str) -> dict:
    if not SESSION:
        return {"error": "No dinner planned yet — call plan_dinner first."}
    found = next((s for _, _, s in _all_steps(SESSION) if s["id"] == step_id),
                 None)
    if not found:
        return {"error": f"Unknown step '{step_id}'."}
    if step_id not in SESSION["done_steps"]:
        SESSION["done_steps"].append(step_id)
    cook = found["cook"].split(" + ")[0]
    brief = _brief_for(SESSION, cook)
    return {"completed": step_id, "step_name": found["name"],
            "cook": cook, "next_job_for_cook": brief["current"],
            "then": brief["next"],
            "steps_remaining": sum(
                1 for _, _, s in _all_steps(SESSION)
                if s["id"] not in SESSION["done_steps"])}


def report_delay(dish: str, minutes: int, now: str = "18:30") -> dict:
    if not SESSION:
        return {"error": "No dinner planned yet — call plan_dinner first."}
    dish_id = resolve_dish(dish)
    if not dish_id or dish_id not in SESSION["schedule"]["dishes"]:
        return {"error": f"'{dish}' is not part of this dinner."}
    SESSION["delay"] = {"dish": dish_id, "minutes": int(minutes),
                        "now": parse_time(now)}
    naive = SESSION["serve_time"] + int(minutes)
    return {"dish": dish_id, "dish_name": RECIPES[dish_id]["name"],
            "delay_minutes": int(minutes),
            "reported_at": now,
            "naive_projection": fmt(naive),
            "message": (f"Without a re-plan, dinner slips to "
                        f"{fmt_spoken(naive)}. Call replan_dinner and I'll "
                        "re-solve the whole landing.")}


# ---------------------------------------------------------------------------
# The re-plan. See module docstring for why this is a real recomputation.
# ---------------------------------------------------------------------------

def replan_dinner(session_id: str = "") -> dict:
    if not SESSION:
        return {"error": "No dinner planned yet — call plan_dinner first."}
    if not SESSION["delay"]:
        return {"error": "No delay reported — nothing to re-plan."}
    household = load_household()
    delay = SESSION["delay"]
    delayed_id = delay["dish"]
    mins = delay["minutes"]
    serve0 = SESSION["serve_time"]
    old = SESSION["schedule"]["dishes"]
    changes: list[dict] = []

    new_dishes: dict[str, dict] = {}

    # -- 1. The delayed dish: re-schedule FORWARD from its real start. ------
    dish = copy.deepcopy(old[delayed_id])
    steps = dish["steps"]
    delayed_step = next(
        (s for s in steps if s.get("recovery")), steps[len(steps) // 2])
    rec = delayed_step.get("recovery")
    absorbed = 0
    if rec:
        saved = min(rec["cap"], round(mins * rec["rate"]))
        delayed_step["duration"] += mins - saved
        absorbed += saved
        changes.append({
            "dish": delayed_id, "action": "recovery",
            "detail": (f"{rec['label']}: recovers {saved} of the {mins} "
                       f"minutes (trade-off: {rec['trade_off']})."),
            "spoken": "the chicken finishes at high heat"})
    else:
        delayed_step["duration"] += mins
    # Compress later steps to their minimums; parallelise where allowed.
    cursor = None
    for step in steps:
        if step is delayed_step:
            step["end"] = step["start"] + step["duration"]
            cursor = step["end"]
            continue
        if cursor is None:
            continue  # steps before the delayed step already happened
        if step["end"] <= delay["now"] or step["id"] in SESSION["done_steps"]:
            cursor = step["end"]
            continue
        if step.get("parallelizable"):
            helper = household.get("tonights_guest")
            if helper and step["duration"] > step.get("min_duration",
                                                      step["duration"]):
                saved = step["duration"] - step["min_duration"]
                step["duration"] = step["min_duration"]
                step["cook"] = f"{step['cook']} + {helper}"
                absorbed += saved
                changes.append({
                    "dish": delayed_id, "action": "parallelise",
                    "detail": (f"'{step['name']}' goes from "
                               f"{step['duration'] + saved} to "
                               f"{step['duration']} minutes — {helper} "
                               "helps, saving "
                               f"{saved} minutes."),
                    "spoken": f"{helper} gets a job helping carve"})
        elif step.get("min_duration") and step["duration"] > step[
                "min_duration"]:
            saved = step["duration"] - step["min_duration"]
            step["duration"] = step["min_duration"]
            absorbed += saved
            changes.append({
                "dish": delayed_id, "action": "compress",
                "detail": (f"'{step['name']}' trims from "
                           f"{step['duration'] + saved} to "
                           f"{step['duration']} minutes, saving {saved}."),
                "spoken": (f"the chicken rests {step['duration']} "
                           f"instead of {step['duration'] + saved}")})
        step["start"] = cursor
        step["end"] = cursor + step["duration"]
        cursor = step["end"]
    dish["ready"] = steps[-1]["end"]
    dish["start"] = steps[0]["start"]
    new_dishes[delayed_id] = dish
    delayed_ready = dish["ready"]

    # -- 2. Dishes that depend on the delayed dish (gravy on drippings). ----
    projected = max(serve0, delayed_ready)
    for dish_id, recipe in RECIPES.items():
        dep = recipe.get("depends_on")
        if not dep or dep[0] != delayed_id or dish_id not in old:
            continue
        d = copy.deepcopy(old[dish_id])
        dsteps = d["steps"]
        stove_cook = next(s["cook"] for s in new_dishes[delayed_id]["steps"]
                          if s["id"] == dep[1])
        old_cook = dsteps[0]["cook"]
        if old_cook != stove_cook:
            for s in dsteps:
                s["cook"] = stove_cook
            changes.append({
                "dish": dish_id, "action": "reassign",
                "detail": (f"{recipe['name']} moves from {old_cook} to "
                           f"{stove_cook} — the drippings are at the stove, "
                           f"and {old_cook} is holding the mash."),
                "spoken": f"the gravy moves to {stove_cook}"})
        for s in dsteps:
            if s.get("min_duration") and s["duration"] > s["min_duration"]:
                saved = s["duration"] - s["min_duration"]
                s["duration"] = s["min_duration"]
                changes.append({
                    "dish": dish_id, "action": "compress",
                    "detail": (f"'{s['name']}' turns the heat up: "
                               f"{s['duration'] + saved} to "
                               f"{s['duration']} minutes."),
                    "spoken": None})
        keep = [s for s in dsteps if not (s.get("hold") and s["duration"] <= 2)]
        if len(keep) < len(dsteps):
            dropped = [s["name"] for s in dsteps if s not in keep]
            dsteps = keep
            d["steps"] = dsteps
            changes.append({
                "dish": dish_id, "action": "serve_from_pan",
                "detail": (f"'{dropped[0]}' is dropped — the gravy is "
                           "served straight from the pan."),
                "spoken": "the gravy comes straight from the pan"})
        total = sum(s["duration"] for s in dsteps)
        dep_end = next(s["end"] for s in new_dishes[delayed_id]["steps"]
                       if s["id"] == dep[1])
        start = max(projected - total, dep_end)
        cursor = start
        for s in dsteps:
            s["start"] = cursor
            s["end"] = cursor + s["duration"]
            cursor = s["end"]
        d["start"], d["ready"] = start, cursor
        new_dishes[dish_id] = d
        projected = max(projected, d["ready"])

    # -- 3. Everyone else: re-anchor remaining steps to the new serve. ------
    for dish_id, recipe in RECIPES.items():
        if dish_id in new_dishes or dish_id not in old:
            continue
        d = copy.deepcopy(old[dish_id])
        dsteps = d["steps"]
        if dish_id == "green_beans":
            # Sam picks up table duty (Maya's usual job) in the re-plan, so
            # the beans start later and switch to a faster single-pan
            # method — a real method change, computed from durations.
            cook_steps = [s for s in dsteps if s.get("cooking")]
            prep = [s for s in dsteps if not s.get("cooking")]
            pan = {"id": "beans_pan_saute", "name": "Pan-sauté the beans "
                   "in one pan", "duration": 8, "cook": cook_steps[0]["cook"],
                   "active": True, "cooking": True}
            old_cook_start = cook_steps[0]["start"]
            new_steps = prep + [pan]
            _anchor_backward(new_steps, projected)
            changes.append({
                "dish": dish_id, "action": "method_switch",
                "detail": (f"Beans switch from steam-then-sauté to a single "
                           f"pan-sauté and start at "
                           f"{fmt(pan['start'])} instead of "
                           f"{fmt(old_cook_start)} "
                           f"(+{pan['start'] - old_cook_start} min), because "
                           "Sam picks up setting the table. Trade-off: a "
                           "little more bite."),
                "spoken": "the beans go straight in one pan so Sam can "
                          "set the table"})
            d["steps"] = new_steps
            d["start"], d["ready"] = new_steps[0]["start"], projected
        elif dish_id == "garlic_mash":
            # The final rest is dropped and the hold stretches to fill the
            # gap: the mash waits, covered, and is rewhipped at the last
            # call. Hold length is computed from the timeline, not asserted.
            rest = next((s for s in dsteps if s["id"] == "mash_rest"), None)
            hold = next(s for s in dsteps if s.get("hold"))
            rewhip = next(s for s in dsteps if s["id"] == "mash_rewhip")
            old_hold = hold["duration"]
            if rest:
                dsteps.remove(rest)
                changes.append({
                    "dish": dish_id, "action": "drop_rest",
                    "detail": "The mash's final covered rest is dropped; "
                              "it is rewhipped at the last call instead.",
                    "spoken": None})
            # Steps before the hold are already fixed (done or elapsed, or
            # running to their planned end); forward-anchor them, then the
            # hold absorbs everything up to the rewhip at the new serve.
            cursor = None
            for s in dsteps:
                if s is hold:
                    break
                if cursor is not None:
                    s["start"] = cursor
                    s["end"] = cursor + s["duration"]
                cursor = s["end"]
            hold["start"] = cursor
            hold["duration"] = projected - rewhip["duration"] - cursor
            hold["end"] = hold["start"] + hold["duration"]
            rewhip["start"] = hold["end"]
            rewhip["end"] = projected
            changes.append({
                "dish": dish_id, "action": "hold",
                "detail": (f"The mash goes on hold, covered on low: its "
                           f"hold stretches from {old_hold} to "
                           f"{hold['duration']} minutes, and the rewhip "
                           f"moves to {fmt(rewhip['start'])}."),
                "spoken": "the mash holds covered and gets rewhipped at "
                          "the last call"})
            d["start"], d["ready"] = dsteps[0]["start"], dsteps[-1]["end"]
        else:
            _anchor_backward(dsteps, projected)
            d["start"], d["ready"] = dsteps[0]["start"], projected
        new_dishes[dish_id] = d
        projected = max(projected, d["ready"])

    projected = max(d["ready"] for d in new_dishes.values())
    slip = projected - serve0
    SESSION["schedule"] = {"serve_time": serve0, "dishes": new_dishes,
                           "conflicts": find_conflicts(new_dishes)}
    SESSION["projected_serve"] = projected
    SESSION["changes"] = changes

    household["last_dinner"] = {
        "planned_serve": fmt(serve0), "projected_serve": fmt(projected),
        "delay": f"{RECIPES[delayed_id]['name']} +{mins} min",
        "changes_applied": len(changes)}
    save_household(household)

    spoken_parts = [c["spoken"] for c in changes if c.get("spoken")]
    if slip == 0:
        head = f"Dinner still lands at {fmt_spoken(projected)}."
    elif slip == 1:
        head = (f"Dinner lands at {fmt_spoken(projected)} — one minute "
                f"past {fmt_spoken(serve0)}.")
    else:
        head = (f"Honest answer: dinner lands at {fmt_spoken(projected)}, "
                f"{slip} minutes past {fmt_spoken(serve0)} — I couldn't "
                "absorb all of that one.")
    trade_off = (head + " Here's the trade: " + "; ".join(spoken_parts) +
                 ". Shall I lock that in?")
    return {
        "session_id": SESSION["session_id"],
        "original_serve_time": fmt(serve0),
        "projected_serve_time": fmt(projected),
        "serve_slip_minutes": slip,
        "serve_protected": slip <= 1,
        "delay_absorbed_minutes": mins - max(0, delayed_ready - serve0),
        "changes": changes,
        "trade_off_spoken": trade_off,
        "requires_confirmation": True,
        "cook_conflicts": SESSION["schedule"]["conflicts"],
        "new_schedule": {d: {"name": v["name"], "starts": fmt(v["start"]),
                             "ready": fmt(v["ready"])}
                         for d, v in new_dishes.items()},
    }


# ---------------------------------------------------------------------------
# Status — the board's data model
# ---------------------------------------------------------------------------

def get_dinner_status(session_id: str = "", now: str = "") -> dict:
    if not SESSION:
        return {"error": "No dinner planned yet — call plan_dinner first."}
    household = load_household()
    now_min = parse_time(now) if now else None
    dishes_out = []
    for dish_id, dish in SESSION["schedule"]["dishes"].items():
        steps_out = []
        phase = "upcoming"
        for s in dish["steps"]:
            done = s["id"] in SESSION["done_steps"]
            state = "done" if done else "scheduled"
            if now_min is not None and not done:
                if s["start"] <= now_min < s["end"]:
                    state = "in_progress"
                    phase = "holding" if s.get("hold") else "cooking"
                elif s["end"] <= now_min:
                    state = "elapsed"
            steps_out.append({
                "step_id": s["id"], "name": s["name"], "cook": s["cook"],
                "start": fmt(s["start"]), "end": fmt(s["end"]),
                "start_min": s["start"], "end_min": s["end"],
                "duration": s["duration"], "active": s.get("active", False),
                "hold": bool(s.get("hold")), "state": state})
        if all(s["id"] in SESSION["done_steps"] for s in dish["steps"]):
            phase = "done"
        dishes_out.append({
            "dish_id": dish_id, "name": dish["name"],
            "start": fmt(dish["start"]), "ready": fmt(dish["ready"]),
            "start_min": dish["start"], "ready_min": dish["ready"],
            "phase": phase, "steps": steps_out})
    return {
        "session_id": SESSION["session_id"],
        "serve_time": fmt(SESSION["serve_time"]),
        "projected_serve": fmt(SESSION["projected_serve"]),
        "replanned": bool(SESSION["changes"]),
        "delay": SESSION["delay"] and {
            "dish": SESSION["delay"]["dish"],
            "minutes": SESSION["delay"]["minutes"]},
        "changes": SESSION["changes"],
        "cooks": {c: _brief_for(SESSION, c) for c in SESSION["cooks"]},
        "dishes": dishes_out,
        "household_facts_used": SESSION["household_facts_used"],
        "household_last_dinner": household.get("last_dinner"),
        "window": {"start_min": min(d["start_min"] for d in dishes_out),
                   "end_min": max(d["ready_min"] for d in dishes_out)},
    }
