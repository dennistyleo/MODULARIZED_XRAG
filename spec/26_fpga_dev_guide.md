# FPGA Development Guide
## Sovereign Matrix — AI-PMC Ontology Silicon Module

```
Document Number : SOVEREIGN-SPEC-DEV-002
Version         : 1.0.0
Status          : APPROVED-DRAFT
Target Device   : Xilinx Zynq UltraScale+ xczu7ev-ffvc1156-2-e
Vivado Version  : 2021.2 or later (2023.1 recommended)
Related Specs   : spec/25_aipmc_rtl_spec.md  (RTL specification)
                  spec/24_mcp_fpga.md         (MCP/AXI transport)
```

---

## 1. Prerequisites

### 1.1 Tools Required

| Tool | Version | Purpose |
|---|---|---|
| Xilinx Vivado | ≥ 2021.2 | Synthesis, implementation, bitstream |
| Vivado HLS | Optional | Not needed for this RTL baseline |
| ModelSim / Vivado Simulator | Any | RTL simulation |
| Python 3.10+ | Any | Test harness (`test-harness/`) |
| Git | Any | Version control |

### 1.2 Vivado Licence Requirement

The xczu7ev device requires a **Vivado Design Suite Node-Locked or Floating** licence. For evaluation:
- Use `xc7k325tffg900-2` (Kintex-7, free WebPACK) with reduced BRAM — adjust `BRAM_DEPTH` parameter to 2048
- Or use Vivado Simulator only (no device license needed for simulation)

### 1.3 Workspace Structure

```
MODULARIZED_XRAG/
└── fpga/
    ├── rtl/              ← 15 synthesizable .v modules
    ├── sim/              ← 5 testbenches
    ├── constraints/      ← ontology_silicon.xdc
    ├── scripts/          ← synthesize.tcl · implement.tcl · generate_bitstream.tcl
    └── output/           ← (auto-created) synth/ impl/ bitstream/
```

---

## 2. Quick Start — Simulation (No Board Required)

### Step 1: Open Vivado Simulator

```bash
cd /Users/leodennis/MODULARIZED_XRAG/fpga
vivado -mode tcl
```

### Step 2: Run Governance Testbench

```tcl
# Inside Vivado TCL console:
create_project -in_memory -part xczu7ev-ffvc1156-2-e

# Read all RTL (SystemVerilog superset mode — required)
foreach f [glob rtl/*.v] { read_verilog -sv $f }

# Read governance testbench
read_verilog -sv sim/governance_tb.v

# Run simulation
launch_simulation -simset sim_1 -mode behavioral
run all
```

### Step 3: Expected Output

```
PASS: TC01: GOV_STATE=FAULT on VIN invalid @ 30
PASS: TC01: Evidence emitted on guardrail trip @ 30
PASS: TC01: GOV_STATE=SAFE after guardrail clears @ 60
PASS: TC02: GOV_STATE=RUN after power_up_req @ 120
PASS: TC03: Evidence emitted for throttle command @ 130
PASS: TC04: SEQ_DONE or rail enabled @ 2130
PASS: TC05+TC08: ATP-02 PGOOD timeout → PASS @ 16530
PASS: TC07: ATP-01 VIN invalid → PASS @ 33090
PASS: TC06: Evidence FIFO has records @ 33100
PASS: TC09: Feature vector non-zero @ 33110
=== governance_tb complete ===
```

---

## 3. RTL Verilog Compatibility Rules

> This section documents the **design rules enforced in RTL v1.1** to guarantee clean synthesis under Vivado 2021.2+.

### 3.1 Language Mode: SystemVerilog Superset (`-sv`)

All files are synthesized with `read_verilog -sv`. This is required because:

| Construct | Used In | Status |
|---|---|---|
| `task` inside `always` block | `governance_fsm.v`, `sequencing_engine.v` | SV required |
| `localparam [N:0] ID = ...` long literals | All | Safe in both |
| `{N{1'b1}}` replication (explicit) | `sequencing_engine.v` | Verilog-2001 ✅ |
| Flat packed buses for arrays | `feature_extractor.v` | Verilog-2001 ✅ |

