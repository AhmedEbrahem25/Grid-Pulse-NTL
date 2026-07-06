# 🎬 Grid‑Pulse NTL — Full Demo Guide (Step by Step)

**What this file is:** a complete, click‑by‑click walkthrough of the Grid‑Pulse NTL demo — every command, every button, every expected result, and every fallback. Read this to *run* the demo. For the timed 90‑second stage script read [`plan/06-demo-runbook.md`](plan/06-demo-runbook.md); for the pitch words read [`plan/05-demo-pitch.md`](plan/05-demo-pitch.md).

> **The one idea the demo proves:** *A hot afternoon looks exactly like theft to a naïve system. Our AI predicts how much loss is **natural** right now, and flags only the unexplained excess — with a Theft Probability % and a reasons checklist.*

---

## 0. What you are about to show

The demo is a **live operations dashboard** for five distribution transformers in Kafr El‑Sheikh. You drive it with four buttons that inject a scenario into the selected transformer; the backend runs the **real detection pipeline** and pushes a verdict back to the screen over WebSocket.

| Button on screen | What it injects | Verdict you should see |
|---|---|---|
| **Normal load** | registered load only, energy balance holds | `NORMAL` — 0% theft, 0 reasons |
| **Hot day (technical)** | temperature rises, loss climbs | `TECHNICAL LOSS` — **no alarm** (the AI baseline rises with heat) 🏆 |
| **Legit industrial** | a *registered* high‑THD factory | `NORMAL / technical` — **not** flagged as theft (the 1D‑CNN knows a real factory) |
| **Inject theft** | an *unregistered* hook (workshop past the meter) | `THEFT` — screen turns **red**, **~94% probability**, **5/5 reasons**, ~3 kW unaccounted |

Everything is **replay‑safe** — run the beats in any order, any number of times. Nothing to reset between judges.

---

## 1. Prerequisites (once per machine)

You need **one** of these two ways to run it:

- **Path A — Docker (recommended for the stage):** Docker Desktop installed and running.
- **Path B — Local Python (no Docker):** Python 3.11+ installed.

Check what you have:

```bash
docker --version          # Path A
python --version          # Path B  (3.11 or newer)
```

Also confirm nothing else is already using **port 8000** and **port 6379** (Redis).

---

## 2. Setup — bring the stack up

### Path A · Docker (recommended)

Run these from the project root (`F:\project\Hackathon Kafrelsha5`):

```bash
cp .env.example .env                 # creates .env with INGEST_TOKEN=dev-token
docker compose up --build -d         # starts: api :8000 + redis + celery worker
```

**Optional — train the real model** (the physics fallback works fine without it, so this is *not* required for the demo):

```bash
docker compose run --rm -v "$PWD/ml:/mldir" -w /mldir api python train.py
```

Confirm the three containers are healthy:

```bash
docker compose ps                    # api, redis, worker should be "Up"
```

### Path B · Local Python (no Docker)

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Git Bash:
# source .venv/Scripts/activate

