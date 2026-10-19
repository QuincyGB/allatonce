# AllAtOnce — Demo Video Script (< 3 minutes)

One scenario, one dinner, no cuts away from the kitchen. All Alexa+
responses below are the **real outputs of the server** from the recorded
test run (`test-output.txt`, 66 checks ALL PASS) — quoted verbatim where
the tool returns spoken text, and rendered word-for-word from the tool's
structured output where it returns data (step names and times unchanged).

**Pacing:** Quincy's video standard — slow, complete explanations, raw
speech ~**1.6 words/second** for the opening and narration, ≤2.0 for the
body. Spoken total ≈ 245 words ≈ 2:35 of speech inside a 2:50 video.

**Cast:** Dad (at the stove), Maya (potatoes, then gravy), Sam (beans),
Alex (tonight's guest — gets drafted). Kitchen Echo Show shows the board
(`/board`) throughout.

---

### Beat 1 — The plan (0:00–0:35)

*On screen: the family kitchen, Echo Show. Dad, hands on a raw chicken.*

**DAD** *(24 words, ~15 s)*
> "Alexa, we're four for dinner at seven — roast chicken, garlic mash,
> green beans, and Maya's doing her gravy. Land it all at seven."

**ALEXA+** *(from `plan_dinner`'s `alexa_summary`, times spoken in
12-hour form — 55 words, ~35 s)*
> "Dinner is planned backwards from 7 o'clock. First jobs — Dad: Season
> and truss the chicken at 5:40; Maya: Peel and chop the potatoes at
> 6:00; Sam: Trim the beans at 6:41. I'll call each step as we go, and
> if anything runs late, tell me — **timers don't re-plan dinner when
> the chicken's late. I do.**"

*On screen: the board appears — four dish bars converging on one SERVE
line at 7:00. Camera holds on it for two seconds. It is readable from
across the kitchen, which is the point.*

### Beat 2 — One cook, one job (0:35–0:55)

**DAD**
> "Alexa, what should Maya be doing?"

**ALEXA+** *(from `get_cook_brief` — Maya's current + next step only)*
> "Maya: peel and chop the potatoes, 6:00 to 6:10. Then the boil."

*On screen: Maya's chip on the board shows exactly that one job. Nobody
gets a five-item readout while their hands are covered in potato.*

### Beat 3 — Progress, by voice (0:55–1:15)

*Maya, wiping her hands, doesn't touch anything.*

**MAYA**
> "Alexa, the mash is done."

**ALEXA+** *(from `complete_step` — next job, then the following one)*
> "Checked off. The mash holds covered on low — and Maya, your gravy
> starts at 6:45, from the pan drippings."

*On screen: mash bar checks off on the board; Maya's next job flips to
the gravy.*

### Beat 4 — THE PAYOFF: the chicken is late (1:15–2:10)

*Dad opens the oven, looks, shakes his head.*

**DAD**
> "Alexa, the chicken's running fifteen behind."

**ALEXA+** *(from `report_delay`, verbatim)*
> "Without a re-plan, dinner slips to 7:15."

*Beat. The chicken bar on the board turns red; the SERVE line wobbles
to 7:15.*

**DAD**
> "So re-plan it."

**ALEXA+** *(from `replan_dinner`'s `trade_off_spoken`, verbatim —
72 words, ~45 s. This is the hero beat; let it breathe.)*
> "Dinner lands at 7:01 — one minute past 7 o'clock. Here's the trade:
> the chicken finishes at high heat; the chicken rests 7 instead of 10;
> Alex gets a job helping carve; the gravy moves to Dad; the gravy
> comes straight from the pan; the mash holds covered and gets
> rewhipped at the last call; the beans go straight in one pan so Sam
> can set the table. Shall I lock that in?"

*On screen: while she speaks, the board animates the re-plan — beans bar
shifts to a single pan at 6:53, mash bar turns amber (holding), gravy
chip moves from Maya to Dad, and the SERVE line settles back to 7:01.*

**DAD**
> "Lock it in."

### Beat 5 — The landing (2:10–2:40)

*Clock on the board: 6:58. The kitchen is calm, not frantic.*

**ALEXA+** *(proactive, from `get_dinner_status` at 18:58)*
> "Last call. Maya — rewhip the mash now. Sam, beans are in the pan.
> Dad, gravy straight from the pan, and Alex is carving with you.
> Everything lands at 7:01."

*The family sits down together. All four dishes hit the table in the
same shot.*

### End card (2:40–2:50, no narration)

```
AllAtOnce — the dinner conductor
Planned 7:00 · Chicken ran 15 behind · Landed 7:01
9 changes. One conversation. Zero timers were re-planned in the making of this dinner.
github.com/QuincyGB/allatonce  (MIT)
```

---

## Director's notes

- **Do not sell timers.** The video never demonstrates setting one. The
  first 90 seconds exist to reach the delay; the delay cascade *is* the
  product.
- The trade-off line in Beat 4 is not scripted copy — it is assembled by
  the server from the changes it actually computed (see `test-output.txt`
  Turn 5). If the build changes, re-record from the new output; do not
  hand-write Alexa's lines.
- If a take runs long, cut Beat 2's second sentence, never Beat 4.
- No third-party music or trademarks; kitchen sounds are the soundtrack.
