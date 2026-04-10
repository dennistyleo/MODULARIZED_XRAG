## =============================================================================
## synthesize.tcl  |  Version: 1.0.0
## Vivado synthesis script for OntologySiliconModule
## Usage: vivado -mode batch -source scripts/synthesize.tcl
## =============================================================================

set PART    "xczu7ev-ffvc1156-2-e"
set TOP     "OntologySiliconModule"
set RTL_DIR "[file normalize [file dirname [info script]]/../rtl]"
set SIM_DIR "[file normalize [file dirname [info script]]/../sim]"
set CON_DIR "[file normalize [file dirname [info script]]/../constraints]"
set OUT_DIR "[file normalize [file dirname [info script]]/../output/synth]"

file mkdir $OUT_DIR

# Create in-memory project
create_project -in_memory -part $PART

# ── Read all RTL sources ──────────────────────────────────────────────────────
foreach f [glob -nocomplain ${RTL_DIR}/*.v] {
    read_verilog -sv $f
    puts "  RTL: $f"
}

# ── Read constraints ──────────────────────────────────────────────────────────
read_xdc ${CON_DIR}/ontology_silicon.xdc

# ── Synthesis settings ────────────────────────────────────────────────────────
synth_design \
    -top          $TOP    \
    -part         $PART   \
    -flatten_hierarchy rebuilt \
    -gated_clock_conversion off \
    -bufg          12      \
    -fanout_limit  10000   \
    -directive     PerformanceOptimized

# ── Reports ───────────────────────────────────────────────────────────────────
report_utilization          -file ${OUT_DIR}/utilization_synth.rpt
report_timing_summary -max_paths 10 -file ${OUT_DIR}/timing_synth.rpt
report_clock_networks       -file ${OUT_DIR}/clocks_synth.rpt
report_drc                  -file ${OUT_DIR}/drc_synth.rpt

# ── Write checkpoint ──────────────────────────────────────────────────────────
write_checkpoint -force ${OUT_DIR}/${TOP}_synth.dcp
puts "Synthesis complete → ${OUT_DIR}/${TOP}_synth.dcp"
