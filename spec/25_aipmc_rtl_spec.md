# AI-PMC FPGA RTL Specification
## Universal Physical Admissibility and Stabilisation Layer (UPASL) — RTL Implementation

```
Document Number : SOVEREIGN-SPEC-RTL-001
Version         : 1.0.0
Status          : APPROVED-DRAFT
Design Owner    : Sovereign Matrix Engineering
Date            : 2026-04-11
Target Device   : Xilinx Zynq UltraScale+ xczu7ev-ffvc1156-2-e
                  (Versal VP1002 secondary target)
Interface       : ARM AXI4-Lite + AXI4-Stream
Reference Docs  : AI-PMC Software Spec G_26260208_V0.1
                  XR-PMC Engineering Spec Draft_20260202
                  UPASL Specification Rev 1.1
                  spec/24_mcp_fpga.md (MCP/AXI transport layer)
```

---

## 1. Purpose and Scope

This specification defines the complete synthesizable RTL architecture for the **AI-PMC (AI-native Power Management Controller)** FPGA implementation. It governs the hardware design of all 15 modules across the Ontology Silicon Module hierarchy.

The FPGA implements:

| Layer | Modules | Purpose |
|---|---|---|
| **Governance Layer** | M-04 GovernanceFSM, M-05 SequencingEngine | Power state machine + rail sequencing |
| **Evidence Layer** | M-03 EvidenceEncoder | NDJSON audit trail capture |
| **Verification Layer** | M-06/07 ATPHardware | Automated test pattern injection |
| **ML Layer** | M-08 FeatureExtractor | 64-byte training vector generation |
| **Domain Layer** | UPASLDomainEngine | 6-domain physical admissibility |
| **Compute Layer** | PrimaryDecomposer, GroebnerBasisEngine | Algebraic reasoning acceleration |
| **Interface Layer** | AXISlaveInterface, TelemetryAggregator, MCPJsonRpcDecoder | AXI + serial bus bridging |
| **Storage Layer** | BRAMAxiomStore | 4096×64-bit axiom memory |
| **Semantic Layer** | SemanticDistanceEngine, CausalInvariantTracker | Distance + invariant checking |

---

## 2. System Architecture

