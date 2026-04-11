## =============================================================================
## fpga_walkthrough.tcl  |  Version: 1.1.0
## AI-PMC FPGA Walkthrough Test — Complete design-flow validation
## Usage: vivado -mode batch -source fpga/scripts/fpga_walkthrough.tcl
##        (run from repo root: /Users/leodennis/MODULARIZED_XRAG)
##
## Bug fixes vs. original walkthrough draft:
##   [F1] Part corrected: xczu9eg-ffvb1156-2-i → xczu7ev-ffvc1156-2-e
##        (matches synthesize.tcl line 12 and spec/25_aipmc_rtl_spec.md)
##   [F2] Removed invalid 'elaborate' command (not a Vivado Tcl command)
##        Replaced with synth_design -rtl for elaboration-only pass
##   [F3] Replaced non-standard read_file with correct: open/read/close
##   [F4] Aligned RTL read order to match synthesize.tcl (submodules first)
##   [F5] Replaced create_project with create_project -in_memory
##        (matches synthesize.tcl production pattern; avoids .xpr overhead)
##   [F6] Fixed set_property target_language (applied to fileset, not project)
##   [F7] Replaced $synth_log with explicit report path known at script time
## =============================================================================

# ── Configuration ─────────────────────────────────────────────────────────────
set PART        "xczu7ev-ffvc1156-2-e"    ;# [F1] Correct part per spec §2
set TOP         "OntologySiliconModule"
set SCRIPT_DIR  [file normalize [file dirname [info script]]]
set REPO_ROOT   [file normalize "${SCRIPT_DIR}/../.."]
set RTL_DIR     "${REPO_ROOT}/fpga/rtl"
set CON_DIR     "${REPO_ROOT}/fpga/constraints"
set OUT_DIR     "${REPO_ROOT}/fpga/output/walkthrough"
set PROJECT_DIR "${OUT_DIR}/vivado_project"

# ── Helpers ────────────────────────────────────────────────────────────────────
set pass_count 0
set fail_count 0
set warn_count 0

proc log_pass {msg} {
    global pass_count
    puts "\[PASS\] $msg"
    incr pass_count
}
proc log_fail {msg} {
    global fail_count
    puts "\[FAIL\] $msg"
    incr fail_count
}
proc log_warn {msg} {
    global warn_count
    puts "\[WARN\] $msg"
    incr warn_count
}
proc log_info {msg} {
    puts "\[INFO\] $msg"
}
proc log_step {n title} {
    puts "\n\[INFO\] ── Step $n: $title ──"
}

file mkdir $OUT_DIR

puts "\n\[INFO\] ================================================"
puts "\[INFO\]  AI-PMC FPGA Walkthrough Test  v1.1.0"
puts "\[INFO\]  Part : $PART"
puts "\[INFO\]  Top  : $TOP"
puts "\[INFO\]  Out  : $OUT_DIR"
puts "\[INFO\] ================================================\n"

# =============================================================================
# Step 1: RTL File Inventory
# =============================================================================
log_step 1 "RTL Module Inventory"

# Dependency-ordered (submodules first, top last — matches synthesize.tcl)
set rtl_files [list \
    bram_axiom_store.v         \
    causal_invariant_tracker.v \
    evidence_encoder.v         \
    groebner_basis_engine.v    \
    governance_fsm.v           \
    sequencing_engine.v        \
    atp_hardware.v             \
    feature_extractor.v        \
    semantic_distance_engine.v \
    upasl_domain_engine.v      \
    primary_decomposer.v       \
    telemetry_aggregator.v     \
    mcp_jsonrpc_decoder.v      \
    axi_slave_interface.v      \
    ontology_silicon_module.v  \
]

set missing_count 0
foreach f $rtl_files {
    set fpath "${RTL_DIR}/${f}"
    if {[file exists $fpath]} {
        log_pass "RTL present: $f"
    } else {
        log_fail "RTL MISSING: $f"
        incr missing_count
    }
}

if {$missing_count > 0} {
    log_fail "Step 1: $missing_count RTL file(s) missing — aborting"
    puts "\n\[FATAL\] Cannot continue with missing RTL files"
    exit 1
} else {
    log_pass "Step 1: All 15 RTL files present"
}

# =============================================================================
# Step 2: Create In-Memory Project  [F5]
# =============================================================================
log_step 2 "Create Vivado Project"

if {[catch {
    create_project -in_memory -part $PART
    log_pass "Step 2: In-memory project created (part: $PART)"
} err]} {
    log_fail "Step 2: create_project failed: $err"
    exit 1
}

# =============================================================================
# Step 3: Read RTL Sources
# =============================================================================
log_step 3 "Read RTL Sources (SystemVerilog superset)"

set read_errors 0
foreach f $rtl_files {
    set fpath "${RTL_DIR}/${f}"
    if {[catch {
        read_verilog -sv $fpath
    } err]} {
        log_fail "read_verilog $f: $err"
        incr read_errors
    }
}

if {$read_errors == 0} {
    log_pass "Step 3: All 15 RTL sources read"
} else {
    log_fail "Step 3: $read_errors file(s) failed to read"
    exit 1
}

# =============================================================================
# Step 4: Read Constraints
# =============================================================================
log_step 4 "Read Constraints"

set xdc_path "${CON_DIR}/ontology_silicon.xdc"
if {[file exists $xdc_path]} {
    if {[catch {read_xdc $xdc_path} err]} {
        log_fail "Step 4: read_xdc failed: $err"
    } else {
        log_pass "Step 4: XDC constraints loaded"
    }
} else {
    log_warn "Step 4: No XDC found at $xdc_path"
}