pip install -r backend/requirements.txt
export INGEST_TOKEN=dev-token        # PowerShell: $env:INGEST_TOKEN="dev-token"
uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000
```

> Local mode runs detection **inline** (no Redis/Celery needed) as long as `INLINE_DETECTION=true`, which is the default. That is the simplest, most demo‑safe setup.

---

## 3. Pre‑flight checklist (do this 10 minutes before presenting)

Open **http://localhost:8000** in a browser and verify each item:

- [ ] The **map loads** and shows **5 transformers**.
- [ ] The **feed / verdict list** shows recent events (it back‑fills from `GET /verdicts` so it looks live on open).
- [ ] The header status **dot is green ("live")** — the WebSocket is connected.
      *If it's amber ("polling") the demo still works — it auto‑falls back to 2‑second polling, invisible to the audience.*
- [ ] Click a transformer on the map to **select it** (e.g. `TX‑KFS‑0456`). The verdict panel should stop saying "Select a transformer…".
- [ ] Click **Normal load** once → confirm a clean `NORMAL` with **0 reasons**.
- [ ] Zoom the browser to **110–125%** so the big **94%** and the reasons read from the back of the room.
- [ ] Open the **PDF deck** (`pitch/Grid-Pulse-NTL.pdf`) in another tab as backup.
- [ ] Have the **recorded fallback video** ready (record one dry run — see §7).
- [ ] Click **⟳ Reset** (top‑right) once to clear old verdicts for a clean start.

---

## 4. Running the demo — the three beats, click by click

Select a transformer first (click it on the map). Then:

### Beat 1 — Normal  ·  click **Normal load**
- **Talk:** *"Here's a healthy feeder. Energy in matches energy billed. The AI says **normal, zero percent** — and note it's not just quiet, it tells us *why* it's calm."*
- **Expect:** green verdict, **NORMAL**, theft probability **0%**, **empty reasons** list.
- **Point at:** the green verdict and the empty reasons checklist.

### Beat 2 — The hard case (the money beat)  ·  click **Hot day (technical)**
- **Talk:** *"Now a 45‑degree day. Loss climbs — a dumb threshold screams *theft* right here. But watch: our AI baseline **rises with the heat**, because it learned copper losses grow when it's hot. Verdict stays **technical loss, no alarm**. This is the part every other team gets wrong."*
- **Expect:** amber verdict, **TECHNICAL LOSS**, **no alarm**. The expected‑loss baseline visibly rises to absorb the extra loss.
- **Pause here.** This is the false‑positive killer — let it land.

### Beat 3 — The catch  ·  click **Inject theft**
- **Talk:** *"Same transformer — now someone hooks a workshop past the meter. Screen goes **red. 94% theft probability.** And it doesn't just shout — it **shows its work**: ~3 kilowatts unaccounted, power factor collapsed to 0.66, harmonic distortion up, load off‑pattern. Five independent signals agree. An inspector gets **one tap: dispatch.**"*
- **Expect:** screen turns **red**, **THEFT**, **~94%** probability, **5/5 reasons met**, ~**3.1 kW** estimated unaccounted, recommended action **dispatch field inspection**.
- **Then:** click **Dispatch inspection** to show the lead status update (or **Dismiss**). Then stop talking.

### (Optional) Beat 2b — Legit industrial  ·  click **Legit industrial**
Use this only if a judge doubts the model. It injects a **registered** high‑THD factory — high harmonic distortion — and the verdict stays **not theft**, because the 1D‑CNN harmonic classifier tells a real factory apart from an illegal hook. This is the "0% false alarms on industrial load" claim, live.

> **Close line:** *"Working edge node, a real trained model, and a verdict you can act on. We turn a blind meter reading into a **decision** — and the first month of caught theft pays for the hardware."*

---

## 5. The simulator (backup + live telemetry stream)

The dashboard buttons call `POST /sim/scenario` directly, so you don't *need* the simulator. But it's the **no‑hardware fallback** and it makes the dashboard look alive with a streaming feed.

From the project root:

```bash
# stream normal telemetry once per second (dashboard looks "live"):
python simulator/simulate.py