```
        ┌─────────────────────────────────────────────────────────────────┐
        │              OntologySiliconModule (Top-Level Wrapper)           │
        │                                                                  │
        │  ┌───────────────────────────────────────────┐                  │
        │  │          AXI Slave Interface (M-01)        │◄── AXI4-Lite    │
        │  │       Register Map 0x0000–0x7FFF           │◄── AXI4-Stream  │
        │  └──────────────┬──────────────┬──────────────┘                  │
        │                 │  Config/Cmd  │  Status                         │
        │   ┌─────────────▼──────────────▼────────────────────────────┐   │
        │   │              GOVERNANCE SUBSYSTEM                         │   │
        │   │  ┌──────────────────┐  ┌──────────────────────────────┐ │   │
        │   │  │  GovernanceFSM   │  │     SequencingEngine          │ │   │
        │   │  │  M-04  7-state   │  │  M-05  POWER_ON stepengine    │ │   │
        │   │  │  Guardrail check │  │  PGOOD guard + timeout        │ │   │
        │   │  └────────┬─────────┘  └──────────────┬────────────────┘ │   │
        │   └───────────┼─────────────────────────────┼────────────────┘   │
        │               │ evidence_valid/data          │ evidence_valid/data │
        │   ┌───────────▼─────────────────────────────▼────────────────┐   │
        │   │            EvidenceEncoder (M-03)                          │   │
        │   │   256-bit FIFO depth 1024 · Seq# · SUMMARY on overflow    │   │
        │   │         4-beat AXI-Stream serialisation                    │   │──► AXI4-Stream out
        │   └────────────────────────────────────────────────────────────┘   │
        │                                                                      │
        │   ┌─────────────────────────────────────────────────────────────┐   │
        │   │                  VERIFICATION SUBSYSTEM                      │   │
        │   │  ┌──────────────────────────────────────────────────────┐   │   │
        │   │  │  ATPHardware (M-06/M-07)                              │   │   │
        │   │  │  ATP-01: VIN-invalid injection + BLOCKED check         │   │   │
        │   │  │  ATP-02: PGOOD-timeout injection + TIMEOUT check       │   │   │
        │   │  │  4096-cycle dwell · 5 fail-reason codes               │   │   │
        │   │  └──────────────────────────────────────────────────────┘   │   │
        │   └─────────────────────────────────────────────────────────────┘   │
        │                                                                      │
        │   ┌─────────────────────────────────────────────────────────────┐   │
        │   │                    UPASL DOMAIN ENGINE                       │   │
        │   │   Thermal · Mechanical · EPS · Radiation · Fluid · Info      │   │
        │   │   Q16.16 limit fractions · stability index · ALLOW/LIMIT/   │   │
        │   │   REFUSE decision · safe_div to prevent ÷0                  │   │
        │   └─────────────────────────────────────────────────────────────┘   │
        │                                                                      │
        │   ┌─────────────────────────────────────────────────────────────┐   │
        │   │                 COMPUTE SUBSYSTEM (300 MHz)                   │   │
        │   │  ┌──────────────────────┐  ┌──────────────────────────────┐ │   │
        │   │  │  GroebnerBasisEngine  │─►│    PrimaryDecomposer          │ │   │
        │   │  │  4-lane systolic F4/5 │  │  Buchberger + EHV prime count│ │   │
        │   │  │  1000 iterations      │  │  1024-poly BRAM · 50K wd     │ │   │
        │   │  └──────────────────────┘  └──────────────────────────────┘ │   │
        │   │  ┌──────────────────────┐  ┌──────────────────────────────┐ │   │
        │   │  │  SemanticDistEngine  │  │  CausalInvariantTracker       │ │   │
        │   │  │  4-stage Q16.16 pipe │  │  32-entry CAM · auto-learn   │ │   │
        │   │  └──────────────────────┘  └──────────────────────────────┘ │   │
        │   └─────────────────────────────────────────────────────────────┘   │
        │                                                                      │
        │   ┌ ML / INTERFACE / STORAGE (100 MHz) ─────────────────────────┐   │
        │   │  FeatureExtractor(M-08) · TelemetryAggregator                │   │
        │   │  BRAMAxiomStore · MCPJsonRpcDecoder                          │   │
        │   └─────────────────────────────────────────────────────────────┘   │
        └──────────────────────────────────────────────────────────────────────┘

        Sensor Inputs: vin_valid, bus_ok, vcap[11:0], temp[11:0],
                       pgood[7:0], fault_flags[31:0],
                       adc_bus_voltage, adc_bus_current, adc_battery_soc,
                       adc_dose_rate, adc_fill_fraction,
                       pmbus/i2c/spi/uart/gpio

        Control Outputs: en_out[7:0], reset_out[7:0], irq_out
```

---

## 3. Clock Domain Architecture

| Domain | Frequency | Modules | Notes |
|---|---|---|---|
| `clk_100` | 100 MHz | All AXI, governance, evidence, ATP, ML, telemetry | Control path |
| `clk_300` | 300 MHz | Groebner, PrimaryDecomposer | Compute path; CG-isolated from clk_100 |

**CDC Policy:** All signals crossing `clk_100 ↔ clk_300` must use:
- 2-FF synchronizers for single-bit control
- Gray-code FIFO for multi-bit data (FPGA primitive `xpm_cdc_gray`)
- False-path constraints set in `ontology_silicon.xdc`

---

## 4. AXI Register Map (Complete)

### 4.1 Core Control Block — 0x0000–0x0FFF

| Offset | Name | R/W | Reset | Description |
|---|---|---|---|---|
| 0x0000 | STATUS | R | 0 | [0]=BUSY [1]=DONE [2]=ERROR [3]=DECOMP_ACTIVE [4]=GOV_FAULT [5]=ATP_BUSY |
| 0x0004 | CONTROL | W | 0 | [0]=START [1]=RESET [2]=CLEAR_IRQ [3]=ML_CAPTURE [4]=ATP_INJECT [5]=ATP_CHECK |
| 0x0008 | IRQ_ENABLE | R/W | 0 | Bit mask: [0]=done [1]=error [2]=gov_fault [3]=seq_done [4]=atp_done |
| 0x000C | AXIOM_COUNT | R | 0 | Number of axioms loaded into BRAM |
| 0x0010 | PRIME_COUNT | R | 0 | Irreducible component count (PrimaryDecomposer result) |
| 0x0014 | SEMANTIC_DIST | R | 0 | Q16.16 fixed-point semantic distance |
| 0x0018 | RUNTIME_LSW | R | 0 | Runtime cycle counter [31:0] |
| 0x001C | RUNTIME_MSW | R | 0 | Runtime cycle counter [63:32] |
| 0x0020 | AXIOM_BASE_ADDR | W | 0 | BRAM base address for axiom polynomials |
| 0x0024 | RESULT_BASE_ADDR | W | 0 | BRAM base address for decomposition results |
| 0x0028 | TARGET_ADDR | W | 0 | BRAM address of target polynomial Q |
| 0x002C | ERROR_CODE | R | 0 | Last error: 0=none, E001=FILE_NOT_FOUND … E010=HITL_TIMEOUT |

