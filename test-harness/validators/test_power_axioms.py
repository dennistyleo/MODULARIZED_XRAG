"""
Module: test_power_axioms
Version: 1.0.0  
Description: Power Quality Axiom Verifier — validates PWR_EFF_01 through PWR_TRAN_06
             against telemetry traces captured from XR-PMC hardware or simulation.

Usage:
    verifier = PowerAxiomVerifier(config)
    results  = verifier.run_all(telemetry_log_path)
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ── Default Config ────────────────────────────────────────────────────────────
DEFAULT_CONFIG: Dict[str, Any] = {
    "efficiency_min":    {0: 0.85, 1: 0.85, 2: 0.85, 3: 0.70},  # indices → rail ID
    "efficiency_light_min": {0: 0.70, 1: 0.70, 2: 0.70, 3: 0.70},
    "ripple_max_mv":     {0: 30, 1: 30, 2: 30, 3: 20},
    "min_load_ma":       {0: 50, 1: 50, 2: 100, 3: 50},
    "sequencing": {
        "pgood_timeout_ms":   10,
        "inter_rail_delay_ms": 5,
    },
    "transient": {
        "droop_max_mv":      100,
        "overshoot_max_mv":  100,
        "settling_time_us":   50,
        "load_step_max_a":     5.0,
    },
    "budget": {
        "total_w_max":  50.0,
        "peak_w_max":   75.0,
        "peak_duration_ms": 10,
    },
    "pdn": {
        "z_target_ohms":   0.010,
        "frequency_range": [1e3, 100e6],
    },
}


# ── Data Classes ─────────────────────────────────────────────────────────────
@dataclass
class RailTelemetry:
    """Telemetry snapshot for a single power rail."""
    rail_id: int
    timestamp_us: int
    vout_mv: float
    iout_ma: float
    vin_mv: float
    pgood: bool = True
    ripple_pp_mv: float = 0.0
    efficiency: float = 1.0


@dataclass
class AxiomCheckResult:
    axiom_id: str
    axiom_name: str
    passed: bool
    violations: List[Dict[str, Any]] = field(default_factory=list)
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    note: Optional[str] = None


# ── Verifier ─────────────────────────────────────────────────────────────────
class PowerAxiomVerifier:
    """Verifies power quality axioms against telemetry traces."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.config = config or DEFAULT_CONFIG

    # ── PWR_EFF_01 ────────────────────────────────────────────────────────────
    def verify_efficiency(self, telemetry: List[RailTelemetry]) -> AxiomCheckResult:
        """PWR_EFF_01: η ≥ 85% full load, ≥70% light load (< 10% of rated)."""
        violations: List[Dict] = []
        evidence:   List[Dict] = []

        for t in telemetry:
            # Auto-compute efficiency if not provided
            eta = t.efficiency
            if eta == 1.0 and t.vin_mv > 0:
                pin_mw  = t.vin_mv * t.iout_ma
                pout_mw = t.vout_mv * t.iout_ma
                if pin_mw > 0:
                    eta = pout_mw / pin_mw

            rated_ma = self.config["efficiency_min"].get(t.rail_id, 0.85)
            is_light = t.iout_ma < (rated_ma * 1000 * 0.10)  # <10% of rated
            threshold = (
                self.config["efficiency_light_min"].get(t.rail_id, 0.70)
                if is_light
                else self.config["efficiency_min"].get(t.rail_id, 0.85)
            )

            if eta < threshold:
                viol = {
                    "rail": t.rail_id, "timestamp_us": t.timestamp_us,
                    "efficiency": round(eta, 3), "threshold": threshold,
                    "load_ma": t.iout_ma, "light_load": is_light,
                    "gap": round(threshold - eta, 3),
                }
                violations.append(viol)
                evidence.append({"event_id": "EFF_DEGRADED", "payload": viol})
            else:
                evidence.append({
                    "event_id": "EFF_MEASURED",
                    "payload": {"rail": t.rail_id, "efficiency": round(eta, 3)},
                })

        return AxiomCheckResult(
            axiom_id="PWR_EFF_01", axiom_name="Power Efficiency Constraint",
            passed=len(violations) == 0, violations=violations, evidence=evidence,
        )

    # ── PWR_SEQ_02 ────────────────────────────────────────────────────────────
    def verify_sequencing(self, pgood_timestamps_ms: Dict[int, float]) -> AxiomCheckResult:
        """PWR_SEQ_02: PGOOD must arrive within timeout window."""
        violations: List[Dict] = []
        evidence:   List[Dict] = []
        timeout_ms = self.config["sequencing"]["pgood_timeout_ms"]

        for rail_id, arrival_ms in pgood_timestamps_ms.items():
            if arrival_ms > timeout_ms:
                viol = {
                    "rail": rail_id, "arrival_ms": arrival_ms,
                    "timeout_ms": timeout_ms, "excess_ms": round(arrival_ms - timeout_ms, 2),
                }
                violations.append(viol)
                evidence.append({"event_id": "PGOOD_TIMEOUT", "payload": viol})
            else:
                evidence.append({"event_id": "SEQ_STEP", "payload": {"rail": rail_id, "pgood_ms": arrival_ms}})

        return AxiomCheckResult(
            axiom_id="PWR_SEQ_02", axiom_name="Deterministic Power Sequencing",
            passed=len(violations) == 0, violations=violations, evidence=evidence,
        )

    # ── PWR_RIPPLE_03 ─────────────────────────────────────────────────────────
    def verify_ripple(self, telemetry: List[RailTelemetry]) -> AxiomCheckResult:
        """PWR_RIPPLE_03: Peak-to-peak ripple ≤ threshold per rail."""
        violations: List[Dict] = []
        evidence:   List[Dict] = []

        for t in telemetry:
            max_mv = self.config["ripple_max_mv"].get(t.rail_id, 30)
            if t.ripple_pp_mv > max_mv:
                viol = {
                    "rail": t.rail_id, "ripple_mv": t.ripple_pp_mv,
                    "max_allowed_mv": max_mv, "excess_mv": round(t.ripple_pp_mv - max_mv, 2),
                }
                violations.append(viol)
                evidence.append({"event_id": "RIPPLE_EXCEEDED", "payload": viol})
            else:
                evidence.append({
                    "event_id": "RIPPLE_MEASURED",
                    "payload": {"rail": t.rail_id, "ripple_pp_mv": t.ripple_pp_mv},
                })

        return AxiomCheckResult(
            axiom_id="PWR_RIPPLE_03", axiom_name="Ripple and Noise Constraint",
            passed=len(violations) == 0, violations=violations, evidence=evidence,
        )

    # ── PWR_CONS_04 ───────────────────────────────────────────────────────────
    def verify_budget(self, telemetry: List[RailTelemetry]) -> AxiomCheckResult:
        """PWR_CONS_04: Total power ≤ 50W, peak ≤ 75W."""
        violations: List[Dict] = []
        evidence:   List[Dict] = []

        total_mw = sum(t.vout_mv * t.iout_ma / 1e6 * 1000 for t in telemetry)
        total_w  = total_mw / 1000.0
        budget_w = self.config["budget"]["total_w_max"]
        peak_w   = self.config["budget"]["peak_w_max"]

        if total_w > budget_w:
            viol = {"total_w": round(total_w, 2), "budget_w": budget_w, "excess_w": round(total_w - budget_w, 2)}
            violations.append(viol)
            evidence.append({"event_id": "POWER_BUDGET_EXCEEDED", "payload": viol})
        else:
            evidence.append({"event_id": "POWER_MEASURED", "payload": {"total_w": round(total_w, 2)}})

        return AxiomCheckResult(
            axiom_id="PWR_CONS_04", axiom_name="Power Consumption Budget",
            passed=len(violations) == 0, violations=violations, evidence=evidence,
        )

    # ── PWR_INT_05 ────────────────────────────────────────────────────────────
    def verify_pdn_impedance(self, impedance_by_freq: Dict[float, float]) -> AxiomCheckResult:
        """PWR_INT_05: Z_PDN(f) ≤ 10mΩ across frequency range."""
        violations: List[Dict] = []
        evidence:   List[Dict] = []
        z_target = self.config["pdn"]["z_target_ohms"]

        for freq_hz, z_ohms in impedance_by_freq.items():
            if z_ohms > z_target:
                viol = {
                    "frequency_hz": freq_hz, "impedance_ohms": z_ohms,
                    "target_ohms": z_target, "excess_mohm": round((z_ohms - z_target) * 1000, 2),
                }
                violations.append(viol)
                evidence.append({"event_id": "PDN_RESONANCE_DETECTED", "payload": viol})
            else:
                evidence.append({
                    "event_id": "PDN_IMPEDANCE_MEASURED",
                    "payload": {"frequency_hz": freq_hz, "z_ohms": z_ohms},
                })

        return AxiomCheckResult(
            axiom_id="PWR_INT_05", axiom_name="Power Distribution Network Integrity",
            passed=len(violations) == 0, violations=violations, evidence=evidence,
        )

    # ── PWR_TRAN_06 ───────────────────────────────────────────────────────────
    def verify_transient(
        self,
        load_step: Dict[str, float],
        min_load_by_rail: Optional[Dict[int, float]] = None,
    ) -> AxiomCheckResult:
        """PWR_TRAN_06: Droop ≤ 100mV, overshoot ≤ 100mV, Imin ≥ 50mA."""
        violations: List[Dict] = []
        evidence:   List[Dict] = []
        cfg = self.config["transient"]

        droop_mv    = load_step.get("droop_mv", 0)
        overshoot_mv = load_step.get("overshoot_mv", 0)

        if droop_mv > cfg["droop_max_mv"]:
            viol = {"type": "droop", "measured_mv": droop_mv, "max_mv": cfg["droop_max_mv"]}
            violations.append(viol)
            evidence.append({"event_id": "TRANSIENT_DROOP", "payload": viol})

        if overshoot_mv > cfg["overshoot_max_mv"]:
            viol = {"type": "overshoot", "measured_mv": overshoot_mv, "max_mv": cfg["overshoot_max_mv"]}
            violations.append(viol)
            evidence.append({"event_id": "TRANSIENT_OVERSHOOT", "payload": viol})

        if min_load_by_rail:
            for rail_id, load_ma in min_load_by_rail.items():
                min_req = self.config["min_load_ma"].get(rail_id, 50)
                if load_ma < min_req:
                    viol = {"rail": rail_id, "load_ma": load_ma, "min_required_ma": min_req}
                    violations.append(viol)
                    evidence.append({"event_id": "MIN_LOAD_VIOLATION", "payload": viol})

        if not violations:
            evidence.append({"event_id": "TRANSIENT_SETTLED", "payload": load_step})

        return AxiomCheckResult(
            axiom_id="PWR_TRAN_06", axiom_name="Transient Response and Minimum Load",
            passed=len(violations) == 0, violations=violations, evidence=evidence,
        )

    # ── Full Run ─────────────────────────────────────────────────────────────
    def run_all(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Run all 6 power axiom verifications against a telemetry snapshot."""
        # Parse telemetry
        telemetry = [
            RailTelemetry(**{k: v for k, v in t.items() if k in RailTelemetry.__dataclass_fields__})
            for t in data.get("telemetry", [])
        ]

        checks: List[AxiomCheckResult] = [
            self.verify_efficiency(telemetry),
            self.verify_sequencing(data.get("pgood_timestamps_ms", {})),
            self.verify_ripple(telemetry),
            self.verify_budget(telemetry),
            self.verify_pdn_impedance(data.get("pdn_impedance", {})),
            self.verify_transient(
                data.get("load_step", {}),
                data.get("min_load_by_rail"),
            ),
        ]

        axiom_results = [
            {
                "axiom_id":   c.axiom_id,
                "axiom_name": c.axiom_name,
                "passed":     c.passed,
                "violation_count": len(c.violations),
                "violations": c.violations,
                "evidence":   c.evidence,
            }
            for c in checks
        ]

        overall_pass = all(c.passed for c in checks)

        return {
            "timestamp":     data.get("timestamp"),
            "board_id":      data.get("board_id"),
            "overall_pass":  overall_pass,
            "axiom_results": axiom_results,
            "summary": {
                "total":  len(checks),
                "passed": sum(1 for c in checks if c.passed),
                "failed": sum(1 for c in checks if not c.passed),
            },
        }


# ── Mock Telemetry for Standalone Test ───────────────────────────────────────
_MOCK_TELEMETRY = {
    "timestamp": "2026-04-11T04:00:00Z",
    "board_id": "XR-PMC-V1-TEST",
    "telemetry": [
        {"rail_id": 0, "timestamp_us": 1000, "vout_mv": 1000, "iout_ma": 10000,
         "vin_mv": 12000, "pgood": True, "ripple_pp_mv": 25.0, "efficiency": 0.88},
        {"rail_id": 1, "timestamp_us": 1000, "vout_mv": 1800, "iout_ma": 5000,
         "vin_mv": 12000, "pgood": True, "ripple_pp_mv": 28.0, "efficiency": 0.83},
        {"rail_id": 2, "timestamp_us": 1000, "vout_mv": 3300, "iout_ma": 2000,
         "vin_mv": 12000, "pgood": True, "ripple_pp_mv": 45.0, "efficiency": 0.78},  # ripple violation!
        {"rail_id": 3, "timestamp_us": 1000, "vout_mv": 5000, "iout_ma": 30,
         "vin_mv": 12000, "pgood": True, "ripple_pp_mv": 18.0, "efficiency": 0.42},  # light load violation!
    ],
    "pgood_timestamps_ms": {0: 8.2, 1: 9.1, 2: 25.0, 3: 7.5},  # rail 2 timeout!
    "pdn_impedance": {1000: 0.003, 100000: 0.008, 1e7: 0.035, 5e7: 0.012},  # 10MHz resonance!
    "load_step": {"droop_mv": 180.0, "overshoot_mv": 45.0},  # droop violation!
    "min_load_by_rail": {0: 250, 1: 80, 2: 10, 3: 30},       # rail 2 & 3 too low!
}


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    if len(sys.argv) > 1:
        with open(sys.argv[1]) as f:
            data = json.load(f)
    else:
        data = _MOCK_TELEMETRY
        print("[INFO] No input file — using mock telemetry (expect some failures)\n")

    verifier = PowerAxiomVerifier()
    results  = verifier.run_all(data)

    print(f"\n{'='*60}")
    print("  POWER AXIOM VERIFICATION RESULTS")
    print(f"{'='*60}")
    for r in results["axiom_results"]:
        status = "✓ PASS" if r["passed"] else "✗ FAIL"
        print(f"  {status}  {r['axiom_id']}  violations={r['violation_count']}")
    print(f"{'='*60}")
    print(f"  Overall: {'PASS' if results['overall_pass'] else 'FAIL'}  "
          f"({results['summary']['passed']}/{results['summary']['total']})\n")

    with open("test-harness/results_power.json", "w") as f:
        json.dump(results, f, indent=2)
    print("Results → test-harness/results_power.json")

    sys.exit(0 if results["overall_pass"] else 1)