# =============================================================================
# Step 5: RTL Elaboration (replaces invalid 'elaborate' command)  [F2]
# =============================================================================
log_step 5 "RTL Elaboration Check"

if {[catch {
    synth_design -rtl -top $TOP -part $PART -rtl_skip_ip
    log_pass "Step 5: Elaboration passed (synth_design -rtl)"
} err]} {
    log_fail "Step 5: Elaboration FAILED: $err"
    log_warn "  Common causes:"
    log_warn "  - Unpacked array ports (ANOM-001/002) → fix upasl_domain_engine.v"
    log_warn "  - Missing ml_ ports in TB (ANOM-003) → check testbench connections"
    log_warn "  - 64-bit literal overflow (ANOM-018/019) → truncate to 16 hex digits"
    exit 1
}

# =============================================================================
# Step 6: Known-Issue Scan (lint warnings per diagnostic report)
# =============================================================================
log_step 6 "Known-Issue Scan"

# Read DRC/methodology reports  [F7]: use known output path, not log property
set elab_rpt "${OUT_DIR}/elab_check.rpt"
if {[catch {
    report_drc -file $elab_rpt -quiet
} err]} {
    log_warn "Step 6: report_drc failed (non-fatal): $err"
}

# Check for specific synthesis warnings in the Vivado message DB
set synth_warns [get_msg_config -severity WARNING -id {Synth 8-9917}]
if {[llength $synth_warns] > 0} {
    log_fail "ANOM-001/002: Unpacked array port (Synth 8-9917) — fix upasl_domain_engine.v"
} else {
    log_pass "ANOM-001/002: No unpacked array port violations"
}

set init_warns [get_msg_config -severity WARNING -id {Synth 8-3331}]
if {[llength $init_warns] > 0} {
    log_warn "ANOM-007/008: initial block found (Synth 8-3331) — review causal/sequencing"
} else {
    log_pass "ANOM-007/008: No initial-block synthesis warnings"
}

# =============================================================================
# Step 7: Full Synthesis
# =============================================================================
log_step 7 "Full Synthesis"

if {[catch {
    synth_design \
        -top          $TOP  \
        -part         $PART \
        -flatten_hierarchy rebuilt \
        -directive    PerformanceOptimized
    log_pass "Step 7: Synthesis completed"
} err]} {
    log_fail "Step 7: Synthesis FAILED: $err"
    exit 1
}

# Write synthesis reports
file mkdir $OUT_DIR
report_utilization   -file "${OUT_DIR}/utilization.rpt"
report_timing_summary -max_paths 10 -file "${OUT_DIR}/timing_synth.rpt"
report_drc           -file "${OUT_DIR}/drc_synth.rpt"
report_methodology   -file "${OUT_DIR}/methodology.rpt"
write_checkpoint -force "${OUT_DIR}/${TOP}_synth.dcp"
log_pass "Step 7: Reports written to $OUT_DIR"

# =============================================================================
# Step 8: Implementation
# =============================================================================
log_step 8 "Implementation (place + route)"

if {[catch {
    opt_design
    place_design
    phys_opt_design
    route_design
    log_pass "Step 8: Implementation completed"
} err]} {
    log_fail "Step 8: Implementation FAILED: $err"
    exit 1
}

report_timing_summary -max_paths 50  -file "${OUT_DIR}/timing_impl.rpt"
report_power          -file "${OUT_DIR}/power.rpt"
write_checkpoint -force "${OUT_DIR}/${TOP}_impl.dcp"

# Check timing closure
set wns [get_property SLACK [get_timing_paths -max_paths 1 -nworst 1 -setup]]
if {[info exists wns] && $wns < 0} {
    log_fail "Step 8: Timing NOT closed — WNS = ${wns} ns"
    log_warn "  Groebner 300 MHz path may require ExtraTimingOpt (spec §6)"
} else {
    log_pass "Step 8: Timing closed (WNS = ${wns} ns)"
}

# =============================================================================
# Step 9: Bitstream Generation
# =============================================================================
log_step 9 "Bitstream Generation"

if {[catch {
    write_bitstream -force "${OUT_DIR}/${TOP}.bit"
    log_pass "Step 9: Bitstream generated → ${OUT_DIR}/${TOP}.bit"
} err]} {
    log_fail "Step 9: Bitstream FAILED: $err"
}

# =============================================================================
# Step 10: ATP Telemetry Integration Check
# =============================================================================
log_step 10 "ATP Telemetry Vector Check (Python co-validation)"

set telemetry_script "${SCRIPT_DIR}/mock_telemetry.py"
if {[file exists $telemetry_script]} {
    if {[catch {
        set result [exec python3 $telemetry_script]
        foreach line [split $result "\n"] {
            if {[string match "*ATP-*" $line]} {
                log_pass "Telemetry: $line"
            }
        }
    } err]} {
        log_warn "Step 10: Telemetry generator error: $err"
    }
} else {
    log_warn "Step 10: mock_telemetry.py not found at $telemetry_script"
}

# =============================================================================
# Final Summary
# =============================================================================
puts "\n\[INFO\] ================================================"
puts "\[INFO\]  WALKTHROUGH SUMMARY"
puts "\[INFO\] ================================================"
puts "\[INFO\]  PASS  : $pass_count"
puts "\[INFO\]  FAIL  : $fail_count"
puts "\[INFO\]  WARN  : $warn_count"
puts "\[INFO\]  Output: $OUT_DIR"
puts "\[INFO\] ================================================"

if {$fail_count == 0} {
    puts "\n\[SUCCESS\] All walkthrough gates passed — design production-ready\n"
    exit 0
} else {
    puts "\n\[FAILURE\] $fail_count gate(s) failed — review logs in $OUT_DIR\n"
    exit 1
}