### 4.2 Governance Config Block — 0x1000–0x1FFF

| Offset | Name | R/W | Reset | Description |
|---|---|---|---|---|
| 0x1000 | GOV_PROFILE_ID | R/W | 0 | Active governance profile (A1/A2/B1/B2 encoded) |
| 0x1004 | GOV_TIMEOUT_MS | R/W | 1000 | Single-step timeout in milliseconds |
| 0x1008 | GOV_THRESHOLDS | R/W | - | [23:12]=temp_max_C × 10, [11:0]=vcap_min_mV |
| 0x100C | GOV_HYSTERESIS | R/W | 0 | Hysteresis window for guardrail re-arm |
| 0x1010 | GOV_ALLOWED_ACTIONS | R/W | 0xFF | Bitmask: [0]=throttle [1]=timing_shift [2–7]=reserved |

### 4.3 Evidence FIFO Block — 0x2000–0x2FFF

| Offset | Name | R/W | Reset | Description |
|---|---|---|---|---|
| 0x2000 | EVIDENCE_STATUS | R | 0 | [0]=EMPTY [1]=FULL [9:2]=FIFO_COUNT[7:0] |
| 0x2004 | EVIDENCE_COUNT | R | 0 | Full 10-bit FIFO depth read |
| 0x2008 | EVIDENCE_ACK | W | 0 | Write 1 to pop head record from FIFO |
| 0x200C | EVIDENCE_SEQ_NUM | R | 0 | Monotonic record sequence number |
| 0x2010 | EVIDENCE_DROPPED | R | 0 | Overflow-dropped record count |

### 4.4 Governance FSM Block — 0x3000–0x3FFF

| Offset | Name | R/W | Reset | Description |
|---|---|---|---|---|
| 0x3000 | GOV_STATE | R | 0 | Current FSM state: 0=BOOT 1=IDLE 2=PUP 3=RUN 4=PDOWN 5=FAULT 6=SAFE |
| 0x3004 | GOV_FAULT_CAUSE | R | 0 | Guardrail reason code (1–5, 0=no fault) |
| 0x3008 | GOV_UPTIME_NS | R | 0 | ns-resolution uptime in RUN state |
| 0x300C | GOV_PWR_UP_REQ | W | 0 | Write 1 to request power-up transition |
| 0x3010 | GOV_PWR_DOWN_REQ | W | 0 | Write 1 to request power-down transition |
| 0x3014 | GOV_THROTTLE_REQ | W | 0 | [7:0] throttle percentage (0=off, 255=full throttle) |

### 4.5 Sequencing Engine Block — 0x4000–0x4FFF

| Offset | Name | R/W | Reset | Description |
|---|---|---|---|---|
| 0x4000 | SEQ_STATE | R | 0 | 0=IDLE 1=START 2=RUN 3=HOLD 4=DONE 5=FAIL |
| 0x4004 | SEQ_CMD | W | 0 | [0]=START [1]=STOP [2]=HOLD [3]=RESUME |
| 0x4008 | SEQ_STEP_ID | R | 0 | [7:0] current step index |
| 0x400C | SEQ_TIMEOUT_MS | R/W | 1000 | Per-step timeout override |
| 0x4010 | SEQ_PGOOD | R | 0 | Live pgood_in[7:0] snapshot |
| 0x4014 | SEQ_EN_OUT | R | 0 | Current en_out[7:0] driver state |

### 4.6 ATP Harness Block — 0x5000–0x5FFF

| Offset | Name | R/W | Reset | Description |
|---|---|---|---|---|
| 0x5000 | ATP_INJECT_FAULT | W | 0 | Fault test ID to inject (see §7.1) |
| 0x5004 | ATP_TEST_PASS | R | 0 | [0]=PASS after evaluation |
| 0x5008 | ATP_FAIL_REASON | R | 0 | Failure reason code (see §7.2) |
| 0x500C | ATP_STATUS | R | 0 | [0]=BUSY [1]=DONE |
| 0x5010 | ATP_TIMEOUT_MS | R/W | 10 | Injected fast-timeout value |

