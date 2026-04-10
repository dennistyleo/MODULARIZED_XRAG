"""
Module: telemetry_aggregator
Version: 1.0.0
Description: Telemetry Aggregator for XR-PMC — collects data from all interfaces
             (PMBus, SMBus, I2C, I3C, SPI, UART, SERDES, GPIO) and evaluates
             telemetry axioms TEL_RED_01 through TEL_GPIO_10.

In production: replace async poll stubs with real hardware driver calls.
In test mode: uses mock data to validate the axiom evaluation logic.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ── Enums ─────────────────────────────────────────────────────────────────────
class BusType(str, Enum):
    PMBUS  = "pmbus"
    SMBUS  = "smbus"
    I2C    = "i2c"
    I3C    = "i3c"
    SPI    = "spi"
    UART   = "uart"
    JTAG   = "jtag"
    SERDES = "serdes"
    GPIO   = "gpio"


# ── Data ─────────────────────────────────────────────────────────────────────
@dataclass
class TelemetrySample:
    timestamp_us: int
    source: BusType
    device_id: int
    register: int
    value: Any
    crc_ok: bool = True


@dataclass
class InterfaceTelemetry:
    """Aggregated snapshot from all interfaces."""
    # PMBus / SMBus / I2C
    vout_mv:   Dict[int, float] = field(default_factory=dict)
    iout_ma:   Dict[int, float] = field(default_factory=dict)
    temp_c:    Dict[int, float] = field(default_factory=dict)
    pgood:     Dict[int, bool]  = field(default_factory=dict)
    # Current sharing (TEL_RED_01)
    phase_currents_ma:    Dict[str, float] = field(default_factory=dict)
    balance_error_pct:    float = 0.0
    # Ride-through (TEL_RT_02)
    vcap_mv:    float = 0.0
    icap_ma:    float = 0.0
    rt_state:   str   = "IDLE"
    hold_time_ms: float = 0.0
    # SERDES (TEL_SERDES_08)
    eye_height_mv: float = 0.0
    eye_width_ui:  float = 0.0
    ber:           float = 0.0
    serdes_locked: bool  = True
    # GPIO (TEL_GPIO_10)
    fault_flags:   Dict[str, bool] = field(default_factory=dict)
    enable_states: Dict[str, bool] = field(default_factory=dict)


@dataclass
class AxiomCheckResult:
    axiom_id: str
    passed: bool
    violations: List[Dict[str, Any]] = field(default_factory=list)
    evidence:   List[Dict[str, Any]] = field(default_factory=list)


# ── Telemetry Aggregator ─────────────────────────────────────────────────────
class TelemetryAggregator:
    """
    Collects telemetry from all XR-PMC interfaces.
    Hardware driver methods are stubs — replace with real implementations.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.config   = config or _DEFAULT_CONFIG
        self.samples: List[TelemetrySample] = []
        self.current  = InterfaceTelemetry()

    # ── PMBus (TEL_PMBUS_03) ─────────────────────────────────────────────────
    async def poll_pmbus(self) -> Dict[int, Dict[str, Any]]:
        """Poll PMBus regulators via READ_VOUT/IOUT/TEMPERATURE commands."""
        results: Dict[int, Dict] = {}
        for dev in self.config.get("pmbus", {}).get("devices", []):
            try:
                # STUB — replace with: await pmbus_driver.read_word(dev["addr"], 0x8B)
                vout_raw = dev.get("mock_vout_raw", 0)
                iout_raw = dev.get("mock_iout_raw", 0)
                temp_raw = dev.get("mock_temp_raw", 0)
                results[dev["rail_id"]] = {
                    "vout_mv": self._linear11_to_float(vout_raw) * 1000,
                    "iout_ma": self._linear11_to_float(iout_raw) * 1000,
                    "temp_c":  self._linear11_to_float(temp_raw),
                    "pgood":   dev.get("mock_pgood", True),
                }
                self._record(BusType.PMBUS, dev["rail_id"], 0x8B, results[dev["rail_id"]])
            except Exception as exc:
                logger.error("E002: PMBus poll failed for device %s — %s", dev, exc)
        return results

    # ── Current Sharing (TEL_RED_01) ─────────────────────────────────────────
    async def poll_current_sharing(self) -> Dict[str, Any]:
        """Monitor active OR-ring current balance across parallel phases."""
        cfg = self.config.get("current_sharing", {})
        phases = cfg.get("phases", [])
        total  = 0.0
        phase_currents: Dict[str, float] = {}

        for ph in phases:
            # STUB — replace with real ADC read
            current_ma = ph.get("mock_current_ma", 0.0)
            phase_currents[ph["id"]] = current_ma
            total += current_ma

        if total == 0 or len(phases) == 0:
            return {"phase_currents_ma": phase_currents, "total_ma": 0, "balance_error_pct": 0.0, "balanced": True}

        ideal = total / len(phases)
        max_err = max(
            abs((i - ideal) / ideal) * 100 for i in phase_currents.values()
        )
        balanced = max_err <= cfg.get("balance_error_max_pct", 5.0)
        return {
            "phase_currents_ma":  phase_currents,
            "total_ma":           total,
            "balance_error_pct":  round(max_err, 2),
            "balanced":           balanced,
        }

    # ── Ride-Through (TEL_RT_02) ─────────────────────────────────────────────
    async def poll_ride_through(self) -> Dict[str, Any]:
        """Monitor RT capacitor voltage, current, state."""
        cfg    = self.config.get("ride_through", {})
        vcap   = cfg.get("mock_vcap_mv", 1200)
        icap   = cfg.get("mock_icap_ma", 0)
        temp   = cfg.get("mock_temp_c", 25)
        enable = cfg.get("mock_rt_enable", False)
        ready  = cfg.get("mock_rt_ready", True)

        state  = "HOLD" if (enable and ready) else ("TRANSITION" if enable else "IDLE")
        vcap_ok = vcap >= cfg.get("vcap_min_mv", 800)
        temp_ok = temp <= cfg.get("temp_max_c", 85)

        return {
            "vcap_mv": vcap, "icap_ma": icap, "temp_c": temp,
            "state": state, "vcap_ok": vcap_ok, "temp_ok": temp_ok,
            "hold_time_ms": cfg.get("mock_hold_time_ms", 0),
        }

    # ── SERDES (TEL_SERDES_08) ────────────────────────────────────────────────
    async def poll_serdes(self) -> Dict[str, Any]:
        """Monitor SERDES lock, eye height/width, BER."""
        cfg = self.config.get("serdes", {})
        return {
            "eye_height_mv": cfg.get("mock_eye_height_mv", 150),
            "eye_width_ui":  cfg.get("mock_eye_width_ui", 0.65),
            "ber":           cfg.get("mock_ber", 1e-14),
            "locked":        cfg.get("mock_locked", True),
        }

    # ── GPIO (TEL_GPIO_10) ────────────────────────────────────────────────────
    async def poll_gpio(self) -> Dict[str, Any]:
        """Read GPIO state bank showing PGOOD, FAULT, ENABLE signals."""
        cfg   = self.config.get("gpio", {})
        pins  = cfg.get("pins", [])
        state = {p["name"]: p.get("mock_level", False) for p in pins}
        return {"pins": state}

    # ── Axiom Evaluation ─────────────────────────────────────────────────────
    def evaluate_tel_red_01(self, sharing: Dict) -> AxiomCheckResult:
        """TEL_RED_01: Current balance ≤ 5% error."""
        passed = sharing.get("balanced", True)
        err    = sharing.get("balance_error_pct", 0)
        ev_id  = "CURRENT_SHARE_BALANCED" if passed else "CURRENT_SHARE_IMBALANCE"
        return AxiomCheckResult(
            axiom_id="TEL_RED_01", passed=passed,
            violations=[] if passed else [{"balance_error_pct": err}],
            evidence=[{"event_id": ev_id, "payload": sharing}],
        )

    def evaluate_tel_rt_02(self, rt: Dict) -> AxiomCheckResult:
        """TEL_RT_02: Vcap ≥ Vmin, hold ≥ 50ms."""
        cfg    = self.config.get("ride_through", {})
        violations: List[Dict] = []
        if not rt.get("vcap_ok"):
            violations.append({"reason": "VCAP_BELOW_THRESHOLD", "vcap_mv": rt["vcap_mv"]})
        hold   = rt.get("hold_time_ms", 0)
        min_hold = cfg.get("hold_time_ms_min", 50)
        if rt["state"] == "DONE" and hold < min_hold:
            violations.append({"reason": "HOLD_TIME_INSUFFICIENT", "hold_ms": hold, "min_ms": min_hold})
        ev_id  = "RT_HOLD" if not violations else "RT_FAULT"
        return AxiomCheckResult(
            axiom_id="TEL_RT_02", passed=len(violations) == 0,
            violations=violations, evidence=[{"event_id": ev_id, "payload": rt}],
        )

    def evaluate_tel_serdes_08(self, serdes: Dict) -> AxiomCheckResult:
        """TEL_SERDES_08: BER ≤ 1e-12, eye height ≥ 100mV, eye width ≥ 0.5UI."""
        cfg = self.config.get("serdes", {})
        violations: List[Dict] = []
        ber_max    = cfg.get("ber_max", 1e-12)
        eye_h_min  = cfg.get("eye_height_mv_min", 100)
        eye_w_min  = cfg.get("eye_width_ui_min", 0.5)

        if serdes["ber"] > ber_max:
            violations.append({"metric": "BER", "measured": serdes["ber"], "limit": ber_max})
        if serdes["eye_height_mv"] < eye_h_min:
            violations.append({"metric": "eye_height", "measured": serdes["eye_height_mv"], "limit": eye_h_min})
        if serdes["eye_width_ui"] < eye_w_min:
            violations.append({"metric": "eye_width", "measured": serdes["eye_width_ui"], "limit": eye_w_min})

        ev_id = "SERDES_STATUS" if not violations else "SERDES_BER_EXCEEDED"
        return AxiomCheckResult(
            axiom_id="TEL_SERDES_08", passed=len(violations) == 0,
            violations=violations, evidence=[{"event_id": ev_id, "payload": serdes}],
        )

    # ── Full Poll + Evaluate ──────────────────────────────────────────────────
    async def poll_and_evaluate(self) -> Dict[str, Any]:
        """Collect all telemetry and evaluate all TEL axioms."""
        pmbus   = await self.poll_pmbus()
        sharing = await self.poll_current_sharing()
        rt      = await self.poll_ride_through()
        serdes  = await self.poll_serdes()
        gpio    = await self.poll_gpio()

        # Update current snapshot
        for rail_id, data in pmbus.items():
            self.current.vout_mv[rail_id] = data.get("vout_mv", 0)
            self.current.iout_ma[rail_id] = data.get("iout_ma", 0)
            self.current.temp_c[rail_id]  = data.get("temp_c", 0)
            self.current.pgood[rail_id]   = data.get("pgood", True)

        self.current.phase_currents_ma = sharing.get("phase_currents_ma", {})
        self.current.balance_error_pct = sharing.get("balance_error_pct", 0)
        self.current.vcap_mv    = rt.get("vcap_mv", 0)
        self.current.rt_state   = rt.get("state", "IDLE")
        self.current.hold_time_ms = rt.get("hold_time_ms", 0)
        self.current.eye_height_mv = serdes.get("eye_height_mv", 0)
        self.current.eye_width_ui  = serdes.get("eye_width_ui", 0)
        self.current.ber           = serdes.get("ber", 0)
        self.current.serdes_locked = serdes.get("locked", True)

        axiom_results = [
            self.evaluate_tel_red_01(sharing).__dict__,
            self.evaluate_tel_rt_02(rt).__dict__,
            self.evaluate_tel_serdes_08(serdes).__dict__,
        ]
        # Additional interface sub-checks (PMBus timeout, I2C health, SPI CRC, GPIO latency)
        # would be added here with real driver integration

        overall = all(r["passed"] for r in axiom_results)
        return {
            "timestamp_us": int(time.time() * 1_000_000),
            "overall_pass": overall,
            "axiom_results": axiom_results,
            "raw": {
                "pmbus": pmbus, "current_sharing": sharing,
                "ride_through": rt, "serdes": serdes, "gpio": gpio,
            },
        }

    # ── Helpers ───────────────────────────────────────────────────────────────
    @staticmethod
    def _linear11_to_float(value: int) -> float:
        """Convert PMBus Linear-11 fixed-point to float."""
        exponent = (value >> 11) & 0x1F
        mantissa = value & 0x7FF
        if exponent > 15:
            exponent -= 32
        return float(mantissa) * (2 ** exponent)

    def _record(self, bus: BusType, device_id: int, reg: int, value: Any) -> None:
        self.samples.append(TelemetrySample(
            timestamp_us=int(time.time() * 1_000_000),
            source=bus, device_id=device_id, register=reg, value=value,
        ))


