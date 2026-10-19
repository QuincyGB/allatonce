"""Pure-logic tests for the AllAtOnce scheduling engine.

Run:  python test_schedule.py
No server needed. These tests are the evidence that the re-plan is a real
recomputation: different delays produce different, honest outcomes, and
household memory actually changes the plan.
"""

from __future__ import annotations

import copy
import json
import os
import sys
import tempfile

# Keep test state out of the project folder.
os.environ["ALLATONCE_STATE"] = os.path.join(
    tempfile.mkdtemp(prefix="allatonce-test-"), "state.json")

import schedule  # noqa: E402

failures: list[str] = []


def check(label: str, cond: bool, detail: str = "") -> None:
    print(f"  [{'PASS' if cond else 'FAIL'}] {label} {detail}")
    if not cond:
        failures.append(label)


def step(dishes, dish, step_id):
    return next(s for s in dishes[dish]["steps"] if s["id"] == step_id)


def fresh_plan():
    if os.path.exists(schedule.STATE_PATH):
        os.remove(schedule.STATE_PATH)
    schedule.SESSION = None
    return schedule.plan_dinner(
        ["roast chicken", "garlic mash", "green beans", "gravy"],
        "19:00", ["Dad", "Maya", "Sam"])


print("Time parsing")
check("'19:00' -> 1140", schedule.parse_time("19:00") == 1140)
check("'7:00 PM' -> 1140", schedule.parse_time("7:00 PM") == 1140)
check("'7pm' -> 1140", schedule.parse_time("7pm") == 1140)
check("fmt(1141) -> '19:01'", schedule.fmt(1141) == "19:01")

print("\nBackward plan from serve time")
fresh_plan()
d = schedule.SESSION["schedule"]["dishes"]
check("chicken starts 17:40", d["roast_chicken"]["start"] == 17 * 60 + 40,
      schedule.fmt(d["roast_chicken"]["start"]))
check("every dish ready 19:00",
      all(v["ready"] == 1140 for v in d.values()))
check("gravy cook is Maya (household fact)",
      step(d, "gravy", "gravy_roux")["cook"] == "Maya")
check("chicken rest is 10 (household fact)",
      step(d, "roast_chicken", "chicken_rest")["duration"] == 10)
check("gravy starts after roast ends (dependency)",
      step(d, "gravy", "gravy_roux")["start"]
      >= step(d, "roast_chicken", "chicken_roast")["end"])
check("beans cook inside freshness window",
      step(d, "green_beans", "beans_steam")["start"] >= 1140 - 20)
check("no cook conflicts in the plan",
      schedule.SESSION["schedule"]["conflicts"] == [])

print("\nHousehold memory actually drives the plan")
house = schedule.load_household()
for fact in house["facts"]:
    if fact.get("id") == "chicken_rest_10":
        fact["rest_minutes"] = 12
schedule.save_household(house)
schedule.SESSION = None
schedule.plan_dinner(["roast chicken"], "19:00", ["Dad"])
d2 = schedule.SESSION["schedule"]["dishes"]
check("rest=12 in memory -> rest step is 12",
      step(d2, "roast_chicken", "chicken_rest")["duration"] == 12)
check("rest=12 -> chicken starts 2 min earlier (17:38)",
      d2["roast_chicken"]["start"] == 17 * 60 + 38,
      schedule.fmt(d2["roast_chicken"]["start"]))
os.remove(schedule.STATE_PATH)  # restore seed memory for the rest

print("\nRe-plan: the demo delay (chicken +15)")
fresh_plan()
schedule.complete_step("mash_mash")
schedule.report_delay("roast chicken", 15, now="18:30")
r = schedule.replan_dinner()
nd = schedule.SESSION["schedule"]["dishes"]
check("projected serve 19:01", r["projected_serve_time"] == "19:01",
      r["projected_serve_time"])
check("slip is exactly 1", r["serve_slip_minutes"] == 1)
check("chicken itself lands 19:00 (delay absorbed)",
      nd["roast_chicken"]["ready"] == 1140)
check("roast recovered 9 via high-heat (54+15-9=60)",
      step(nd, "roast_chicken", "chicken_roast")["duration"] == 60)
check("rest trimmed to its minimum 7",
      step(nd, "roast_chicken", "chicken_rest")["duration"] == 7)
check("carve parallelised to 3 with the guest",
      step(nd, "roast_chicken", "chicken_carve")["duration"] == 3
      and "Alex" in step(nd, "roast_chicken", "chicken_carve")["cook"])
check("gravy reassigned Maya -> Dad",
      step(nd, "gravy", "gravy_roux")["cook"] == "Dad")
check("gravy ready 19:01 (drippings dependency, computed)",
      nd["gravy"]["ready"] == 1141)
check("gravy keep-warm dropped (served from the pan)",
      all(s["id"] != "gravy_keep_warm" for s in nd["gravy"]["steps"]))
check("mash hold extended 14 -> 18",
      step(nd, "garlic_mash", "mash_hold")["duration"] == 18,
      str(step(nd, "garlic_mash", "mash_hold")["duration"]))
check("mash rest dropped, rewhip lands at projected serve",
      all(s["id"] != "mash_rest" for s in nd["garlic_mash"]["steps"])
      and step(nd, "garlic_mash", "mash_rewhip")["end"] == 1141)
check("beans switched to single-pan and pushed later",
      step(nd, "green_beans", "beans_pan_saute")["start"]
      > step(d, "green_beans", "beans_steam")["start"],
      f"{schedule.fmt(step(nd, 'green_beans', 'beans_pan_saute')['start'])}"
      f" vs {schedule.fmt(step(d, 'green_beans', 'beans_steam')['start'])}")
check("spoken trade-off present, names 7:01",
      "7:01" in r["trade_off_spoken"] and "lock that in" in
      r["trade_off_spoken"])
check("no cook conflicts after re-plan",
      schedule.SESSION["schedule"]["conflicts"] == [],
      str(schedule.SESSION["schedule"]["conflicts"]))
check("household memory recorded the landing",
      schedule.load_household()["last_dinner"]["projected_serve"] == "19:01")
os.remove(schedule.STATE_PATH)

print("\nRe-plan honesty: a small delay is fully absorbed")
fresh_plan()
schedule.report_delay("roast chicken", 5, now="18:30")
r = schedule.replan_dinner()
check("delay +5 -> serve holds at 19:00, slip 0",
      r["projected_serve_time"] == "19:00" and r["serve_slip_minutes"] == 0,
      r["projected_serve_time"])
os.remove(schedule.STATE_PATH)

print("\nRe-plan honesty: a huge delay cannot be absorbed")
fresh_plan()
schedule.report_delay("roast chicken", 30, now="18:30")
r = schedule.replan_dinner()
check("delay +30 -> honest slip (serve 19:16)",
      r["projected_serve_time"] == "19:16" and r["serve_slip_minutes"] == 16,
      r["projected_serve_time"])
check("spoken summary admits the slip",
      "couldn't absorb" in r["trade_off_spoken"])
os.remove(schedule.STATE_PATH)

print("\nRESULT:", "ALL PASS" if not failures
      else f"{len(failures)} FAILURES: {failures}")
sys.exit(0 if not failures else 1)
