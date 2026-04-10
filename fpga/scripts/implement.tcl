## =============================================================================
## implement.tcl  |  Version: 1.0.0
## Vivado implementation script (place & route)
## Usage: vivado -mode batch -source scripts/implement.tcl
## =============================================================================

set TOP     "OntologySiliconModule"
set OUT_DIR "[file normalize [file dirname [info script]]/../output]"
set SYN_DCP "${OUT_DIR}/synth/${TOP}_synth.dcp"
set IMP_DIR "${OUT_DIR}/impl"

file mkdir $IMP_DIR

open_checkpoint $SYN_DCP

# ── Optimise netlist before P&R ───────────────────────────────────────────────
opt_design -directive ExploreWithRemap

# ── Place ─────────────────────────────────────────────────────────────────────
place_design -directive ExtraTimingOpt
phys_opt_design -directive AggressiveExplore

# ── Route ─────────────────────────────────────────────────────────────────────
route_design -directive AggressiveExplore
phys_opt_design -directive AggressiveExplore

# ── Reports ───────────────────────────────────────────────────────────────────
report_utilization    -file ${IMP_DIR}/utilization_impl.rpt
report_timing_summary -max_paths 20 -file ${IMP_DIR}/timing_impl.rpt -warn_on_violation
report_route_status   -file ${IMP_DIR}/route_status.rpt
report_power          -file ${IMP_DIR}/power_impl.rpt

# ── Checkpoint ────────────────────────────────────────────────────────────────
write_checkpoint -force ${IMP_DIR}/${TOP}_impl.dcp
puts "Implementation complete → ${IMP_DIR}/${TOP}_impl.dcp"
