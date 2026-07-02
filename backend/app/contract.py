"""Pydantic mirror of contracts/edge_telemetry.schema.json.

Kept 1:1 with the JSON Schema. If you change one, change the other
(test_contract.py checks a sample validates against both).
"""
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class Harmonic(BaseModel):
    model_config = ConfigDict(extra="forbid")
    h: int = Field(ge=1, le=50)
    mag_pct: float = Field(ge=0, le=100)


class Phase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    phase: Literal["L1", "L2", "L3", "single"]
    i_rms_a: float = Field(ge=0, le=5000)
    v_rms_v: Optional[float] = Field(default=None, ge=0, le=1000)
    p_active_w: float = Field(ge=-100_000, le=5_000_000)
    s_apparent_va: Optional[float] = Field(default=None, ge=0, le=5_000_000)
    power_factor: float = Field(ge=0, le=1)
    freq_hz: float = Field(ge=45, le=65)
    thd_i_pct: Optional[float] = Field(default=None, ge=0, le=100)
    harmonics: Optional[List[Harmonic]] = Field(default=None, max_length=16)


class Site(BaseModel):
    model_config = ConfigDict(extra="forbid")
    transformer_id: str = Field(pattern=r"^TX-[A-Z0-9-]{3,20}$")
    feeder_id: Optional[str] = Field(default=None, max_length=16)
    lat: Optional[float] = Field(default=None, ge=-90, le=90)
    lng: Optional[float] = Field(default=None, ge=-180, le=180)


class Measurement(BaseModel):
    model_config = ConfigDict(extra="forbid")
    window_ms: int = Field(ge=200, le=60_000)
    energy_wh_interval: Optional[float] = Field(default=None, ge=0)
    phases: List[Phase] = Field(min_length=1, max_length=3)


class Env(BaseModel):
    model_config = ConfigDict(extra="forbid")
    temp_c: Optional[float] = Field(default=None, ge=-20, le=90)
    humidity_pct: Optional[float] = Field(default=None, ge=0, le=100)
    enclosure_temp_c: Optional[float] = Field(default=None, ge=-20, le=120)


class Health(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rssi_dbm: Optional[int] = Field(default=None, ge=-120, le=0)
    uptime_s: Optional[int] = Field(default=None, ge=0)
    tamper: Optional[bool] = None


class EdgePayload(BaseModel):
    """The Strict API Contract payload posted to POST /ingest."""
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["1.0"]
    device_id: str = Field(pattern=r"^GP-EDGE-[A-Z0-9]{4,12}$")
    firmware: Optional[str] = Field(default=None, pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$")
    ts: int = Field(ge=1_700_000_000)
    seq: int = Field(ge=0)
    site: Site
    measurement: Measurement
    env: Optional[Env] = None
    health: Optional[Health] = None
    sig: Optional[str] = Field(default=None, pattern=r"^hmac-sha256:[A-Za-z0-9+/=]+$")

    # --- convenience aggregates used by the detection pipeline ---
    def total_active_w(self) -> float:
        return sum(p.p_active_w for p in self.measurement.phases)

    def worst_power_factor(self) -> float:
        return min(p.power_factor for p in self.measurement.phases)

    def max_thd(self) -> float:
        return max((p.thd_i_pct or 0.0) for p in self.measurement.phases)

    def primary_phase(self) -> str:
        return self.measurement.phases[0].phase


class MeterReading(BaseModel):
    model_config = ConfigDict(extra="forbid")
    meter_id: str
    transformer_id: Optional[str] = Field(default=None, pattern=r"^TX-[A-Z0-9-]{3,20}$")
    ts: int = Field(ge=1_700_000_000)
    energy_wh_interval: float = Field(ge=0)
    p_active_w: float = Field(ge=0)
