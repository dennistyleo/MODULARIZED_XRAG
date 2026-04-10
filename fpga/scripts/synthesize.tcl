## =============================================================================
## synthesize.tcl  |  Version: 1.1.0
## Vivado synthesis script for OntologySiliconModule
## Usage: vivado -mode batch -source scripts/synthesize.tcl
##
## IMPORTANT: All RTL files are read with -sv (SystemVerilog superset) because:
##   - Tasks inside always blocks (governance_fsm, sequencing_engine) are SV
##   - Unpacked-array ports use Verilog-2001 flat buses after v1.1 fix
##   - Vivado 2021.2+ supports SV synthesis natively; -sv is safe for all files
## =============================================================================

set PART    "xczu7ev-ffvc1156-2-e"
set TOP     "OntologySiliconModule"
set RTL_DIR "[file normalize [file dirname [info script]]/../rtl]"
set CON_DIR "[file normalize [file dirname [info script]]/../constraints]"
set OUT_DIR "[file normalize [file dirname [info script]]/../output/synth]"

file mkdir $OUT_DIR

# Create in-memory project
create_project -in_memory -part $PART

# ── Read all RTL sources with SystemVerilog superset mode ─────────────────────
# Order: submodules first, top-level last (avoids forward-reference warnings)
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
    set fpath "${RTL_DIR}/${f}"
    if {![file exists $fpath]} {
        puts "ERROR: RTL file not found: $fpath"
        exit 1
    }
    read_verilog -sv $fpath
    puts "  [OK] RTL: $f"
}

# ── Read constraints ──────────────────────────────────────────────────────────
read_xdc ${CON_DIR}/ontology_silicon.xdc

# ── Run synthesis ─────────────────────────────────────────────────────────────
synth_design \
    -top          $TOP    \
    -part         $PART   \
    -flatten_hierarchy rebuilt \
    -gated_clock_conversion off \
    -bufg          12      \
    -fanout_limit  10000   \
    -directive     PerformanceOptimized

# ── Verify top-level was elaborated ──────────────────────────────────────────
set top_cells [get_cells -hierarchical -filter {PRIMITIVE_LEVEL == "MACRO"}]
puts "INFO: Top-level cell count: [llength $top_cells]"

# ── Reports ───────────────────────────────────────────────────────────────────
report_utilization          -file ${OUT_DIR}/utilization_synth.rpt
report_timing_summary -max_paths 10 -file ${OUT_DIR}/timing_synth.rpt
report_clock_networks       -file ${OUT_DIR}/clocks_synth.rpt
report_drc                  -file ${OUT_DIR}/drc_synth.rpt
report_methodology          -file ${OUT_DIR}/methodology_synth.rpt

# ── Write checkpoint ──────────────────────────────────────────────────────────
write_checkpoint -force ${OUT_DIR}/${TOP}_synth.dcp
puts "Synthesis complete → ${OUT_DIR}/${TOP}_synth.dcp"