### 4.7 UPASL Domain Block — 0x6000–0x6FFF

| Offset | Name | R/W | Reset | Description |
|---|---|---|---|---|
| 0x6000 | THERMAL_STATUS | R | UND | 3-bit: 001=SAT 010=VIOL 100=UND |
| 0x6004 | MECH_STATUS | R | UND | As above |
| 0x6008 | EPS_STATUS | R | UND | As above |
| 0x600C | RAD_STATUS | R | UND | As above |
| 0x6010 | FLUID_STATUS | R | UND | As above |
| 0x6014 | INFO_STATUS | R | UND | As above |
| 0x6018 | THERMAL_LF | R | 0 | Limit fraction Q16.16 (Eq.20) |
| 0x601C | MECH_LF | R | 0 | As above |
| 0x6020 | EPS_LF | R | 0 | As above |
| 0x6024 | RAD_LF | R | 0 | As above |
| 0x6028 | FLUID_LF | R | 0 | As above |
| 0x602C | INFO_LF | R | 0 | As above |
| 0x6030 | GLOBAL_HAZARD | R | 0 | Q16.16 = 1.0 − stability_index |
| 0x6034 | STABILITY_INDEX | R | 0 | Q16.16 mean of limit fractions |
| 0x6038 | UPASL_DECISION | R | REFUSE | 0=REFUSE 1=LIMIT 2=ALLOW |
| 0x6040 | THRESHOLD_CONFIG_0 | W | - | [31:16]=t_dot_max [15:0]=t_max (Thermal) |
| 0x6044 | THRESHOLD_CONFIG_1 | W | - | [31:16]=h_t_min [15:0]=sigma_max (Mech) |
| 0x6048 | THRESHOLD_CONFIG_2 | W | - | [31:16]=v_min [15:0]=soc_min (EPS) |
| 0x604C | THRESHOLD_CONFIG_3 | W | - | [31:16]=d_max [15:0]=l_max (Rad/Info) |

### 4.8 Feature Extractor Block — 0x7000–0x7FFF

| Offset | Name | R/W | Description |
|---|---|---|---|
| 0x7000–0x700F | FEATURE_VEC_0–3 | R | Bytes 0–15: VOUT[0–7] in Q4.8 |
| 0x7010–0x701F | FEATURE_VEC_4–7 | R | Bytes 16–31: IOUT[0–7] |
| 0x7020–0x702F | FEATURE_VEC_8–B | R | Bytes 32–47: Efficiency, Ripple |
| 0x7030–0x703F | FEATURE_VEC_C–F | R | Bytes 48–63: Temp, Droop, Overshoot, Settling |
| 0x7040 | FEATURE_VALID | R | [0]=valid after last capture |

---

## 5. Module Specifications

### 5.1 M-01: AXI Slave Interface
**File:** `fpga/rtl/axi_slave_interface.v`

| Parameter | Value |
|---|---|
| Address width | 15-bit (32 KB window) |
| Data width | 32-bit |
| Register count | 256 (word-addressed) |
| Write latency | 2 cycles (AW + W accepted simultaneously) |
| Read latency | 2 cycles |
| Command outputs | `seq_start/stop/hold/resume`, `atp_inject/check`, `ml_capture` (single-cycle strobes) |

**Write path:**
```
AW accepted → aw_pend=1
W  accepted → w_pend=1
Both pending → write to RF[word_idx] + shadow decode → bresp=OKAY
```

**Read path:** Combinatorial mux over status registers registered from all submodules.

---

### 5.2 M-03: Evidence Encoder
**File:** `fpga/rtl/evidence_encoder.v`

#### Evidence Record Format (256 bits)

```
 Bits [255:224]  ts_ns[31:0]         — Nanosecond timestamp (×10 per 100MHz cycle)
 Bits [223:160]  event_id[63:0]      — ASCII-packed event type
 Bits [159:128]  state_id[31:0]      — Current FSM state at emission
 Bits [127:96]   severity[31:0]      — 0=INFO 1=WARN 2=CRITICAL
 Bits [95:32]    payload[63:0]       — Event-specific context
 Bits [31:0]     seq_number[31:0]    — Monotonic counter (injected by encoder)
```

#### Event ID Constants (ASCII-packed)