# fire a single beat from the command line (identical to the buttons):
python simulator/simulate.py normal
python simulator/simulate.py technical
python simulator/simulate.py theft
```

Configure via environment variables if needed:

```bash
API=http://localhost:8000  INGEST_TOKEN=dev-token  TRANSFORMER=TX-KFS-0456  python simulator/simulate.py
```

What it does: `set_registered()` posts the registered meter reading (6800 W baseline), then either fires one `/sim/scenario` and exits, or loops posting realistic telemetry (small natural variation, PF 0.96–0.99, THD 3–6%, temp 26–30 °C) so the dashboard has a live pulse.

---

## 6. Reset & repeatability

- The demo is **replay‑safe** — a `theft` followed by a `normal` comes back cleanly (0 reasons). A load *drop* is never mistaken for theft.
- **⟳ Reset** (top‑right of the dashboard) clears all verdicts and history for a fresh run between judges. It asks for confirmation first.
- You can run the beats in **any order, any number of times**. Nothing to reset between judges unless you want a clean feed.

---

## 7. Fallbacks (in order of preference)

1. **Live on localhost** — the plan.
2. **WebSocket dropped?** The dashboard auto‑falls back to **2‑second polling** (header dot goes amber). Keep going — it's invisible to the audience.
3. **Buttons/backend flaky?** Fire the beats from the CLI instead: `python simulator/simulate.py theft`.
4. **Backend won't start?** Play the **recorded video** — record one now: run the three beats, screen‑capture, keep it ≤ 90 s.
5. **Total laptop failure?** Present the **PDF deck** (`pitch/Grid-Pulse-NTL.pdf`) — the hero slide *is* the verdict.
6. **Projector too dim?** The dashboard and deck are both high‑contrast dark; zoom the browser and lean on the big 94%.

**Always carry:** the recorded video (offline), the PDF/screenshot deck, a phone hotspot, and a spare pre‑built ESP32 circuit.

---

## 8. Troubleshooting

| Symptom | Fix |
|---|---|
| Map doesn't load at `localhost:8000` | Is the API up? `docker compose ps` (Path A) or check the uvicorn terminal (Path B). Check nothing else owns port 8000. |
| Header dot is amber, not green | WebSocket didn't connect — it's fine, polling covers you. To fix: reload the tab; check no proxy is blocking `/ws/stream`. |
| Button does nothing | Did you **select a transformer** first? Open the browser console (F12) for errors. Try the CLI: `python simulator/simulate.py theft`. |
| `/ingest` returns **401** | Wrong token. The edge/simulator token must match `INGEST_TOKEN` in `.env` (`dev-token` by default). |
| `/ingest` returns **422** | Malformed body — the contract is strict (zero‑trust). This is *expected* behavior when you send junk; the simulator sends valid payloads. |
| Verdict looks stale | Click **⟳ Reset**, then re‑run the beat. |
| Want the real model, not the physics fallback | Run `python ml/train.py` (Path B) or the `docker compose run … python train.py` command in §2. The demo works either way. |

---

## 9. Verify it yourself (before you trust the stage)

```bash
# Path A (Docker): runs the 3 beats + confirms the contract rejects junk
docker compose exec api python backend/tests/test_detection.py

# Regenerate the evaluation report (600 held-out scenarios):
python ml/evaluate.py        # → ml/artifacts/eval_report.json
```

Expected headline numbers: theft **precision 1.00** (0 false positives), **F1 0.88**, and **0% false alarms on legitimate industrial load**.

---

## 10. Rapid answers to judge questions

| Question | Answer |
|---|---|
| "Is the AI real or scripted?" | "Real — the verdict is computed live. Here's the same physics on a different transformer." *(select another, inject theft)* |
| "How do you avoid false positives?" | "The AI predicts *normal* loss for the current temp and load; only the **unexplained residual**, confirmed by power factor and harmonics, is flagged. You saw it stay quiet on the hot day and on the industrial load." |
| "Is it temperature‑only?" | "No — seven features. Learned importance is **load 0.58, temperature 0.27, current 0.15**, plus hour, day, voltage, rating." |
| "What's the hardware?" | "ESP32 + a split‑core CT with a proper burden + bias circuit today; **Rogowski coils on the LV busbar over LoRaWAN** in production." |
| "How do you avoid false accusations?" | "We don't accuse — we **rank leads with confidence + evidence** and dispatch inspectors. The AI baseline is exactly what suppresses false positives." |
| "Is the data real?" | "Synthetic + physics‑seeded for the POC; retrains on the utility's real readings on deployment." |
| "Business model?" | "B2G — a share of recovered energy. ~30B EGP pool, ROI under a month per kiosk. The labelled theft data compounds into a moat." |

---

## 11. What NOT to do on stage

- Don't explain the pipeline architecture unless asked — **show the three beats, then stop talking.**
- Don't say "we think" or "it should" — the numbers are real; state them flat.
- Don't run `train.py` live (do it in pre‑flight). The physics fallback covers you if you forget.
- Don't rotate the demo token or change ports right before presenting.

> **The line they'll remember:** *"A hot afternoon looks like theft — our AI knows the difference."*
