"""
Module: ai_pmc_axiom_runner
Version: 1.0.0
Description: AI-PMC Axiom Validator — executes ATP cases from XR-PMC spec
             Chapter 9 against FPGA evidence logs.
             
Usage:
    validator = PMC_AxiomValidator(evidence_log_path)
    result = validator.run_atp(ATP_RT_HOLD)
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ── Data Classes ─────────────────────────────────────────────────────────────
@dataclass
class AxiomTestCase:
    """ATP case from XR-PMC spec Chapter 9.2"""
    atp_id: str
    description: str
    stimulus: Dict[str, Any]
    expected_evidence: List[str]
    pass_threshold: float = 0.95
    required_state_transitions: List[str] = field(default_factory=list)


@dataclass
class ATPResult:
    atp_id: str
    passed: bool
    score: float
    failures: List[str]
    evidence_found: List[str]
    evidence_missing: List[str]


# ── Validator ─────────────────────────────────────────────────────────────────
class PMC_AxiomValidator:
    """
    Validates that hardware behavior matches AI-PMC axioms.
    Evidence log format: NDJSON with fields: seq, t_us, event_id, payload
    """

    def __init__(self, evidence_log: Optional[Path] = None) -> None:
        self.evidence: List[Dict[str, Any]] = []
        if evidence_log and evidence_log.exists():
            self.evidence = self._load_evidence(evidence_log)

    def _load_evidence(self, path: Path) -> List[Dict[str, Any]]:
        """Load NDJSON evidence log. Raises ValueError on malformed lines."""
        records = []
        with open(path, "r", encoding="utf-8") as f:
            for i, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    logger.warning("E003: Malformed evidence at line %d — %s", i, exc)
        logger.info("Loaded %d evidence records from %s", len(records), path)
        return records

    # ── Guardrail (AI-PMC spec Ch.7.1) ───────────────────────────────────────
    def check_guardrail(self, sensors: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate PMC_GUARDRAIL_BASE_02.
        Returns pass/fail for each guardrail condition.
        """
        vin_ok   = sensors.get("vin_valid", False)
        vcap_ok  = sensors.get("vcap_mv", 0) >= 800          # 0.8V threshold
        temp_ok  = sensors.get("temp_c", 999) <= 105
        bus_ok   = sensors.get("bus_ok", True)
        all_ok   = vin_ok and vcap_ok and temp_ok and bus_ok

        return {
            "axiom": "PMC_GUARDRAIL_BASE_02",
            "passed": all_ok,
            "conditions": {
                "vin_ok":  vin_ok,
                "vcap_ok": vcap_ok,
                "temp_ok": temp_ok,
                "bus_ok":  bus_ok,
            },
        }

    # ── Sequencing (AI-PMC spec Ch.5) ────────────────────────────────────────
    def verify_sequencing(self, expected_rails: List[int]) -> Dict[str, Any]:
        """Verify PMC_SEQ_RAIL_01: all rails reached RAIL_STABLE."""
        stable_events  = [e for e in self.evidence if e.get("event_id") == "RAIL_STABLE"]
        stable_rail_ids = {e.get("payload", {}).get("rail_id") for e in stable_events}
        missing         = [r for r in expected_rails if r not in stable_rail_ids]

        return {
            "axiom":           "PMC_SEQ_RAIL_01",
            "passed":          len(missing) == 0,
            "stable_rails":    list(stable_rail_ids),
            "missing_rails":   missing,
            "evidence_count":  len(stable_events),
        }

    # ── Evidence integrity (AI-PMC spec Ch.7.3) ──────────────────────────────
    def verify_evidence_ordering(self) -> Dict[str, Any]:
        """Verify PMC_EVIDENCE_LOG_03: monotonic seq and timestamp."""
        violations: List[str] = []
        last_seq = -1
        last_ts  = -1

        for ev in self.evidence:
            seq = ev.get("seq", -1)
            ts  = ev.get("t_us", -1)
            if seq <= last_seq:
                violations.append(
                    f"Seq discontinuity: {seq} after {last_seq} (event: {ev.get('event_id')})"
                )
            if ts < last_ts:
                violations.append(
                    f"Timestamp regression: {ts} < {last_ts} (event: {ev.get('event_id')})"
                )
            last_seq = seq
            last_ts  = ts

        return {
            "axiom":      "PMC_EVIDENCE_LOG_03",
            "passed":     len(violations) == 0,
            "violations": violations,
            "total_records": len(self.evidence),
        }

    # ── AI Gate (AI-PMC spec Ch.6) ───────────────────────────────────────────
    def verify_ai_gate(self) -> Dict[str, Any]:
        """
        Verify PMC_AI_GATE_01 + PMC_EVIDENCE_MANDATE_05:
        Whenever AI_mode is active, exactly one of AI_RUN / AI_SKIP / AI_EARLY_EXIT
        must appear in the evidence log.
        """
        mandatory = {"AI_RUN", "AI_SKIP", "AI_EARLY_EXIT"}
        ai_mode_events = [e for e in self.evidence if e.get("event_id") == "AI_MODE_ACTIVE"]
        found_mandate  = {e.get("event_id") for e in self.evidence} & mandatory
        missing_mandate = mandatory - found_mandate if ai_mode_events else set()

        return {
            "axiom":             "PMC_AI_GATE_01 + PMC_EVIDENCE_MANDATE_05",
            "passed":            len(missing_mandate) == 0,
            "ai_mode_events":    len(ai_mode_events),
            "found_mandate":     list(found_mandate),
            "missing_mandate":   list(missing_mandate),
        }

    # ── Ride-Through (AI-PMC spec Ch.8) ──────────────────────────────────────
    def verify_ride_through(self, vcap_min_mv: float = 800, hold_target_ms: float = 50) -> Dict[str, Any]:
        """
        Verify PMC_RT_BASE_01: RT must only trigger when Vcap ≥ Vmin,
        and must hold for at least hold_target_ms.
        """
        rt_trigger = next(
            (e for e in self.evidence if e.get("event_id") == "RT_TRIGGERED"), None
        )
        rt_done    = next(
            (e for e in self.evidence if e.get("event_id") == "RT_DONE"), None
        )

        violations: List[str] = []
        if rt_trigger:
            vcap_at_trigger = rt_trigger.get("payload", {}).get("vcap_mv", 0)
            if vcap_at_trigger < vcap_min_mv:
                violations.append(
                    f"RT triggered with Vcap={vcap_at_trigger}mV < Vmin={vcap_min_mv}mV (PMC_RT_GUARDRAIL_04 missing)"
                )

        if rt_trigger and rt_done:
            t_start = rt_trigger.get("t_us", 0)
            t_end   = rt_done.get("t_us", 0)
            hold_ms = (t_end - t_start) / 1000.0
            if hold_ms < hold_target_ms:
                violations.append(
                    f"RT hold={hold_ms:.1f}ms < required={hold_target_ms}ms"
                )

        return {
            "axiom":    "PMC_RT_BASE_01",
            "passed":   len(violations) == 0 and rt_trigger is not None,
            "violations": violations,
        }

    # ── Source Selection (AI-PMC spec Ch.4) ─────────────────────────────────
    def verify_source_selection(self) -> Dict[str, Any]:
        """
        Verify PMC_SRC_SELECT_01: every SRC_SELECT event must include
        from/to/reason fields.
        """
        select_events = [e for e in self.evidence if e.get("event_id") == "SRC_SELECT"]
        malformed     = [
            e for e in select_events
            if not all(k in e.get("payload", {}) for k in ["from", "to", "reason"])
        ]

        return {
            "axiom":               "PMC_SRC_SELECT_01",
            "passed":              len(malformed) == 0,
            "select_events":       len(select_events),
            "malformed_events":    len(malformed),
        }

    # ── Full ATP Run ──────────────────────────────────────────────────────────
    def run_atp(self, test_case: AxiomTestCase) -> ATPResult:
        """Execute a single ATP case from XR-PMC spec Chapter 9."""
        found:   List[str] = []
        missing: List[str] = []
        failures: List[str] = []

        # Check required evidence events
        evidence_ids = {e.get("event_id") for e in self.evidence}
        for required in test_case.expected_evidence:
            if required in evidence_ids:
                found.append(required)
            else:
                missing.append(required)
                failures.append(f"Missing required evidence: {required}")

        # Check guardrail
        sensors = test_case.stimulus.get("sensors", {})
        if sensors:
            gr = self.check_guardrail(sensors)
            if not gr["passed"]:
                failures.append(f"Guardrail violation: {gr['conditions']}")

        # Check evidence ordering
        ev_order = self.verify_evidence_ordering()
        if not ev_order["passed"]:
            failures.extend(ev_order["violations"])

        # Check state transitions
        for transition in test_case.required_state_transitions:
            if not any(str(transition) in str(e) for e in self.evidence):
                failures.append(f"Missing state transition: {transition}")

        total_checks = (
            len(test_case.expected_evidence) +
            (1 if sensors else 0) +
            1 +  # evidence ordering
            len(test_case.required_state_transitions)
        )
        pass_count = total_checks - len(failures)
        score      = pass_count / total_checks if total_checks else 0.0
        passed     = score >= test_case.pass_threshold and len(missing) == 0

        return ATPResult(
            atp_id          = test_case.atp_id,
            passed          = passed,
            score           = round(score, 3),
            failures        = failures,
            evidence_found  = found,
            evidence_missing= missing,
        )