| Event Name | ASCII Value | Trigger |
|---|---|---|
| `EVID.BOOT` | 0x455649442E424F4F54 | System reset exit |
| `EVID.STAT` | 0x455649442E53544154 | FSM state entry |
| `EVID.GRDT` | 0x455649442E47524454 | Guardrail trip |
| `EVID.THRT` | 0x455649442E54485254 | Throttle command |
| `EVID.TIMG` | 0x455649442E54494D47 | Timing shift command |
| `EVID.SEQS` | 0x455649442E534551_53 | Sequence start |
| `EVID.STEP.ENT` | 0x455649442E535445 | Step entry |
| `EVID.STEP.EXT` | 0x455649442E535458 | Step exit |
| `EVID.BLK` | 0x455649442E424C4B | Step blocked by guard |
| `EVID.TOU` | 0x455649442E544F55 | Step timeout |
| `EVID.DON` | 0x455649442E444F4E | Sequence done |
| `SUMMARY` | 0x53554D4D41525900 | Overflow summary |

#### FIFO Overflow Policy

When `ev_full=1` and a new event arrives:
1. `dropped_count` increments
2. On next available slot: a `SUMMARY` record is emitted with `payload[31:0] = dropped_count`
3. `dropped_count` resets to 0
4. Gap detectable by receiver via discontinuity in `seq_number`

---

### 5.3 M-04: Governance FSM
**File:** `fpga/rtl/governance_fsm.v`

#### State Definitions

| State | Encoding | Description |
|---|---|---|
| BOOT | 3'd0 | Post-reset initialisation, emits EVID.BOOT |
| IDLE | 3'd1 | Awaiting `power_up_req`; guardrails checked |
| POWERUP | 3'd2 | Rail sequencing in progress |
| RUN | 3'd3 | Normal operating state |
| POWEROFF | 3'd4 | Controlled shutdown |
| FAULT | 3'd5 | Guardrail condition active |
| SAFE | 3'd6 | Cleared fault, awaiting manual recovery |

#### Guardrail Evaluation (every clock edge)

```verilog
wire gr_vin  = ~vin_valid;                         // Reason 1
wire gr_bus  = ~bus_ok;                            // Reason 2
wire gr_vcap = (vcap < vcap_min);                  // Reason 3
wire gr_temp = (temp > temp_max);                  // Reason 4
wire gr_flt  = (fault_flags != 32'd0);             // Reason 5
wire guardrail_trip = gr_vin | gr_bus | gr_vcap | gr_temp | gr_flt;
```

`vcap_min` and `temp_max` are unpacked from `thresholds[23:12]` and `thresholds[11:0]` respectively.

#### Transition Conditions

| From | To | Condition |
|---|---|---|
| BOOT | IDLE | Unconditional (1 cycle) |
| IDLE | POWERUP | `power_up_req && !guardrail_trip` |
| IDLE | FAULT | `guardrail_trip` |
| POWERUP | RUN | Sequencing engine `seq_state == DONE` |
| POWERUP | FAULT | `guardrail_trip` |
| RUN | POWEROFF | `power_down_req && !guardrail_trip` |
| RUN | FAULT | `guardrail_trip` |
| POWEROFF | IDLE | Unconditional (1 cycle) |
| FAULT | SAFE | `!guardrail_trip` (condition cleared) |
| SAFE | POWERUP | `power_up_req && !guardrail_trip` |

---

### 5.4 M-05: Sequencing Engine
**File:** `fpga/rtl/sequencing_engine.v`

#### Hardcoded POWER_ON Sequence (Spec §3.2)

| Step | ID | Semantic | Rail | Timeout | Done Condition |
|---|---|---|---|---|---|
| 0 | ON_00_PRECHECK | NOP | — | 0.01 ms | Immediate |
| 1 | ON_10_ENABLE_MAIN | ASSERT_EN | 0 | 10 ms | `pgood_in[0] == 1` |
| 2 | ON_20_ENABLE_AUX | ASSERT_EN | 1 | 10 ms | `pgood_in[1] == 1` |
| 3 | ON_30_RELEASE_RESET | RELEASE_RESET | 0 | 20 ms | Timer expiry |

#### Step Semantics

| Semantic | Action | Reset Value |
|---|---|---|
| `NOP` | No hardware action | — |
| `ASSERT_EN` | `en_out[rail] ← 1` | 0 |
| `DEASSERT_EN` | `en_out[rail] ← 0` | — |
| `RELEASE_RESET` | `reset_out[rail] ← 0` | 1 (active-high reset) |
| `ASSERT_RESET` | `reset_out[rail] ← 1` | — |

#### Guard Condition

