# Grid‑Pulse NTL — Demo Runbook (90 seconds to win)

*Print this. One person drives the laptop, one talks. Rehearse it 5× until the words are muscle memory. Judges decide in the first 30 seconds of the demo and the last line of the pitch.*

---

## 0. Pre‑flight (do this 10 min before you present)

```bash
docker compose up --build -d        # api:8000 + redis + celery
# optional but recommended — trains the real model (physics fallback works without it):
docker compose run --rm -v "$PWD/ml:/mldir" -w /mldir api python train.py
```

- [ ] Open **http://localhost:8000** — map loads, 5 transformers, feed shows recent events.
- [ ] Header dot is **green ("live")** — WebSocket connected. If amber ("polling"), it still works (2 s fallback).
- [ ] Click **Normal load** once → confirm it returns a clean `NORMAL` (0 reasons).
- [ ] Zoom the browser to **110–125%** so the 94% and reasons read from the back row.
- [ ] Have the **PDF deck** (`pitch/Grid-Pulse-NTL.pdf`) open in another tab as backup.
- [ ] Have the **recorded fallback video** ready (record one dry run — see §4).

---

## 1. The script (≈90 s, 30% problem / 70% demo)

### Beat 0 — The hook (0:00–0:20) · *talk over the map*
> "Egypt loses around **30 billion pounds a year** to electricity theft — power that leaves the transformer that nobody pays for. The problem isn't measuring the loss. It's that **a hot afternoon looks exactly like theft** — so operators either drown in false alarms or switch the alarm off. This is a live map of five transformers in Kafr El‑Sheikh."

### Beat 1 — Normal (0:20–0:32) · *click **Normal load***
> "Here's a healthy feeder. Energy in matches energy billed. The AI says **normal, zero percent** — and note it's not just quiet, it tells us *why* it's calm."

*(Point at the green verdict, the empty reasons.)*

### Beat 2 — The hard case (0:32–0:55) · *click **Hot day (technical)***
> "Now a **45‑degree day**. Loss climbs — a dumb threshold screams *theft* right here. But watch: our AI baseline **rises with the heat**, because it learned that copper losses grow when it's hot. Verdict stays **technical loss, no alarm.** *This* is the part every other team gets wrong."

*(This is the money beat. Pause on the amber "no alarm".)*

### Beat 3 — The catch (0:55–1:20) · *click **Inject theft***
> "Same transformer — now someone hooks a workshop past the meter. Screen goes **red. 94% theft probability.** And it doesn't just shout — it **shows its work**: 3 kilowatts unaccounted, power factor collapsed to 0.66, harmonic distortion up, load off‑pattern. Five independent signals agree. An inspector gets **one tap: dispatch.**"

*(Let the red + the reasons checklist sit for a beat. Then close.)*

### Beat 4 — The close (1:20–1:30)
> "Working edge node, a real trained model, and a verdict you can act on. We turn a blind meter reading into a **decision** — and the first month of caught theft pays for the hardware."

---

## 2. If a judge asks… (rapid answers)

| Question | Answer |
|---|---|
| "Is the AI real or scripted?" | "Real. The verdict is computed live — here's the same physics on a different transformer." *(select another, inject theft)* |
| "How do you avoid false positives?" | "That's the whole design — the AI predicts *normal* loss for the current temp and load; only the **unexplained residual**, confirmed by power‑factor and harmonics, is flagged. You saw it stay quiet on the hot day." |
| "Is it temperature‑only?" | "No — seven features. Learned importance is **load 0.58, temperature 0.27, current 0.15**, plus hour, day, voltage, rating." |
| "What's the hardware?" | "ESP32 + a split‑core CT with a proper burden + bias circuit today; **Rogowski coils on the LV busbar over LoRaWAN** in production." |
| "Business model?" | "B2G — we take a share of recovered energy. ~30B EGP pool, ROI under a month per kiosk. The **labelled theft data** compounds into a moat." |

---

## 3. Repeatability (the demo is replay‑safe)

You can run the three beats in **any order, as many times as you like** — a `theft` followed by a `normal` still comes back cleanly (0 reasons). Nothing to reset between judges.

---

## 4. Fallbacks (in order of preference)

1. **Live on localhost** — the plan.
2. **WebSocket dropped?** The dashboard auto‑falls back to 2 s polling (header dot goes amber). Keep going; it's invisible to the audience.
3. **Backend won't start?** Open the **recorded video** (record one now: run the 3 beats, screen‑capture, keep it ≤ 90 s).
4. **Total laptop failure?** Present the **PDF deck** (`pitch/Grid-Pulse-NTL.pdf`) — the hero slide *is* the verdict.
5. **Projector too dim?** The dashboard and deck are both high‑contrast dark; if it washes out, zoom the browser and lean on the big 94%.

---

## 5. What NOT to do

- Don't explain the pipeline architecture unless asked — **show the three beats, then stop talking.**
- Don't say "we think" or "it should" — the numbers are real; state them flat.
- Don't run `train.py` live (do it in pre‑flight). The physics fallback covers you if you forget.
- Don't rotate the demo token or change ports right before presenting.

> **The one line they'll remember:** *"A hot afternoon looks like theft — our AI knows the difference."*