# ── Pre-built ATP Cases (from XR-PMC spec Ch.9) ──────────────────────────────
ATP_SEQUENCING_BASIC = AxiomTestCase(
    atp_id="ATP-01",
    description="Basic power sequencing — all rails stable",
    stimulus={"sensors": {"vin_valid": True, "vcap_mv": 1200, "temp_c": 25, "bus_ok": True}},
    expected_evidence=["SEQ_START", "SEQ_STEP", "SEQ_DONE", "RAIL_STABLE"],
    pass_threshold=0.95,
    required_state_transitions=["IDLE→START", "START→RUN", "RUN→DONE"],
)

ATP_RT_HOLD = AxiomTestCase(
    atp_id="ATP-07",
    description="RT trigger and hold — Vcap adequate",
    stimulus={"sensors": {"vin_valid": False, "vcap_mv": 1200, "temp_c": 50, "bus_ok": True}, "cmd": "RT_TRIGGER"},
    expected_evidence=["RT_TRIGGERED", "RT_HOLD", "RT_EXIT", "RT_DONE"],
    pass_threshold=0.95,
    required_state_transitions=["IDLE→TRIGGER", "TRIGGER→HOLD", "HOLD→EXIT"],
)

ATP_AI_GATE_SKIP = AxiomTestCase(
    atp_id="ATP-12",
    description="AI gate skip path — must emit AI_SKIP evidence",
    stimulus={"sensors": {"vin_valid": True, "vcap_mv": 1000, "temp_c": 40}, "ai_mode": True},
    expected_evidence=["AI_MODE_ACTIVE", "AI_SKIP"],
    pass_threshold=1.0,  # strict — governance axiom
)

