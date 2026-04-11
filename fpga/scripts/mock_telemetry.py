#!/usr/bin/env python3
"""
Mock Telemetry Generator for AI-PMC FPGA Walkthrough
Version: 1.1.0
Description: Generates test vectors for ATP scenarios.
             ATP-01 and ATP-02 are formally defined in spec/25_aipmc_rtl_spec.md §5.5.
             ATP-03 through ATP-12 are extended engineering validation scenarios
             aligned with XR-PMC protection concepts (not formally specified in RTL spec).

Usage:
    python mock_telemetry.py                 # Print summary
    python mock_telemetry.py --export all    # Export all scenarios to JSON
    python mock_telemetry.py --export ATP-01 # Export single scenario
"""

import json
import random
import argparse
import sys
from dataclasses import dataclass
from typing import Dict, List
from enum import Enum


class Severity(Enum):
    INFO  = 0
    WARN  = 1
    FAULT = 2


@dataclass
class TelemetrySample:
    """One telemetry sample frame — matches FeatureExtractor 64-byte vector layout."""
    timestamp_ns:   int
    vin_valid:      bool
    bus_ok:         bool
    vcap_mv:        int            # 12-bit ADC value in mV
    temp_c:         int            # adc_temp_hotspot × 0.1 °C resolution
    fault_flags:    int            # 32-bit fault register
    pgood:          List[bool]     # pgood_in[7:0] (6 rails used here)
    iout_ma:        List[int]      # Per-rail current (mA)
    vout_mv:        List[int]      # Per-rail voltage (mV)
    efficiency:     List[float]    # Per-rail efficiency [0.0–1.0]
    ripple_mv:      List[float]    # Per-rail ripple mVpp
    droop_mv:       int            # Load droop (mV)
    overshoot_mv:   int            # Overshoot (mV)
    settling_us:    int            # Settling time (µs)

    def to_axi_feature_words(self) -> Dict[str, int]:
        """Convert to 16 × 32-bit words matching FeatureExtractor register layout §4.8."""
        words = {}
        # Words 0x7000–0x700F: VOUT[0–7] — Q4.8 (zero-padded from 12-bit ADC)
        for i, v in enumerate(self.vout_mv[:8]):
            words[f"0x{0x7000 + i*4:04X}"] = (v & 0xFFF) << 4
        # Words 0x7010–0x701F: IOUT[0–7]
        for i, v in enumerate(self.iout_ma[:8]):
            words[f"0x{0x7010 + i*4:04X}"] = (v & 0xFFF) << 4
        # 0x7020: adc_temp packed
        words["0x7020"] = (self.temp_c & 0xFFF) << 4
        # 0x7030: droop / overshoot
        words["0x7030"] = (self.droop_mv & 0xFFFF) | ((self.overshoot_mv & 0xFFFF) << 16)
        # 0x7034: settling
        words["0x7034"] = self.settling_us & 0xFFFF
        return words


