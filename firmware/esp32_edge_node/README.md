# ESP32 Edge Node — wiring & calibration

The **SCT-013-000** (100A/50mA) is a *current-output* CT with **no internal burden resistor**, and its output is **AC — it swings negative**. The ESP32 ADC reads **0–3.3V only** and a negative voltage will corrupt readings or **damage the pin**. So you MUST condition the signal: a **burden resistor** + a **1.65V DC bias** + a filter cap.

## Signal-conditioning circuit

```
                 ┌───────────────┬──────────────┐
   SCT-013 ─────►│               │              │
   (two leads)   Rburden(33Ω)   Cbias(10µF)     │
                 │               │              │
      ┌──────────┴───────┐       │        ESP32 3.3V
      │  10kΩ ── mid ── 10kΩ ────┴──────── GND   │
      │  3.3V           GND                       │
      └── mid (1.65V) ── one CT lead              │
          other CT lead ─────────────────► GPIO34 (ADC1)
```

1. **Burden resistor (Rb):** across the CT leads, converts the 50 mA into a voltage EmonLib can read. `Rb = 33Ω` is a good match for ESP32 3.3V (keeps the peak within the 0–1.65V half-swing). `22Ω` also works.
2. **DC bias (1.65V):** two `10kΩ` resistors form a divider from 3.3V→GND; the midpoint (~1.65V) lifts the AC waveform so it never goes negative. Tie one CT lead + the burden to this midpoint.
3. **Filter cap:** `10µF` from the 1.65V midpoint to GND stabilises the bias.
4. **To the ADC:** the other CT lead goes to `GPIO34` (ADC1). Never feed the raw CT straight into the ADC.

## Calibration

EmonLib needs a **calibration factor = turns_ratio / burden_ohms**.
- SCT-013-000 turns ratio = **2000:1** (100A / 0.05A).
- With `Rb = 33Ω` → `2000 / 33 ≈ 60.6` → `CAL_FACTOR 60.6` in `config.h`.
- With `Rb = 22Ω` → `≈ 90.9`.

Then trim: clamp the CT around a **known load** (e.g. a 1000 W heater at 230 V ≈ 4.35 A) and adjust `CAL_FACTOR` until `Irms` matches within ±5%.

## POC scope / honesty

- The SCT gives **current only**. We assume nominal voltage (`230 V`) and a fixed `power_factor` (`0.95`). To measure **real PF and THD** (the harmonic theft signal), add a voltage sensor (e.g. **ZMPT101B**) and FFT the two waveforms.
- Production uses **Rogowski coils** around the LV busbars in the transformer kiosk — see `plan/05-demo-pitch.md` §5.

## Flash

Arduino IDE → install **ESP32 boards** + the **EmonLib** library → open `esp32_edge_node.ino` → edit `config.h` (WiFi, `INGEST_URL`, `INGEST_TOKEN`) → upload. Watch Serial at 115200: `Irms=.. P=.. -> 200`.