At every step before advancing: `vin_valid && bus_ok && (fault_flags == 0)`.  
If guard fails mid-step → evidence `EVID.BLK` emitted, `seq_state → FAIL`.

---

### 5.5 M-06 / M-07: ATP Hardware
**File:** `fpga/rtl/atp_hardware.v`

#### Test Cases

| ATP Test ID | M-06/07 | Fault Injected | Expected Evidence |
|---|---|---|---|
| `ATP_VIN_INVALID = 8'd1` | M-06 | `inject_vin_invalid = 1` | `ev_has_seq_blocked=1`, `ev_has_seq_done=0` |
| `ATP_PGOOD_TIMEOUT = 8'd2` | M-07 | `inject_pgood_timeout=1`, `timeout_ms=10` | `ev_has_seq_timeout=1`, `ev_has_seq_done=0` |

#### Fail Reason Codes

| Code | Name | Meaning |
|---|---|---|
| 0 | FR_PASS | Test passed |
| 1 | FR_NO_BLOCKED_EV | ATP-01: BLOCKED evidence absent — guardrail did not fire |
| 2 | FR_DONE_WHEN_BLOCKED | ATP-01: SEQ_DONE present despite active fault — sequencing continued incorrectly |
| 3 | FR_NO_TIMEOUT_EV | ATP-02: TIMEOUT evidence absent — step did not time out |
| 4 | FR_DONE_WHEN_TIMEOUT | ATP-02: SEQ_DONE present despite timeout — should have aborted |
| 0xFF | FR_UNKNOWN_TEST | Unknown `atp_test_id` requested |

#### Dwell Timer

Fault injection is held for 4096 clock cycles (`dwell = 12'hFFF`) before evaluation. This ensures all downstream evidence paths have time to settle before the pass/fail determination.

---

### 5.6 M-08: Feature Extractor
**File:** `fpga/rtl/feature_extractor.v`

#### 64-Byte Feature Vector Layout (Spec §6.1)

| Bytes | Bits | Content | Format |
|---|---|---|---|
| 0–15 | [511:384] | VOUT[0–7] — 8 rails, 16 bits each | Q4.8 (zero-padded from 12-bit ADC) |
| 16–31 | [383:256] | IOUT[0–7] — 8 rails | Same |
| 32–47 | [255:128] | Efficiency[0–7] | Q8.8 (pre-computed externally) |
| 48–63 | [127:96] | Ripple mVpp [0–7] | 16-bit, mVpp |
| 64–79 | [95:32] | Temp[0–3] + 2× reserved | Q4.8 from ADC |
| 80–83 | [31:16] | Droop (mV) | raw 16-bit |
| 84–87 | [15:0] | Overshoot (mV) + Settling (μs) | raw 16-bit each |

**Capture protocol:** Host writes CONTROL[3]=1 (`ML_CAPTURE`). Module samples all inputs in a single clock cycle and asserts `feature_valid` for one cycle. Host must be ready (`feature_ready=1`) or the capture is silently dropped.

---

### 5.7 UPASL Domain Engine
**File:** `fpga/rtl/upasl_domain_engine.v`

#### Domain Evaluations

##### Thermal (UPASL §5)
```
SAT = (temp_hotspot ≤ T_max) ∧ (temp_rate ≤ T_dot_max) ∧
      ((T_max − temp_hotspot) ≥ H_T_min)
```

##### Mechanical (UPASL §6)
```
SAT = (stress_mech ≤ σ_max) ∧ (stress_rate ≤ σ_dot_max)
```

##### EPS / Power (UPASL §7)
```
SAT = (bus_voltage ≥ V_min) ∧ (bus_current_derivative ≤ I_dot_max) ∧
      (battery_soc ≥ SoC_min)
```

##### Radiation (UPASL §8)
```
SAT = (dose_rate ≤ D_max)
```

##### Fluid (UPASL §9)
```
SAT = (fill_fraction ≤ τ_s_max)
```

##### Information (UPASL §10)
```
SAT = (loop_latency ≤ L_max) ∧ (jitter ≤ J_max)
```

#### Limit Fraction Formula (UPASL Eq. 20)

```
limit_fraction_i = (max_i − current_i) / (max_i − min_i)   [Q16.16]
stability_index  = mean(limit_fraction_0 … limit_fraction_5)
global_hazard    = 1.0 − stability_index
```

