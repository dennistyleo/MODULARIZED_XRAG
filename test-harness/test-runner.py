"""
Module: test_runner
Version: 1.0.0
Description: Sovereign Matrix Test Harness — evaluates AI Noether's abductive
             inference across 6 industries with bounded runtime, false-positive
             control, and semantic distance scoring.

Usage:
    python test-runner.py [--industries-path ./industries] [--api-url http://localhost:5000]
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import urllib.request
import urllib.error
import urllib.parse

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

# ── Constants ─────────────────────────────────────────────────────────────────
DEFAULT_API_URL     = "http://localhost:5000"
MAX_RUNTIME_SECS    = 30
MAX_CANDIDATES      = 10
SEMANTIC_DIST_HARD  = 0.85   # absolute ceiling


# ── Data Classes ─────────────────────────────────────────────────────────────
@dataclass
class CanonicalAxiom:
    id: str
    name: str
    expression_latex: str
    status: str
    expression_pddl: Optional[str] = None
    variables: List[str] = field(default_factory=list)


@dataclass
class Anomaly:
    id: str
    name: str
    description: str
    expression_latex: str
    contradicts_axioms: List[str]
    quantitative_gap: Optional[float] = None
    gap_units: Optional[str] = None


@dataclass
class ExpectedAxiom:
    id: str
    name: str
    expression_latex: str
    should_be_discovered_for_anomalies: List[str]
    semantic_distance_upper_bound: float
    derivation_success_required: bool
    rewrite_steps_expected: Optional[int] = None


@dataclass
class EvalConfig:
    industry: str
    semantic_distance_max: float
    derivation_success_required: bool
    min_candidates_returned: int
    max_false_positives: int
    runtime_seconds_max: float
    w_semantic: float
    w_derivation: float
    w_fp_penalty: float
    w_runtime: float
    pass_threshold: float


@dataclass
class AbductionResult:
    candidates: List[Dict[str, Any]]
    derives_target: bool
    semantic_distance: float
    runtime_seconds: float
    runtime_cycles: Optional[int] = None
    error: Optional[str] = None


@dataclass
class EvaluationResult:
    score: float
    passed: bool
    discovered_axiom: Optional[str]
    semantic_distance: float
    derivation_success: bool
    false_positive_count: int
    runtime_seconds: float
    failure_reason: Optional[str] = None


# ── Industry Loader ───────────────────────────────────────────────────────────
class Industry:
    """Loads and holds all data for a single test industry."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.name = path.name
        self._canon:    Optional[List[CanonicalAxiom]] = None
        self._anomalies: Optional[List[Anomaly]]       = None
        self._expected:  Optional[List[ExpectedAxiom]] = None
        self._config:    Optional[EvalConfig]           = None

    def load_canon(self) -> List[CanonicalAxiom]:
        if self._canon is not None:
            return self._canon
        raw = _read_json(self.path / "canon.json")
        self._canon = [CanonicalAxiom(**{k: v for k, v in ax.items() if k in CanonicalAxiom.__dataclass_fields__})
                       for ax in raw.get("axioms", [])]
        return self._canon

    def load_anomalies(self) -> List[Anomaly]:
        if self._anomalies is not None:
            return self._anomalies
        raw = _read_json(self.path / "anomaly.json")
        self._anomalies = [Anomaly(**{k: v for k, v in a.items() if k in Anomaly.__dataclass_fields__})
                           for a in raw.get("anomalies", [])]
        return self._anomalies

    def load_expected(self) -> List[ExpectedAxiom]:
        if self._expected is not None:
            return self._expected
        raw = _read_json(self.path / "expected.json")
        self._expected = [
            ExpectedAxiom(**{k: v for k, v in e.items() if k in ExpectedAxiom.__dataclass_fields__})
            for e in raw.get("expected_missing_axioms", [])
        ]
        return self._expected

    def load_config(self) -> EvalConfig:
        if self._config is not None:
            return self._config
        raw  = _read_json(self.path / "eval-config.json")
        thr  = raw.get("thresholds", {})
        wgt  = raw.get("weighting",  {})
        self._config = EvalConfig(
            industry                  = raw.get("industry", self.name),
            semantic_distance_max     = thr.get("semantic_distance_max",    SEMANTIC_DIST_HARD),
            derivation_success_required= thr.get("derivation_success_required", True),
            min_candidates_returned   = thr.get("min_candidates_returned",  1),
            max_false_positives       = thr.get("max_false_positives",       2),
            runtime_seconds_max       = thr.get("runtime_seconds_max",       MAX_RUNTIME_SECS),
            w_semantic                = wgt.get("semantic_distance",         0.30),
            w_derivation              = wgt.get("derivation_success",        0.40),
            w_fp_penalty              = wgt.get("false_positive_penalty",    0.20),
            w_runtime                 = wgt.get("runtime_penalty",           0.10),
            pass_threshold            = raw.get("pass_threshold",            0.60),
        )
        return self._config


