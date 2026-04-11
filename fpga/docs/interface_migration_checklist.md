# Interface Migration Checklist — Sovereign Matrix v1.1.0
> **Layer 7 Preventive Document** | Required review for any port-renaming PR

## Purpose
This checklist must be completed by any engineer renaming, adding, or removing ports
on any RTL module. It prevents a recurrence of the v1.0→v1.1 refactoring errors
documented in RCA report `rca_fpga_errors.md`.

---

## Checklist — Module Port Change

**Module being changed:** `_____________________`  
**Author:** `_____________________`  
**Date:** `_____________________`  
**PR / Commit:** `_____________________`

### Step 1 — Specification Check
- [ ] Change is reflected in `spec/25_aipmc_rtl_spec.md` (update spec FIRST)
- [ ] Version header in spec is bumped (e.g. `v1.0.0 → v1.1.0`)
- [ ] Change log entry added in spec

### Step 2 — RTL Module
- [ ] Port list updated in the **module declaration** (not just internal wires)
- [ ] All **instantiations** of this module updated in `ontology_silicon_module.v`
- [ ] If output port type changed (array → flat bus): run RULE-01 check (`lint_rtl.py`)
- [ ] If adding a CDC-crossing port: 2-FF synchroniser added and XDC `max_delay` constraint added
- [ ] Version header in RTL file bumped
- [ ] `TEST_POINT` comment added near changed logic

### Step 3 — Testbench Update
- [ ] Testbench(es) that instantiate this module updated to match new port names
- [ ] All wire/reg declarations in testbench match new widths
- [ ] No `'{...}` SystemVerilog aggregate syntax used if file is `.v` (not `.sv`)
- [ ] Testbench elaboration verified locally before PR open

### Step 4 — Elaboration Gate
- [ ] `fpga/scripts/pre_commit_elab.sh` run locally — exit 0
- [ ] `fpga/scripts/lint_rtl.py` run on changed files — 0 errors
- [ ] Vivado `synth_design -rtl` elaboration run — 0 ERRORs / 0 CRITICAL WARNINGs

### Step 5 — Downstream Ripple Check
Use grep to confirm no stale references:
```bash
grep -rn "<OLD_PORT_NAME>" fpga/rtl/ fpga/sim/
```
- [ ] Zero matches for old port name in `fpga/rtl/`
- [ ] Zero matches for old port name in `fpga/sim/`
- [ ] Zero matches in `fpga/scripts/*.tcl`

### Step 6 — Sign-off
- [ ] Self-review complete
- [ ] Second reviewer approved (required for any M- or M-04+ module changes)
- [ ] CI pipeline green (RTL lint + walkthrough)

---

## Reference: Known High-Risk Modules (Require Extra Care)

| Module | Risk | Reason |
|---|---|---|
| `upasl_domain_engine.v` | 🔴 HIGH | Flat-bus port change broke 3 files in v1.1 |
| `governance_fsm.v` | 🔴 HIGH | CDC crossing + new `seq_state_in` port |
| `bram_axiom_store.v` | 🟡 MEDIUM | Added `rst_n` + `data_valid_*` in v1.1 |
| `ontology_silicon_module.v` | 🔴 HIGH | Top-level — instantiates all others |
| `primary_decomposer.v` | 🟡 MEDIUM | Algorithm complexity; limited TB coverage |

---

## Quick Reference: Port Flatten Pattern (RULE-01)

**WRONG (Verilog-2001 synthesis boundary violation):**
```verilog
output reg [2:0] domain_status [0:NUM_DOMAINS-1]
```

**CORRECT (flat packed bus):**
```verilog
output reg [NUM_DOMAINS*3-1:0] domain_status_flat
// Extract: domain_status_flat[d*3+2 -: 3] == domain_status[d]
```