> **Do NOT use:** `'1` (SV-only fill), `'0` fill, unpacked array ports (`reg [N:0] arr [0:M]` in port list), underscores inside hex literals (`64'h1234_5678_9ABC` has underscores between 4-digit groups = OK; `64'h12345_678` = NOT OK — odd grouping causes Verilog parser issues in some configs).

### 3.2 Hex Literal Rules

```verilog
// ✅ SAFE: underscores between 4-digit groups
localparam [31:0] OK_A = 32'hDEAD_BEEF;  // standard 8-digit hex
localparam [63:0] OK_B = 64'h4556_4944_2E42_4F4F;

// ❌ UNSAFE: underscore at any position that splits the hex value ambiguously
localparam [63:0] BAD  = 64'h455649442E534551_53;  // illegal: underscore between groups of 16+2
```

### 3.3 Reset Values

```verilog
// ✅ Correct Verilog-2001 (all RTL uses this form):
reset_out <= {MAX_RAILS{1'b1}};   // replicate 1'b1 MAX_RAILS times

// ❌ SystemVerilog-only (fixed in v1.1):
reset_out <= '1;                   // removed
```

### 3.4 Port Arrays — Use Flat Buses

```verilog
// ✅ Verilog-2001 compatible (used in feature_extractor.v v1.1+):
input wire [ADC_WIDTH*8-1:0] vout_flat,  // flat packed bus
// Access lane i: vout_flat[i*ADC_WIDTH +: ADC_WIDTH]

// ❌ SystemVerilog-only (removed from RTL):
input wire [ADC_WIDTH-1:0] vout [0:7],   // unpacked array port
```

### 3.5 Initial Blocks for ROM Initialization

`initial begin ... end` blocks in `SequencingEngine` (step ROM) will synthesize correctly in Vivado as **distributed RAM or ROM** with initial contents. This is the standard pattern for initializing small LUT-based tables. It is **not** simulation-only here.

> If Vivado reports a warning `"Initial value not supported"`, wrap with `(* rom_style = "distributed" *)` attribute on the register array.

---

## 4. Synthesis Flow

### 4.1 Run Synthesis

```bash
cd /Users/leodennis/MODULARIZED_XRAG/fpga
vivado -mode batch -source scripts/synthesize.tcl 2>&1 | tee output/synth_run.log
```

Expected console output:
```
  [OK] RTL: bram_axiom_store.v
  [OK] RTL: causal_invariant_tracker.v
  ... (15 files)
  [OK] RTL: ontology_silicon_module.v
INFO: [Synth 8-7079] Finished RTL Elaboration
...
INFO: Top-level cell count: <N>
Synthesis complete → output/synth/OntologySiliconModule_synth.dcp
```

### 4.2 Check Reports

After synthesis, review these files in `fpga/output/synth/`:

| Report | What to Check |
|---|---|
| `utilization_synth.rpt` | LUTs, FFs, BRAM should be < 10% |
| `timing_synth.rpt` | No CRITICAL WARNINGs; WNS should be positive |
| `drc_synth.rpt` | Zero errors; warnings about `initial` in non-BRAM OK |
| `methodology_synth.rpt` | Review CDC warnings — expected for clk_100↔clk_300 |
| `clocks_synth.rpt` | Verify `clk_100` (10 ns) and `clk_300` (3.33 ns) defined |

### 4.3 Common Synthesis Errors and Fixes

| Error Message | Root Cause | Fix |
|---|---|---|
| `[Synth 8-549] 'decomp_done' is not declared` | Old AXI interface without port | Upgrade to v1.1: `git pull` |
| `[Synth 8-2715] 'reset_out' is never driven` | `'1` SV syntax not parsed | Upgrade sequencing_engine.v v1.1 |
| `[Synth 8-5544] Unsupported array port` | Unpacked port without `-sv` | Add `-sv` to `read_verilog`; use `synthesize.tcl v1.1` |
| `[Synth 8-6841] Literal has X bits` | Underscore in odd hex position | Check hex literals — only `XXXX_YYYY` groups |
| `[DRC UCIO-1] No constraints for clock` | Missing `create_clock` | Verify `ontology_silicon.xdc` loaded correctly |
| `[Timing 38-282] Clock ... not found` | clk_100/clk_300 port name mismatch | Check top-level port names match XDC |

