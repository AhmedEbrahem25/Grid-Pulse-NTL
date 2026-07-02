# Grid‑Pulse NTL — Demo & Pitch

*Part of the plan set · see also: [00-overview](00-overview.md) (problem) · [02-detection-and-ai](02-detection-and-ai.md)*

> Judges decide in the **first 2 h** (is the scope real?) and the **last 3 min** (the pitch). Grasp‑in‑<30 s, wow‑in‑the‑first‑minute. Lead with the **live 3‑beat demo**, not slides. **~30 % problem / 70 % demo+solution.** Re‑tailor to the **official rubric** the moment you have it.

---

## 1. The 90‑second demo script (3 beats)

**[0:00–0:20] Problem.**
> "Egypt loses about **30 billion pounds a year** to electricity theft — illegal hooks, tampered meters, unlicensed workshops. The problem isn't measuring power; it's that cables **naturally** lose energy as heat, so simple systems can't tell theft from normal loss and drown operators in false alarms. Watch how ours does."

**[0:20–0:35] Beat 1 — Normal.**
> *(lamp on)* "A registered customer. Power in equals power billed. Dashboard: **NORMAL, no loss.**"

**[0:35–0:60] Beat 2 — the false‑positive killer.**
> *(blow hot air on the sensor)* "Now it's a scorching afternoon — the cable heats up and loses more energy, *legitimately*. A naive system screams 'theft!' here. Ours? *(dashboard)* **TECHNICAL LOSS — natural, weather‑adjusted.** Our AI **predicted** how much loss is normal at this temperature and load — so it stays calm. **This is why inspectors will trust it.**"

**[0:60–1:20] Beat 3 — Theft, detected + explained.**
> *(secretly plug the hair‑dryer into an unregistered outlet)* "Now someone hooks an illegal load onto the line." *(screen turns RED)* "In seconds: **Illegal Bypass Detected — Non‑Technical Loss.** It even says **why** — ~1.8 kW unaccounted for, **beyond** what heat explains, the **power factor collapsed**, and the **waveform is distorted**. It tells the inspector *which feeder* and *how much* — actionable, not just an alarm."

**[1:20–1:30] Tagline.**
> "Grid‑Pulse turns billions in invisible losses into a **map of exactly where the theft is.**"

## 2. Choreography (rehearse to muscle memory)

| Step | Action | Expected | If it fails |
|---|---|---|---|
| 1 | dashboard open, transformer selected | live power, NORMAL | reload seeded tab |
| 2 | lamp on | NORMAL, loss≈0 | — |
| 3 | hot air on CT (or `sim technical`) | **TECHNICAL_LOSS**, baseline rises | narrate + `sim technical` |
| 4 | hair‑dryer → unregistered outlet (or `sim theft`) | **RED**, XAI, theft watts | `sim theft`, else video |
| 5 | tap alert → "dispatch inspection" | status updates | say it, move on |

**Pre‑demo checklist:** stack up (`docker-compose up`), transformers seeded, model loaded, **simulator armed as backup**, fallback video in a tab, circuit pre‑warmed & calibrated, hair‑dryer reachable.

## 3. Deck outline (~6 slides — back the demo, don't read)

1. **Title** — name + "AI that catches electricity theft — without false alarms" + team.
2. **Problem** — ~30B EGP/yr NTL; worsens load‑shedding; the theft‑vs‑natural‑loss trap.
3. **Live demo** — the 3 beats (the heart).
4. **How** — `energy balance → AI technical‑loss baseline → harmonics/PF → decision + XAI`; the baseline is the moat.
5. **Business** — B2G SaaS+HaaS; % of recovered energy; ROI < 1 month/kiosk; hardware upgrade path (Rogowski/IP65/LoRa).
6. **Roadmap / ask** — TinyML on‑device, auto‑cutoff smart contactors, theft‑location triangulation; what a win unlocks.

## 4. Rubric mapping (provisional)

| Criterion | We score via | Say |
|---|---|---|
| Innovation | AI that **separates technical vs non‑technical loss** | "the false‑positive problem everyone else ignores" |
| Technical depth | edge DSP (RMS/FFT) + balance + regression + anomaly + XAI, on real hardware | show the circuit + live detection |
| Impact | 30B EGP; load‑shedding relief; national scale | the felt story |
| Feasibility | **working POC + deployable stack**; cheap BOM; clear prod path | "~1000 EGP of parts, running now" |
| Presentation | 3 tight beats + explainable "why" + fallback | calm, timed, no dead air |

## 5. Handling the tough judge questions

- **"Will you clamp that toy sensor on a real transformer?"** → *No — the SCT‑013 proves the **AI + software**. In production we wrap **Rogowski coils** around the LV busbars inside the kiosk (non‑invasive, no outage), in an IP65 box, over LoRaWAN.* (Show the kiosk photo.)
- **"How do you avoid false accusations?"** → *We don't accuse — we **rank leads with confidence + evidence** (residual vs AI baseline, PF, THD) and dispatch inspectors. The AI baseline is exactly what suppresses false positives.*
- **"Data/privacy?"** → *We read **aggregate power at the transformer**, not per‑home behavior; registered meter totals only.*
- **"Is the data real?"** → *Synthetic + physics‑seeded for the POC; retrains on the utility's real readings on deployment.*

## 6. Fallback runbook (something will break)

| Failure | Fallback |
|---|---|
| Circuit/ADC misbehaves | run `POST /sim/scenario` — identical dashboard beats |
| Wi‑Fi down | local stack + simulator (no internet needed) |
| Whole rig dies | play the **recorded 90 s video**, narrate live |
| WS stalls | 2 s polling keeps the dashboard live |

**Always carry:** recorded video (offline), screenshot deck, phone hotspot, spare ESP32 + pre‑built circuit.

## 7. Elevator pitch (memorize)

> "Egypt loses ~30 billion pounds a year to electricity theft, and existing tools can't tell theft from the normal heat‑loss in cables — so they cry wolf and get ignored. **Grid‑Pulse** puts a cheap AI sensor on the transformer that **predicts how much loss is natural** right now, and flags only the rest as theft — explained, localized, and ranked for inspectors. We turn invisible losses into a **theft map**, and we bill a slice of what we help recover."