`safe_div_q1616(num, den)` is used throughout to prevent divide-by-zero:
```verilog
function [31:0] safe_div_q1616;
    safe_div_q1616 = (den == 0)    ? 32'hFFFF_FFFF :
                     (num >= den)  ? 32'h0001_0000 :
                     (num * 32'h0001_0000) / den;
endfunction
```

#### Decision Logic (UPASL §3.2)

| Condition | Decision |
|---|---|
| Any domain VIOL or UND | REFUSE (2'b00) |
| All SAT, stability > 0.5 | ALLOW (2'b10) |
| All SAT, stability ≤ 0.5 | LIMIT (2'b01) |

---

### 5.8 Compute Subsystem

#### PrimaryDecomposer
**File:** `fpga/rtl/primary_decomposer.v`

- 4-way systolic Q16.16 reduction pipeline
- 1024-polynomial BRAM store (`ram_style="block"`)
- Eisenbud-Huneke-Vasconcelos simplified prime count
- **Watchdog:** 50,000 iterations → `error_code = E001`, `done = 1`
- Groebner basis coefficients interleaved via `gb_coeff_in`/`gb_coeff_valid`

#### GroebnerBasisEngine
**File:** `fpga/rtl/groebner_basis_engine.v`

- 4-lane systolic F4/F5 reduction, `LANE_COUNT=4`
- 1000 reduction iterations across all polynomial pairs and variables
- Identity-seeded `MAX_POLYS × MAX_VARS` basis matrix in block RAM
- Streams final basis coefficients to PrimaryDecomposer via registered output

#### SemanticDistanceEngine
**File:** `fpga/rtl/semantic_distance_engine.v`

- Compares 8 nibble-packed tokens of two 32-bit axiom IDs
- 4-stage pipeline: diff → abs → squared → sum + Q16.16 normalise
- One result per clock at steady state (after 4-cycle latency)

#### CausalInvariantTracker
**File:** `fpga/rtl/causal_invariant_tracker.v`

- 32-entry CAM, pre-loaded with 8 canonical axiom IDs at synthesis
- Auto-learns unknown IDs into free slots
- Violation: unknown ID presented → `violation_count++`, `irq_out` pulse

---

### 5.9 Interface Modules

#### TelemetryAggregator
**File:** `fpga/rtl/telemetry_aggregator.v`

| Bus | Mode | Baud / Rate |
|---|---|---|
| PMBus/I2C | Bit-bang receiver (SDA falling edge + SCL sample) | Up to 400 kHz |
| SPI | Mode 0 (CPOL=0, CPHA=0) | Up to 10 MHz |
| UART | 115200 baud, 8N1, mid-bit sampling | Fixed |
| GPIO | Passthrough mirror | Combinatorial |

#### BRAMAxiomStore
**File:** `fpga/rtl/bram_axiom_store.v`

- 4096 × 64-bit = 32 KB (2× RAMB36 when targeting 7-series)
- Port A: Read/Write (host CPU via DMA or AXI-Lite indirect)
- Port B: Read-only (PrimaryDecomposer + SemanticDistanceEngine)

#### MCPJsonRpcDecoder
**File:** `fpga/rtl/mcp_jsonrpc_decoder.v`

- Sliding 4-byte window detects ASCII "meth" keyword
- Accumulates 8 bytes of method name, matches 6 known methods
- First 64-bit params beat captured as `payload_out`
- Resets on closing brace `}` (0x7D)

---

## 6. Timing Budget

| Path | Frequency | Budget | Status |
|---|---|---|---|
| AXI4-Lite read | 100 MHz | 10.0 ns | ✅ Closed (est. 7.2 ns) |
| AXI4-Lite write | 100 MHz | 10.0 ns | ✅ Closed (est. 6.8 ns) |
| GovernanceFSM guardrail | 100 MHz | 10.0 ns | ✅ Closed (est. 4.1 ns, combinatorial) |
| UPASLDomainEngine all 6 | 100 MHz | 10.0 ns | ✅ Closed with 1-cycle reg |
| GroebnerBasisEngine systolic | 300 MHz | 3.33 ns | ⚠️ Requires ExtraTimingOpt placement |
| PrimaryDecomposer BRAM | 300 MHz | 3.33 ns | ⚠️ BRAM output registered (2-cycle latency) |
| SemanticDistance 4-stage | 100 MHz | 10.0 ns | ✅ Closed (est. 5.6 ns) |
| EvidenceEncoder FIFO | 100 MHz | 10.0 ns | ✅ Closed |

> **Timing closure note:** The 300 MHz Groebner path requires `directive ExtraTimingOpt` in `place_design` and placement within `CLOCKREGION_X0Y2:CLOCKREGION_X1Y3` as defined in `ontology_silicon.xdc`.

---

## 7. Resource Utilisation (Estimated — xczu7ev)

| Module | LUTs | FFs | BRAM36 | DSP48 |
|---|---|---|---|---|
| AXISlaveInterface | 800 | 600 | 0 | 0 |
| GovernanceFSM | 1,200 | 800 | 0 | 0 |
| SequencingEngine | 1,500 | 1,200 | 2 | 0 |
| EvidenceEncoder | 800 | 1,500 | 4 | 0 |
| ATPHardware | 600 | 400 | 0 | 0 |
| FeatureExtractor | 400 | 600 | 0 | 0 |
| UPASLDomainEngine | 5,000 | 4,000 | 2 | 32 |
| PrimaryDecomposer | 2,000 | 1,600 | 6 | 16 |
| GroebnerBasisEngine | 2,000 | 1,800 | 4 | 48 |
| SemanticDistEngine | 300 | 400 | 0 | 8 |
| CausalInvariantTracker | 600 | 500 | 0 | 0 |
| TelemetryAggregator | 700 | 900 | 0 | 0 |
| BRAMAxiomStore | 50 | 100 | 8 | 0 |
| MCPJsonRpcDecoder | 400 | 350 | 0 | 0 |
| **Total** | **~16,350** | **~14,750** | **~26** | **~104** |
| ZU7EV Capacity | 230,400 | 460,800 | 312 | 1,728 |
| **Utilisation** | **7.1%** | **3.2%** | **8.3%** | **6.0%** |

---

## 8. Interrupt Architecture

```
                GOV_FAULT  → irq_sources[2]
                SEQ_DONE   → irq_sources[3]
                ATP_DONE   → irq_sources[4]
                EVID_FULL  → irq_sources[5]
                DECOMP_DONE→ irq_sources[1]
                ML_READY   → irq_sources[6]
                         └──────► AND └── irq_out (edge to PS GIC)
                                  irq_enable[7:0]
```

All IRQ sources gate through `irq_enable` mask (AXI register 0x0008). Software must:
1. Read `STATUS` to decode source
2. Handle the event
3. Write `CONTROL[2]=1` to clear

---

## 9. Error Code Reference

| Code | Name | Source | Recovery |
|---|---|---|---|
| E001 | FILE_NOT_FOUND | PrimaryDecomposer watchdog | No retry — reload axiom BRAM |
| E002 | GEMINI_API_TIMEOUT | MCP Proxy (SW) | Retry up to 3× |
| E003 | INVALID_JSON_RESPONSE | MCPJsonRpcDecoder | Retry up to 2× |
| E004 | SCHEMA_VALIDATION_FAILED | UPASLDomainEngine | Check threshold config |
| E005 | MODULE_TIMEOUT | GovernanceFSM step timeout | Retry up to 3× |
| E006 | DRIFT_DETECTION_FAILED | CausalInvariantTracker | Manual axiom review |
| E007 | CAUSAL_CHAIN_BROKEN | CausalInvariantTracker | HITL escalation |
| E008 | DATABASE_CONNECTION_FAILED | BRAMAxiomStore (SW) | Retry up to 3× |
| E009 | BUS_ROUTING_FAILED | AXISlaveInterface | Reset CONTROL[1] |
| E010 | HITL_TIMEOUT | SW HITL modal | Escalate to audit |

---

## 10. Security Considerations

| Item | Requirement | Implementation |
|---|---|---|
| Register access | AXI4-Lite protection via PS TrustZone | Config registers in NS=0 (Secure) zone |
| Evidence FIFO | Non-writable from NS domain | AXI-Lite `awprot[1]` checked for write |
| ATP injection | Restricted to production test mode | `allowed_actions[7]` gating |
| Feature vectors | ML data must not leak axiom internals | `FEATURE_VALID` cleared after first read |
| Bitstream | AES-256 encrypted, BBRAM key | Set in Vivado Security tab |

---

## 11. Revision History

| Version | Date | Author | Change |
|---|---|---|---|
| 0.1 | 2026-04-09 | Sovereign Matrix Eng | Initial draft |
| 0.9 | 2026-04-10 | Sovereign Matrix Eng | All 15 modules defined |
| 1.0.0 | 2026-04-11 | Sovereign Matrix Eng | APPROVED-DRAFT — AXI map, timing, resources |
