# Grid‑Pulse NTL — Overview

*Part of the plan set · see also: [01-architecture](01-architecture.md) · [02-detection-and-ai](02-detection-and-ai.md) · [03-timeline-96h](03-timeline-96h.md) · [04-tasks-roles](04-tasks-roles.md) · [05-demo-pitch](05-demo-pitch.md)*

> **Event:** Kafr El‑Sheikh hackathon (~**11 July 2026**) · build window ~96 h · **Team:** 3–4
> **Working name:** *Grid‑Pulse NTL*. ⚠️ **Rename before launch** — "Grid Pulse" is an existing portfolio project ([grid-pulse-reference in memory]); for a startup pick a distinct name: **AmperGuard** · **Rakib (رقيب)** · **WattWatch**.
>
> ⛔ This supersedes the earlier cyber‑IDS plan. That concept (false‑data injection as a *cyber* attack, rogue devices, DoS) has been **removed**. The reusable part — the Edge → API → queue → AI → dashboard architecture — carries over.

---

## One‑liner

**Grid‑Pulse NTL is an AI edge‑system that catches electricity theft on the distribution grid — and, crucially, tells the difference between real theft and the *natural* losses caused by heat and load, so it doesn't cry wolf.**

## The problem (this is the whole pitch — everyone in Egypt feels it)

Electricity distribution companies bleed on **Non‑Technical Loss (NTL)** — theft: illegal direct hooks, tampered meters, unlicensed workshops / brick factories / crypto‑mining rigs pulling power off the network. Estimated **~30 billion EGP/year** in Egypt. It also worsens **load‑shedding** (تخفيف الأحمال) by overloading transformers with unmetered demand.

The hard part isn't *measuring* power — it's **separating theft from legitimate loss.** Cables naturally lose energy as heat, and that loss **rises with temperature and load** (Egyptian summer!). A naive "meter‑difference" alarm floods operators with **false positives** and gets ignored. **That separation is exactly what our AI does — and it's our winning differentiator.**

## Who it's for

| Persona | Pain | We give them |
|---|---|---|
| **Distribution company / Ministry of Electricity** (B2G, primary) | billions lost, blind to *where* theft happens | per‑transformer theft map + evidence, few false alarms |
| **Field inspection teams** | chase random tips, waste trips | ranked, localized, time‑stamped leads |
| **Grid operations** | transformers overloaded by unmetered load | early overload + NTL signal |

## How it works (one paragraph)

An **Edge Node** (ESP32 + current sensor) clamps onto the feeder at a **distribution transformer**, measures current/voltage/power‑factor and computes the current waveform's **harmonic distortion (FFT/THD)**. The backend continuously runs an **energy balance** — power out of the transformer vs. the sum of registered meters — and an **AI model predicts the *expected technical (natural) loss*** from temperature, load and time. If the **measured loss exceeds the AI‑predicted natural loss** (and/or the harmonic signature screams "illegal hook"), it flags **suspected theft**, localizes it, and explains why. Full detail in [02-detection-and-ai](02-detection-and-ai.md).

## The single "aha" demo (this *is* the product)

1. **Lamp on** (registered load) → dashboard: **NORMAL — no loss**.
2. **Blow hot air on the sensor** (simulate summer heat) → dashboard: **TECHNICAL LOSS — natural, weather‑adjusted (AI baseline raised)**. *← the false‑positive killer; judges lean in here.*
3. **Secretly plug a hair‑dryer/heater into an *unregistered* outlet** (illegal hook) → draw spikes, power factor drops → AI fires: screen turns **RED — "Illegal Bypass Detected · Non‑Technical Loss"** with the estimated stolen watts + the "why".

Everything else exists to make those three beats look real.

## Scope — MVP (96 h) vs. cut

| Capability | In (MVP) | Cut / mock / later |
|---|---|---|
| ESP32 edge: I_rms, power, PF, freq via burden+bias+RMS | ✅ | multi‑phase board, Rogowski |
| Energy‑balance engine | ✅ (transformer vs. registered loads) | full utility meter integration |
| **AI technical‑loss baseline (regression)** | ✅ **HERO** | per‑cable physics model |
| **Harmonic/THD + power‑factor theft signal** | ✅ | 1D‑CNN harmonic classifier (stretch) |
| Temporal anomaly (Isolation Forest) | ✅ small | full behavioral suite |
| FastAPI + **Strict API Contract** + Redis + Celery | ✅ | HMAC signing (stretch) |
| Live dashboard (map + verdict + XAI) | ✅ | full ops console |
| Demo simulator (no‑hardware fallback) | ✅ | — |
| Smart‑contactor auto‑cutoff, TinyML, HW crypto | ❌ **Pitch as "Phase 2"** | ✅ roadmap |

## Business (why judges see a company, not a project)

- **B2G SaaS + HaaS** to distribution companies / Ministry of Electricity.
- **Pricing:** % of *recovered* stolen energy, or per‑transformer monthly subscription.
- **TAM:** ~30B EGP/yr NTL. Recovering even 10% ≈ 3B EGP. **ROI < 1 month** per kiosk (hardware ~300 USD vs. tens of thousands EGP/month leaked per feeder).
- **Wedge:** the AI false‑positive killer → inspectors trust the leads → adoption.

## What's original / defensible

Fresh code, our own detection AI and simulator. The old "Grid Pulse" monitoring platform is only distant inspiration — **different problem (theft vs. monitoring), different data (power/harmonics vs. device telemetry), our own models.** Rename to seal it.

## Glossary

- **NTL** — Non‑Technical Loss = theft/tampering (vs. **Technical Loss** = natural heat loss in cables/transformers).
- **CT sensor** — clip‑on Current Transformer (measures AC current without cutting the wire).
- **THD / PF** — Total Harmonic Distortion / Power Factor (waveform quality — distorted by illegal loads).
- **Energy balance** — power in vs. sum of metered power out; the residual hints at theft.
- **Edge Node** — the ESP32 unit at the transformer doing local measurement/FFT.
- **RMU / kiosk** — Ring Main Unit, the street distribution‑transformer cabinet.