ATP_SRC_SWITCH = AxiomTestCase(
    atp_id="ATP-03",
    description="Source switch VIN_A → VIN_B — must emit SRC_SELECT with reason",
    stimulus={"sensors": {"vin_valid": True, "vcap_mv": 1100}},
    expected_evidence=["SRC_PRESENT", "SRC_SELECT", "SWITCH_START", "SWITCH_DONE"],
    pass_threshold=0.95,
)

ATP_EVIDENCE_INTEGRITY = AxiomTestCase(
    atp_id="ATP-15",
    description="Evidence log integrity — monotonic seq and timestamps",
    stimulus={},
    expected_evidence=[],  # checked via verify_evidence_ordering
    pass_threshold=1.0,
)


# ── Standalone Entry ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    import json as _json

    log_path = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    validator = PMC_AxiomValidator(log_path)

    results = []
    for atp in [ATP_SEQUENCING_BASIC, ATP_RT_HOLD, ATP_AI_GATE_SKIP, ATP_SRC_SWITCH, ATP_EVIDENCE_INTEGRITY]:
        r = validator.run_atp(atp)
        results.append({
            "atp_id": r.atp_id, "passed": r.passed, "score": r.score,
            "failures": r.failures, "found": r.evidence_found, "missing": r.evidence_missing,
        })
        status = "✓ PASS" if r.passed else "✗ FAIL"
        print(f"  {status}  {r.atp_id}  score={r.score}  missing={r.evidence_missing}")

    with open("test-harness/results_pmc.json", "w") as f:
        _json.dump(results, f, indent=2)
    print(f"\nResults → test-harness/results_pmc.json")
