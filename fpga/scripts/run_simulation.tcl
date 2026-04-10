## =============================================================================
## run_simulation.tcl  |  Version: 1.0.0
## Run AI-PMC Governance full test suite in Vivado Simulator (batch mode)
## Usage: vivado -mode batch -source fpga/scripts/run_simulation.tcl
## =============================================================================

set PART    "xczu7ev-ffvc1156-2-e"
set RTL_DIR "[file normalize [file dirname [info script]]/../rtl]"
set SIM_DIR "[file normalize [file dirname [info script]]/../sim]"
set WRK_DIR "[file normalize [file dirname [info script]]/../output/sim]"

file mkdir $WRK_DIR

# Create a temporary in-memory project (non-persistent)
create_project -in_memory -part $PART

# ── Read RTL sources (dependency order, -sv superset) ─────────────────────────
set rtl_files [list \
    bram_axiom_store.v        \
    causal_invariant_tracker.v \
    evidence_encoder.v        \
    groebner_basis_engine.v   \
    governance_fsm.v          \
    sequencing_engine.v       \
    atp_hardware.v            \
    feature_extractor.v       \
    semantic_distance_engine.v \
    upasl_domain_engine.v     \
    primary_decomposer.v      \
    telemetry_aggregator.v    \
    mcp_jsonrpc_decoder.v     \
    axi_slave_interface.v     \
    ontology_silicon_module.v \
]

foreach f $rtl_files {
    set fp "${RTL_DIR}/${f}"
    if {![file exists $fp]} {
        puts "ERROR: RTL file missing: $fp"
        exit 1
    }
    read_verilog -sv $fp
    puts "  [OK] $f"
}

# ── Read testbenches ──────────────────────────────────────────────────────────
set sim_files [list \
    tb_governance_top.v \
    governance_tb.v     \
    tb_upasl_domain.v   \
    tb_ontology_silicon_module.v \
]

foreach f $sim_files {
    set fp "${SIM_DIR}/${f}"
    if {[file exists $fp]} {
        read_verilog -sv $fp
        puts "  [OK] sim/$f"
    }
}

# ── Elaborate → compile ───────────────────────────────────────────────────────
# Primary: top-level governance suite
set_property top tb_governance_top [current_fileset -simset]
set_property top_lib xil_defaultlib [current_fileset -simset]

# Compile
launch_simulation -simset [current_fileset -simset] -mode behavioral

# ── Run simulation ────────────────────────────────────────────────────────────
# tb_governance_top runs all 22 tests and calls $finish
run -all

# ── Collect pass/fail from log ────────────────────────────────────────────────
# Vivado writes transcript to vivado.log; parse it for summary
set log_file "[file normalize ./vivado.log]"
set fail_count 0
set pass_count 0

if {[file exists $log_file]} {
    set fh [open $log_file r]
    while {[gets $fh line] >= 0} {
        if {[string match "*\[PASS\]*" $line]} { incr pass_count }
        if {[string match "*\[FAIL\]*" $line]} { incr fail_count }
    }
    close $fh
}

puts "\n========================================="
puts "SIMULATION RESULT: $pass_count PASS  $fail_count FAIL"
puts "========================================="

if {$fail_count > 0} {
    puts "SIMULATION FAILED — check vivado.log for details"
    exit 1
} else {
    puts "SIMULATION PASSED"
    exit 0
}