class MockTelemetryGenerator:
    """
    Generates realistic telemetry frames for each ATP scenario.
    Single instance should be used across scenarios to maintain monotonic timestamps.
    """

    RAILS = ["VCORE", "VDDQ", "VCCIO", "VCCAUX", "VPP", "VTT"]

    def __init__(self, seed: int = 42):
        random.seed(seed)
        self._ts_ns: int = 0

    def _tick(self, delta_ns: int = 10_000) -> int:
        """Advance clock. Default 10 µs per sample."""
        self._ts_ns += delta_ns
        return self._ts_ns

    def _nominal(self, delta_ns: int = 1_000_000) -> TelemetrySample:
        """Return one nominal-state sample."""
        return TelemetrySample(
            timestamp_ns=self._tick(delta_ns),
            vin_valid=True, bus_ok=True, vcap_mv=1200, temp_c=45, fault_flags=0,
            pgood=[True] * 6,
            iout_ma=[5000, 3000, 1000, 500, 200, 100],
            vout_mv=[950, 1200, 3300, 1800, 2500, 1200],
            efficiency=[0.92, 0.89, 0.85, 0.82, 0.80, 0.75],
            ripple_mv=[15.0, 12.0, 20.0, 18.0, 25.0, 30.0],
            droop_mv=0, overshoot_mv=0, settling_us=0,
        )

    # ── ATP-01: VIN invalid blocks power-up (spec §5.5, ATP_VIN_INVALID=8'd1) ──

    def scenario_atp01_vin_invalid(self) -> List[TelemetrySample]:
        """ATP-01: VIN invalid — guardrail must block power-up and fire EVID.GRDT."""
        samples = [self._nominal() for _ in range(10)]
        for vin in [True, True, False, False, False]:
            s = self._nominal()
            s.vin_valid = vin
            s.vcap_mv   = 1050
            samples.append(s)
        return samples

    # ── ATP-02: PGOOD timeout → abort (spec §5.5, ATP_PGOOD_TIMEOUT=8'd2) ────

    def scenario_atp02_pgood_timeout(self) -> List[TelemetrySample]:
        """ATP-02: PGOOD never asserts — sequencing must time out and emit EVID.TOU."""
        samples = []
        for step in range(20):
            s = self._nominal()
            # Rail 0 (VCORE) never goes PGOOD in this scenario
            s.pgood = [False] * 6
            if step > 5:
                s.pgood[1] = True   # Rail 1 comes up; rail 0 stays down — timeout
            samples.append(s)
        return samples

    # ── ATP-03–12: Engineering validation scenarios (not in RTL spec §5.5) ─────
    # These are XR-PMC §9.2-inspired scenarios for extended validation.
    # Pass/fail criteria must be defined per DESIGN_005 before formal sign-off.

    def scenario_atp03_brownout(self) -> List[TelemetrySample]:
        """ATP-03: Gradual vcap brownout → UPASL EPS VIOL → REFUSE decision."""
        samples = []
        for vcap in [1200, 1150, 1100, 1050, 1000, 950, 900, 850, 800, 750]:
            s = self._nominal()
            s.vcap_mv = vcap
            s.vout_mv[0] = vcap         # VCORE tracks vcap in this scenario
            s.fault_flags = 0 if vcap >= 900 else 0x4  # UVP flag at 850 mV
            samples.append(s)
        return samples

    def scenario_atp04_protection_ocp(self) -> List[TelemetrySample]:
        """ATP-04: VCORE overcurrent ramp → fault_flags OCP bit → REFUSE."""
        samples = []
        for iout in [5000, 5500, 6000, 6500, 7000, 7500, 8000]:
            s = self._nominal()
            s.iout_ma[0] = iout
            s.fault_flags = 0x01 if iout >= 7000 else 0     # OCP bit [0]
            samples.append(s)
        return samples

    def scenario_atp05_sequencing_nominal(self) -> List[TelemetrySample]:
        """ATP-05: Full nominal POWER_ON sequence — all 6 rails come up in order."""
        samples = []
        pgood_state = [False] * 6
        for rail in range(6):
            for ramp_step in range(5):
                s = self._nominal()
                if ramp_step == 4:
                    pgood_state[rail] = True
                s.pgood = pgood_state.copy()
                samples.append(s)
        return samples

    def scenario_atp06_sequencing_retry(self) -> List[TelemetrySample]:
        """ATP-06: Rail 2 (VCCIO) fails, auto-retry on cycle 3."""
        samples = []
        for attempt in range(3):
            for _ in range(5):
                s = self._nominal()
                # Rail 2 comes up only on 3rd attempt
                s.pgood = [True, True, attempt >= 2, True, True, True]
                s.fault_flags = 0 if attempt >= 2 else 0x08  # PGOOD fault flag
                samples.append(s)
        return samples

    def scenario_atp07_rt_trigger(self) -> List[TelemetrySample]:
        """ATP-07: Upstream outage → vcap discharge → RT holds output."""
        samples = []
        for vcap in [1200, 1150, 1100, 1050, 1000, 950, 900, 850]:
            s = self._nominal(delta_ns=5_000_000)
            s.vin_valid = vcap > 950
            s.vcap_mv   = vcap
            s.droop_mv  = max(0, 50 - (vcap - 850))
            s.overshoot_mv = 30
            s.settling_us  = 200
            samples.append(s)
        return samples

    def scenario_atp08_rt_guardrail(self) -> List[TelemetrySample]:
        """ATP-08: Over-temperature ramp → UPASL Thermal VIOL → REFUSE."""
        samples = []
        for temp in [45, 60, 75, 90, 105, 110, 115]:
            s = self._nominal()
            s.temp_c      = temp
            s.vin_valid   = False          # Combined stress: VIN + OTP
            s.vcap_mv     = 900
            s.fault_flags = 0x10 if temp >= 105 else 0    # OTP bit [4]
            samples.append(s)
        return samples

    def scenario_atp09_evidence_ordering(self) -> List[TelemetrySample]:
        """ATP-09: 1000 high-rate events → stress evidence FIFO, check no drops."""
        samples = []
        for _ in range(1000):
            s = self._nominal(delta_ns=1_000)     # 1 µs per sample → 1 MHz rate
            s.fault_flags  = random.randint(0, 1)
            s.pgood        = [random.random() > 0.1 for _ in range(6)]
            s.droop_mv     = random.randint(0, 100)
            s.overshoot_mv = random.randint(0, 50)
            s.settling_us  = random.randint(100, 500)
            samples.append(s)
        return samples

    def scenario_atp10_ai_gate(self) -> List[TelemetrySample]:
        """ATP-10: Sweep feature vector — verify ML_CAPTURE captures unique vectors."""
        samples = []
        for i in range(50):
            s = self._nominal()
            s.iout_ma[0]    = 5000 + i * 100
            s.efficiency[0] = max(0.5, 0.92 - i * 0.002)
            s.ripple_mv[0]  = 15.0 + i
            s.droop_mv      = i * 2
            s.overshoot_mv  = i
            s.settling_us   = 100 + i * 5
            samples.append(s)
        return samples

    def scenario_atp11_bus_export(self) -> List[TelemetrySample]:
        """ATP-11: SMBus/PMBus export — host-side check; use nominal sensor data."""
        return [self._nominal() for _ in range(100)]

    def scenario_atp12_config_reject(self) -> List[TelemetrySample]:
        """ATP-12: Invalid rail-graph config — validates host-side rejection; nominal data."""
        return [self._nominal() for _ in range(20)]


