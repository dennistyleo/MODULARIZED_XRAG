## =============================================================================
## generate_bitstream.tcl  |  Version: 1.0.0
## Vivado bitstream generation
## Usage: vivado -mode batch -source scripts/generate_bitstream.tcl
## =============================================================================

set TOP     "OntologySiliconModule"
set OUT_DIR "[file normalize [file dirname [info script]]/../output]"
set IMP_DCP "${OUT_DIR}/impl/${TOP}_impl.dcp"
set BIT_DIR "${OUT_DIR}/bitstream"

file mkdir $BIT_DIR

open_checkpoint $IMP_DCP

# ── Bitstream options ─────────────────────────────────────────────────────────
set_property BITSTREAM.GENERAL.COMPRESS TRUE [current_design]

# ── Generate ──────────────────────────────────────────────────────────────────
write_bitstream -force -bin_file ${BIT_DIR}/${TOP}.bit

# ── Device image for Zynq MPSoC (BOOT.BIN compatible) ────────────────────────
write_device_image -format BIN -file ${BIT_DIR}/${TOP}_device.bin \
    -force -verbose \
    2>/dev/null || puts "Note: write_device_image requires Versal/MPSoC device"

# ── Debug probes (optional ILA) ───────────────────────────────────────────────
if {[llength [get_debug_cores]] > 0} {
    write_debug_probes -force ${BIT_DIR}/${TOP}.ltx
    puts "  ILA probes written → ${BIT_DIR}/${TOP}.ltx"
}

puts "Bitstream generated → ${BIT_DIR}/${TOP}.bit"
