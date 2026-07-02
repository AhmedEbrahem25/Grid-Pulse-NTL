# Grid‑Pulse NTL — Strict API Contract

The **single source of truth** for how an Edge Node talks to the backend. Firmware, backend, and simulator **must** all conform to [`edge_telemetry.schema.json`](edge_telemetry.schema.json) (JSON Schema draft 2020‑12).

> **Zero‑trust rule:** the backend validates every payload against this schema and **rejects non‑conforming ones with HTTP 422**. No "best effort" parsing.

---

## Endpoint

```
POST /ingest
Content-Type: application/json
Authorization: Bearer <INGEST_TOKEN>
Body: <edge telemetry payload>          # must validate against the schema
→ 200 {"accepted": true, "reading_id": "..."}
→ 422 {"accepted": false, "errors": [ ... ]}   # schema violations
→ 401 if the bearer token is missing/wrong
```

Companion endpoint for registered consumption (used by the energy balance):
```
POST /meters/reading
{"meter_id":"M-0007","ts":1720003600,"energy_wh_interval":1.90,"p_active_w":6840}
```

## Field notes

| Field | Meaning | Used by |
|---|---|---|
| `device_id` | edge id `GP-EDGE-…` | routing, replay guard |
| `seq` | monotonic per device | gap/replay detection |
| `site.transformer_id` | which transformer `TX-…` | energy balance, map |
| `measurement.energy_wh_interval` | Wh out of the transformer this window | **energy balance** |
| `phases[].p_active_w` | active power (W) | balance, load feature |
| `phases[].power_factor` | active/apparent | **theft signal** (drops on illegal loads) |
| `phases[].thd_i_pct` + `harmonics[]` | waveform distortion | **theft signal** |
| `env.temp_c` | ambient temperature | **AI technical‑loss baseline** |

See [`../plan/02-detection-and-ai.md`](../plan/02-detection-and-ai.md) for how each field drives detection.

## Example — NORMAL (registered load only)

```json
{
  "schema_version": "1.0",
  "device_id": "GP-EDGE-000123",
  "firmware": "1.0.0",
  "ts": 1720003600,
  "seq": 4211,
  "site": { "transformer_id": "TX-KFS-0456", "feeder_id": "F-03", "lat": 31.1107, "lng": 30.9388 },
  "measurement": {
    "window_ms": 1000,
    "energy_wh_interval": 1.95,
    "phases": [
      { "phase": "single", "i_rms_a": 30.4, "v_rms_v": 228.5, "p_active_w": 6820.0,
        "s_apparent_va": 6950.0, "power_factor": 0.981, "freq_hz": 49.98, "thd_i_pct": 4.1 }
    ]
  },
  "env": { "temp_c": 27.0, "humidity_pct": 50.0 },
  "health": { "rssi_dbm": -67, "uptime_s": 84213, "tamper": false }
}
```

## Example — THEFT (unregistered high‑draw load, distorted waveform)

```json
{
  "schema_version": "1.0",
  "device_id": "GP-EDGE-000123",
  "firmware": "1.0.0",
  "ts": 1720003720,
  "seq": 4231,
  "site": { "transformer_id": "TX-KFS-0456", "feeder_id": "F-03", "lat": 31.1107, "lng": 30.9388 },
  "measurement": {
    "window_ms": 1000,
    "energy_wh_interval": 2.68,
    "phases": [
      { "phase": "single", "i_rms_a": 41.9, "v_rms_v": 226.0, "p_active_w": 8990.0,
        "s_apparent_va": 12660.0, "power_factor": 0.710, "freq_hz": 49.95, "thd_i_pct": 18.3,
        "harmonics": [ { "h": 3, "mag_pct": 12.1 }, { "h": 5, "mag_pct": 7.8 } ] }
    ]
  },
  "env": { "temp_c": 27.2, "humidity_pct": 50.0 },
  "health": { "rssi_dbm": -66, "uptime_s": 84333, "tamper": false }
}
```

The backend pairs this with the registered meter total (~6.8 kW). The energy balance sees **~2.2 kW unaccounted**, the AI baseline says heat only explains a few hundred W at 27 °C, and PF/THD confirm an illegal load → **NTL_THEFT_SUSPECTED**.

## Validate locally

```bash
# Python
pip install jsonschema
python -c "import json,jsonschema; \
  s=json.load(open('contracts/edge_telemetry.schema.json')); \
  p=json.load(open('contracts/example_normal.json')); \
  jsonschema.validate(p,s); print('valid')"
```

The backend uses the **Pydantic** mirror in `backend/app/contract.py` (kept 1:1 with this schema) so validation is identical in code and contract. **If you change one, change both** (there's a test that checks they agree).