# ── Default Config (mirrors interfaces.json structure) ───────────────────────
_DEFAULT_CONFIG: Dict[str, Any] = {
    "pmbus": {
        "devices": [
            {"rail_id": 0, "addr": 0x20, "name": "VR_VCORE",
             "mock_vout_raw": 0x0800, "mock_iout_raw": 0x0500, "mock_temp_raw": 0x0190, "mock_pgood": True},
            {"rail_id": 1, "addr": 0x21, "name": "VR_VDDQ",
             "mock_vout_raw": 0x0E00, "mock_iout_raw": 0x0280, "mock_temp_raw": 0x0180, "mock_pgood": True},
        ]
    },
    "current_sharing": {
        "phases": [{"id": "A", "mock_current_ma": 5000.0}, {"id": "B", "mock_current_ma": 5200.0}],
        "balance_error_max_pct": 5.0,
    },
    "ride_through": {
        "vcap_min_mv": 800, "hold_time_ms_min": 50, "temp_max_c": 85,
        "mock_vcap_mv": 1200, "mock_icap_ma": 0, "mock_temp_c": 35,
        "mock_rt_enable": False, "mock_rt_ready": True, "mock_hold_time_ms": 0,
    },
    "serdes": {
        "ber_max": 1e-12, "eye_height_mv_min": 100, "eye_width_ui_min": 0.5,
        "mock_eye_height_mv": 145, "mock_eye_width_ui": 0.62,
        "mock_ber": 1e-14, "mock_locked": True,
    },
    "gpio": {
        "pins": [
            {"name": "EN_VCORE",   "mock_level": True},
            {"name": "PGOOD_VCORE","mock_level": True},
            {"name": "FAULT_IN",   "mock_level": False},
            {"name": "RT_ENABLE",  "mock_level": False},
        ]
    },
}


# ── Standalone Entry ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    async def main():
        agg     = TelemetryAggregator()
        results = await agg.poll_and_evaluate()

        print(f"\n{'='*60}")
        print("  TELEMETRY INTERFACE AXIOM RESULTS")
        print(f"{'='*60}")
        for r in results["axiom_results"]:
            status = "✓ PASS" if r["passed"] else "✗ FAIL"
            print(f"  {status}  {r['axiom_id']}  violations={len(r['violations'])}")
        print(f"{'='*60}")
        print(f"  Overall: {'PASS' if results['overall_pass'] else 'FAIL'}\n")

        with open("test-harness/results_telemetry.json", "w") as f:
            json.dump(results, f, indent=2, default=str)
        print("Results → test-harness/results_telemetry.json")

        return 0 if results["overall_pass"] else 1

    sys.exit(asyncio.run(main()))