# ── Scenario registry ──────────────────────────────────────────────────────────
# IMPORTANT: Use a SINGLE generator instance.
# Do NOT create a new MockTelemetryGenerator() per entry (timestamps would reset).

_GEN = MockTelemetryGenerator()

ALL_SCENARIOS: Dict[str, callable] = {
    "ATP-01": _GEN.scenario_atp01_vin_invalid,        # Formally spec'd
    "ATP-02": _GEN.scenario_atp02_pgood_timeout,       # Formally spec'd
    "ATP-03": _GEN.scenario_atp03_brownout,            # Engineering validation
    "ATP-04": _GEN.scenario_atp04_protection_ocp,
    "ATP-05": _GEN.scenario_atp05_sequencing_nominal,
    "ATP-06": _GEN.scenario_atp06_sequencing_retry,
    "ATP-07": _GEN.scenario_atp07_rt_trigger,
    "ATP-08": _GEN.scenario_atp08_rt_guardrail,
    "ATP-09": _GEN.scenario_atp09_evidence_ordering,
    "ATP-10": _GEN.scenario_atp10_ai_gate,
    "ATP-11": _GEN.scenario_atp11_bus_export,
    "ATP-12": _GEN.scenario_atp12_config_reject,
}


def export_scenario(name: str, samples: List[TelemetrySample]) -> None:
    """Export scenario to NDJSON file for HDL co-simulation or host-side replay."""
    import os
    os.makedirs("output/telemetry", exist_ok=True)
    path = f"output/telemetry/{name.replace('-','_').lower()}.ndjson"
    with open(path, "w") as f:
        for s in samples:
            f.write(json.dumps({
                "ts_ns":       s.timestamp_ns,
                "vin_valid":   s.vin_valid,
                "bus_ok":      s.bus_ok,
                "vcap_mv":     s.vcap_mv,
                "temp_c":      s.temp_c,
                "fault_flags": s.fault_flags,
                "pgood":       s.pgood,
                "iout_ma":     s.iout_ma,
                "vout_mv":     s.vout_mv,
                "efficiency":  s.efficiency,
                "ripple_mv":   s.ripple_mv,
                "droop_mv":    s.droop_mv,
                "overshoot_mv":s.overshoot_mv,
                "settling_us": s.settling_us,
                "axi_words":   s.to_axi_feature_words(),
            }) + "\n")
    print(f"  Exported {len(samples):>5} samples → {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="AI-PMC Mock Telemetry Generator")
    parser.add_argument("--export", metavar="SCENARIO",
                        help="Export scenario to NDJSON. Use 'all' for all scenarios.")
    args = parser.parse_args()

    print("Mock Telemetry Generator — AI-PMC Walkthrough")
    print("=" * 60)

    for name, fn in ALL_SCENARIOS.items():
        tag = "(spec §5.5)" if name in ("ATP-01", "ATP-02") else "(engineering)"
        samples = fn()   # FIX WK-B1: call with no extra args (bound method)
        print(f"  {name} {tag}: {len(samples):>5} samples | "
              f"ts_span={samples[-1].timestamp_ns - samples[0].timestamp_ns:,} ns")

        if args.export and (args.export == "all" or args.export == name):
            export_scenario(name, samples)

    if args.export == "all":
        print("\nAll scenarios exported to output/telemetry/")


if __name__ == "__main__":
    main()