---

## 5. Implementation Flow

### 5.1 Run Implementation

```bash
vivado -mode batch -source scripts/implement.tcl 2>&1 | tee output/impl_run.log
```

### 5.2 Timing Closure Guidance

| Path | Expected WNS | If Failing |
|---|---|---|
| clk_100 paths (AXI, governance, evidence) | > 2.0 ns | Try `place_design -directive Default` |
| clk_300 paths (Groebner systolic) | > 0.2 ns | Move `u_gb` pblock to SLR with best routing |
| CDC paths (clk_100 → clk_300) | N/A (false paths) | Verify `set_false_path` in XDC applied |

**If clk_300 fails to close:**

```tcl
# In implement.tcl, change:
place_design  -directive ExtraTimingOpt
phys_opt_design -directive AggressiveExplore
route_design  -directive AggressiveExplore

# If still failing, reduce Groebner frequency:
# Change in constraints: create_clock -period 4.0 [get_ports clk_300]
# And add: set_property LOC BUFGCE [get_cells u_gb/...]
```

### 5.3 Power Estimation

From `fpga/output/impl/power_impl.rpt`:

| Domain | Expected |
|---|---|
| Static | ~0.8 W |
| Dynamic (clk_100 at 100 MHz) | ~0.4 W |
| Dynamic (clk_300 Groebner) | ~0.6 W |
| **Total** | **~1.8 W** |

---

## 6. Bitstream Generation

```bash
vivado -mode batch -source scripts/generate_bitstream.tcl
```

Output: `fpga/output/bitstream/OntologySiliconModule.bit`

### Flashing via Vivado Hardware Manager

```tcl
open_hw_manager
connect_hw_server
open_hw_target
set_property PROGRAM.FILE {fpga/output/bitstream/OntologySiliconModule.bit} [get_hw_devices]
program_hw_devices [get_hw_devices]
```

---

## 7. Board Bring-Up Checklist

After flashing, verify each subsystem in order:

### Step 1 — AXI Register Access

```c
// Read STATUS register (should return 0x00000000 after reset)
uint32_t status = Xil_In32(MCP_BASE + 0x0000);
assert(status == 0);

// Read GOV_STATE (should be IDLE=1 after boot)
uint32_t gov = Xil_In32(MCP_BASE + 0x3000);
assert(gov == 1);
```

### Step 2 — Evidence FIFO Check

```c
// Boot emits EVID.BOOT — FIFO should have 1 record
uint32_t ev_count = Xil_In32(MCP_BASE + 0x2004);
assert(ev_count >= 1);
```

### Step 3 — ATP-01 (VIN Invalid)

```c
// Inject ATP-01 test
Xil_Out32(MCP_BASE + 0x5000, 0x01);  // ATP_VIN_INVALID

// Wait for dwell (~41 us at 100 MHz)
usleep(100);

// Read result
uint32_t pass = Xil_In32(MCP_BASE + 0x5004);
uint32_t reason = Xil_In32(MCP_BASE + 0x5008);
printf("ATP-01: pass=%d reason=%d\n", pass, reason);
assert(pass == 1 && reason == 0);
```

### Step 4 — ATP-02 (PGOOD Timeout)

```c
Xil_Out32(MCP_BASE + 0x5000, 0x02);  // ATP_PGOOD_TIMEOUT
usleep(200);
uint32_t pass2 = Xil_In32(MCP_BASE + 0x5004);
assert(pass2 == 1);
```

### Step 5 — UPASL Decision

```c
// With nominal sensor values, decision should be ALLOW (2)
uint32_t dec = Xil_In32(MCP_BASE + 0x6038);
printf("UPASL decision: %d (0=REFUSE 1=LIMIT 2=ALLOW)\n", dec);
```

### Step 6 — Power-Up Governance

```c
// Request power-up
Xil_Out32(MCP_BASE + 0x3010, 0x01);  // GOV_PWR_UP_REQ
usleep(500);
uint32_t state = Xil_In32(MCP_BASE + 0x3000);
printf("GOV_STATE after pup_req: %d\n", state); // expect 2=PUP or 3=RUN
```

---

## 8. ILA Debug Probe Setup (Optional)