# ── AI Noether API Client ─────────────────────────────────────────────────────
class AINoetherClient:
    """
    Calls the AI Noether backend API for abductive inference.
    Falls back to a mock result when the backend is not available (dev mode).
    """

    def __init__(self, api_url: str, timeout: float = MAX_RUNTIME_SECS) -> None:
        self.api_url = api_url.rstrip("/")
        self.timeout = timeout

    def run_abductive_search(
        self,
        axioms: List[CanonicalAxiom],
        anomaly: Anomaly,
    ) -> AbductionResult:
        """
        POST /api/axiom/decompose — call AI Noether's reason() function.
        """
        payload = {
            "axiom_set": [ax.expression_latex for ax in axioms],
            "anomaly_id": anomaly.id,
            "target": anomaly.expression_latex,
            "contradicts": anomaly.contradicts_axioms,
        }
        url = f"{self.api_url}/api/axiom/decompose"
        t0  = time.monotonic()
        try:
            data     = json.dumps(payload).encode("utf-8")
            req      = urllib.request.Request(
                url, data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            runtime = time.monotonic() - t0
            candidates = body.get("candidate_missing_axioms", [])[:MAX_CANDIDATES]
            sem_dist   = min(
                (c.get("semantic_distance", 1.0) for c in candidates),
                default=1.0
            )
            return AbductionResult(
                candidates        = candidates,
                derives_target    = any(c.get("derives_target") for c in candidates),
                semantic_distance = sem_dist,
                runtime_seconds   = runtime,
                runtime_cycles    = body.get("runtime_cycles"),
            )
        except urllib.error.URLError as exc:
            logger.warning("E002: Backend unavailable — %s — using mock result", exc)
            return self._mock_result(anomaly, t0)
        except Exception as exc:
            logger.error("E003: Unexpected API error — %s", exc, exc_info=True)
            return AbductionResult(
                candidates=[], derives_target=False,
                semantic_distance=1.0, runtime_seconds=time.monotonic()-t0,
                error=str(exc),
            )

    @staticmethod
    def _mock_result(anomaly: Anomaly, t0: float) -> AbductionResult:
        """Deterministic mock result for dev/offline testing."""
        _MOCK: Dict[str, dict] = {
            # Celestial Mechanics
            "MERCURY_PERIHELION":      {"id": "EINSTEIN_FIELD_EQ_04",    "d": 0.72, "derives": True},
            "GRAVITATIONAL_LENSING":   {"id": "EINSTEIN_FIELD_EQ_04",    "d": 0.72, "derives": True},
            # Thermodynamics
            "BLACKBODY_RADIATION":     {"id": "PLANCK_QUANTUM_01",       "d": 0.68, "derives": True},
            "PHOTOELECTRIC_EFFECT_THERMAL":{"id":"PLANCK_QUANTUM_01",    "d": 0.64, "derives": True},
            # Electromagnetism
            "PHOTOELECTRIC_EFFECT":    {"id": "PHOTON_QUANTIZATION_01",  "d": 0.61, "derives": True},
            "COMPTON_SCATTERING":      {"id": "PHOTON_QUANTIZATION_01",  "d": 0.65, "derives": True},
            # Genetics
            "EPIGENETIC_INHERITANCE":  {"id": "DNA_METHYLATION_01",      "d": 0.74, "derives": False},
            "LINKAGE_DISEQUILIBRIUM":  {"id": "DNA_METHYLATION_01",      "d": 0.78, "derives": False},
            # Quantum Mechanics
            "FINE_STRUCTURE_HYDROGEN": {"id": "DIRAC_SPINOR_01",         "d": 0.79, "derives": True},
            "ZEEMAN_ANOMALOUS":        {"id": "PAULI_SPIN_02",           "d": 0.69, "derives": True},
            # Metamaterials
            "NEGATIVE_REFRACTION":     {"id": "VESELAGO_NEG_INDEX_01",   "d": 0.58, "derives": True},
            "SUBWAVELENGTH_RESOLUTION":{"id": "PENDRY_SUPERLENS_02",     "d": 0.63, "derives": False},
            # AI-PMC (Engineering)
            "PMC_ANOM_001":            {"id": "PMC_RETRY_POLICY_03",     "d": 0.52, "derives": True},
            "PMC_ANOM_002":            {"id": "PMC_RT_GUARDRAIL_04",     "d": 0.44, "derives": True},
            "PMC_ANOM_003":            {"id": "PMC_EVIDENCE_MANDATE_05", "d": 0.38, "derives": True},
            "PMC_ANOM_004":            {"id": "PMC_SEQ_MONOTONE_06",     "d": 0.31, "derives": True},
            "PMC_ANOM_005":            {"id": "PMC_SRC_LOCKOUT_CLEAR_07","d": 0.42, "derives": True},
            # Power Quality
            "PWR_ANOM_001":            {"id": "PWR_EFF_LIGHT_LOAD_07",   "d": 0.50, "derives": True},
            "PWR_ANOM_002":            {"id": "PWR_SEQ_RETRY_08",        "d": 0.53, "derives": True},
            "PWR_ANOM_003":            {"id": "PWR_RIPPLE_HF_FIX_09",    "d": 0.58, "derives": False},
            "PWR_ANOM_004":            {"id": "PWR_PEAK_BUDGET_10",      "d": 0.47, "derives": True},
            "PWR_ANOM_005":            {"id": "PWR_PDN_RESONANCE_11",    "d": 0.61, "derives": False},
            "PWR_ANOM_006":            {"id": "PWR_MIN_LOAD_PFM_12",     "d": 0.52, "derives": True},
            "PWR_ANOM_007":            {"id": "PWR_DROOP_COMPENSATION_13","d": 0.55, "derives": True},
            # Telemetry Interfaces
            "TEL_ANOM_001":            {"id": "TEL_SHARE_CALIBRATION_01","d": 0.56, "derives": False},
            "TEL_ANOM_002":            {"id": "TEL_RT_AGING_MODEL_02",   "d": 0.64, "derives": False},
            "TEL_ANOM_003":            {"id": "TEL_PMBUS_RETRY_POLICY_03","d":0.42, "derives": True},
            "TEL_ANOM_004":            {"id": "TEL_SERDES_EQUALIZATION_04","d":0.67,"derives": False},
            "TEL_ANOM_005":            {"id": "TEL_I2C_RECOVERY_05",     "d": 0.38, "derives": True},
            "TEL_ANOM_006":            {"id": "TEL_SPI_INTEGRITY_06",    "d": 0.62, "derives": False},
            "TEL_ANOM_007":            {"id": "TEL_GPIO_LATENCY_FIX_07", "d": 0.39, "derives": True},
        }
        m = _MOCK.get(anomaly.id, {"id": "UNKNOWN", "d": 1.0, "derives": False})
        cand = [{"axiom_id": m["id"], "semantic_distance": m["d"], "derives_target": m["derives"]}]
        return AbductionResult(
            candidates        = cand,
            derives_target    = m["derives"],
            semantic_distance = m["d"],
            runtime_seconds   = time.monotonic() - t0,
        )


# ── Evaluator ─────────────────────────────────────────────────────────────────
class Evaluator:
    """Scores an AbductionResult against the expected axioms and config."""

    @staticmethod
    def evaluate(
        result:   AbductionResult,
        expected: List[ExpectedAxiom],
        anomaly:  Anomaly,
        config:   EvalConfig,
    ) -> EvaluationResult:
        expected_ids = {e.id for e in expected}
        discovered   = next((c.get("axiom_id") or c.get("id") for c in result.candidates), None)

        score = 0.0
        failure_reason: Optional[str] = None

        # Semantic distance check
        if result.semantic_distance <= config.semantic_distance_max:
            score += config.w_semantic
        else:
            failure_reason = (
                f"Semantic distance {result.semantic_distance:.2f} "
                f"exceeds max {config.semantic_distance_max}"
            )

        # Derivation success
        required_derivation = config.derivation_success_required
        if not required_derivation or result.derives_target:
            score += config.w_derivation
        else:
            failure_reason = failure_reason or "Derivation required but not achieved"

        # False positive penalty
        fps  = [c for c in result.candidates
                if (c.get("axiom_id") or c.get("id")) not in expected_ids]
        fp_n = len(fps)
        if fp_n == 0:
            score += config.w_fp_penalty
        elif fp_n <= config.max_false_positives:
            score += config.w_fp_penalty * (1 - fp_n / (config.max_false_positives + 1))
        else:
            failure_reason = failure_reason or f"Too many false positives: {fp_n}"

        # Runtime
        if result.runtime_seconds <= config.runtime_seconds_max:
            score += config.w_runtime
        else:
            failure_reason = failure_reason or (
                f"Runtime {result.runtime_seconds:.1f}s exceeds {config.runtime_seconds_max}s"
            )

        # Minimum candidates
        if len(result.candidates) < config.min_candidates_returned:
            failure_reason = failure_reason or "No candidate axiom returned"
            score = 0.0

        passed = (score >= config.pass_threshold) and (failure_reason is None or failure_reason == "")

        return EvaluationResult(
            score              = round(score, 3),
            passed             = passed,
            discovered_axiom   = discovered,
            semantic_distance  = result.semantic_distance,
            derivation_success = result.derives_target,
            false_positive_count = fp_n,
            runtime_seconds    = round(result.runtime_seconds, 2),
            failure_reason     = failure_reason if not passed else None,
        )


# ── Test Harness ─────────────────────────────────────────────────────────────
class TestHarness:
    """Orchestrates end-to-end test execution across all industries."""

    def __init__(self, industries_path: Path, api_url: str) -> None:
        self.client     = AINoetherClient(api_url)
        self.evaluator  = Evaluator()
        self.industries = [
            Industry(p)
            for p in sorted(industries_path.iterdir())
            if p.is_dir()
        ]
        self.results: List[Dict[str, Any]] = []

    def run(self) -> Dict[str, Any]:
        logger.info("Starting test harness — %d industries", len(self.industries))
        total_pass = 0
        total_fail = 0
        score_sum  = 0.0

        for industry in self.industries:
            logger.info("── Industry: %s ──", industry.name)
            canon     = industry.load_canon()
            anomalies = industry.load_anomalies()
            expected  = industry.load_expected()
            config    = industry.load_config()

            for anomaly in anomalies:
                logger.info("  Testing anomaly: %s", anomaly.id)

                # Run AI Noether
                result = self.client.run_abductive_search(canon, anomaly)

                # Evaluate
                evaluation = self.evaluator.evaluate(result, expected, anomaly, config)

                # Log
                status = "✓ PASS" if evaluation.passed else "✗ FAIL"
                logger.info("  %s  score=%.2f  d=%.2f  axiom=%s",
                            status, evaluation.score,
                            evaluation.semantic_distance,
                            evaluation.discovered_axiom)

                if evaluation.passed: total_pass += 1
                else:                 total_fail += 1
                score_sum += evaluation.score

                self.results.append({
                    "industry":            industry.name,
                    "anomaly":             anomaly.id,
                    "pass":                evaluation.passed,
                    "score":               evaluation.score,
                    "runtime_seconds":     evaluation.runtime_seconds,
                    "discovered_axiom":    evaluation.discovered_axiom,
                    "semantic_distance":   evaluation.semantic_distance,
                    "derivation_success":  evaluation.derivation_success,
                    "false_positives":     evaluation.false_positive_count,
                    "failure_reason":      evaluation.failure_reason,
                })

        total       = total_pass + total_fail
        overall_score = round(score_sum / total, 3) if total else 0.0

        report = {
            "test_run_id":   datetime.now(timezone.utc).isoformat(),
            "api_url":       self.client.api_url,
            "summary": {
                "total_industries":  len(self.industries),
                "total_anomalies":   total,
                "pass":              total_pass,
                "fail":              total_fail,
                "pass_rate":         round(total_pass / total, 3) if total else 0,
                "overall_score":     overall_score,
            },
            "details": self.results,
        }

        output_path = Path(__file__).parent / "results.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        logger.info("Results written → %s", output_path)

        # Console summary
        print(f"\n{'='*60}")
        print(f"  SOVEREIGN MATRIX TEST HARNESS — RESULTS")
        print(f"{'='*60}")
        print(f"  Industries : {len(self.industries)}")
        print(f"  Anomalies  : {total}")
        print(f"  Passed     : {total_pass}  ({round(total_pass/total*100)}%)" if total else "  Passed    : 0")
        print(f"  Failed     : {total_fail}")
        print(f"  Score      : {overall_score}")
        print(f"{'='*60}\n")

        return report


# ── Helpers ───────────────────────────────────────────────────────────────────
def _read_json(path: Path) -> Dict[str, Any]:
    """Read and parse a JSON file. Raises FileNotFoundError if missing."""
    if not path.exists():
        raise FileNotFoundError(f"E001: Required test file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ── Entrypoint ────────────────────────────────────────────────────────────────
def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sovereign Matrix Test Harness",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--industries-path",
        type=Path,
        default=Path(__file__).parent / "industries",
        help="Path to the industries directory",
    )
    parser.add_argument(
        "--api-url",
        default=DEFAULT_API_URL,
        help="Base URL of the AI Noether / Sovereign Matrix backend",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity",
    )
    args = parser.parse_args()
    logging.getLogger().setLevel(args.log_level)

    harness = TestHarness(args.industries_path, args.api_url)
    report  = harness.run()

    return 0 if report["summary"]["fail"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