To add in-circuit debug, insert `ila_0` instances in Vivado before synthesis:

```tcl
# In synthesize.tcl, after read_verilog calls, add:
set_property mark_debug true [get_nets {u_gov/gov_state[*]}]
set_property mark_debug true [get_nets {u_seq/seq_state[*]}]
set_property mark_debug true [get_nets {u_ev/ev_count[*]}]
set_property mark_debug true [get_nets {u_atp/atp_pass}]
set_property mark_debug true [get_nets {u_upasl/decision[*]}]
```

Or use **Set Up Debug** in Vivado GUI (Flow Navigator → Debug).

Triggers to set:
- **GOV_STATE == FAULT (5)** → track guardrail events
- **ATP_PASS == 0 after ATP_BUSY** → diagnose test failures
- **EV_FULL == 1** → diagnose evidence overflow

---

## 9. Module-Level Simulation Commands

Run each testbench individually for focused debugging:

```bash
# UPASL domain engine only
vivado -mode batch -tclargs sim/tb_upasl_domain.v \
  -source - <<'EOF'
create_project -in_memory -part xczu7ev-ffvc1156-2-e
foreach f [glob rtl/*.v] { read_verilog -sv $f }
read_verilog -sv sim/tb_upasl_domain.v
set_property top tb_upasl_domain [current_fileset -simset]
launch_simulation
run all
EOF

# Groebner basis engine only
# (replace tb_upasl_domain → tb_groebner_basis, set top appropriately)
```

---

## 10. Parameter Tuning Guide

All parameters are set in `OntologySiliconModule` and propagate via the hierarchy.

| Parameter | Default | Safe Range | Effect |
|---|---|---|---|
| `MAX_AXIOMS` | 32 | 8–128 | Primary decomposer polynomial count |
| `MAX_VARIABLES` | 16 | 4–32 | Groebner variable count (DSP48 usage) |
| `BRAM_DEPTH` | 4096 | 256–65536 | Axiom store size (RAMB36 count) |
| `EV_FIFO_DEPTH` | 1024 | 64–4096 | Evidence records before overflow |
| `MAX_RAILS` | 8 | 2–16 | Power rails managed by sequencer |
| `ADC_WIDTH` | 12 | 10–16 | Sensor resolution (UPASL + feature ext.) |
| `EV_FIFO_DEPTH` | 1024 | 64–4096 | Evidence buffer depth |

**For Kintex-7 WebPACK (no licence):**
```verilog
// In tb or wrapper, override with smaller values:
OntologySiliconModule #(
    .MAX_AXIOMS(8),
    .MAX_VARIABLES(4),
    .BRAM_DEPTH(256),
    .EV_FIFO_DEPTH(64)
) dut (...)
```

---

## 11. Known Vivado Warnings (Expected, Non-Critical)

The following warnings are expected and do not affect functionality:

| Warning | Reason | Action |
|---|---|---|
| `[Synth 8-3331] designs with 'initial' statements` | Step ROM init blocks in SequencingEngine | None — intentional for ROM |
| `[Synth 8-6014] Unused sequential element` | `feat_valid` not consumed by AXI (registered) | None — monitoring only |
| `[CDC-1] ... no synchronizer` | clk_100→clk_300 paths | Covered by `set_false_path` in XDC |
| `[DRC MDRV-1] Multiple drivers` | `s_axi_arready` driven combinatorially + sequentially | Resolved by using `reg` throughout |

---

## 12. RTL Change Log

| Version | File | Change |
|---|---|---|
| 1.0.0 | All | Initial delivery — all 15 modules |
| 1.1.0 | `sequencing_engine.v` | Fixed `'1` → `{MAX_RAILS{1'b1}}`, fixed `_53` hex literal |
| 1.1.0 | `feature_extractor.v` | Replaced unpacked array ports with flat packed buses |
| 1.1.0 | `axi_slave_interface.v` | Added `decomp_done` input port; fixed outer case |
| 1.1.0 | `ontology_silicon_module.v` | Wired `decomp_done` to AXI; updated feature extractor call |
| 1.1.0 | `synthesize.tcl` | Added `-sv` flag, explicit ordered file list, file-exist check |
