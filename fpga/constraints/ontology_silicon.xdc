## =============================================================================
## ontology_silicon.xdc  |  Version: 1.0.0
## Target: Xilinx Zynq UltraScale+ (xc7k325t or MPSoC equivalent)
## Clocks: clk_100 (100 MHz AXI/control), clk_300 (300 MHz compute)
## =============================================================================

# ── Primary clocks ────────────────────────────────────────────────────────────
create_clock -name clk_100 -period 10.000 [get_ports clk_100]
create_clock -name clk_300 -period  3.333 [get_ports clk_300]

# ── Clock domain crossing: 100→300 MHz (Groebner / Decomposer) ────────────────
set_clock_groups -asynchronous \
    -group [get_clocks clk_100] \
    -group [get_clocks clk_300]

# ── Input / Output delays (AXI relative to clk_100, 2 ns PCB estimate) ───────
set_input_delay  -clock clk_100 -max 2.0 [get_ports s_axi_*]
set_input_delay  -clock clk_100 -min 0.5 [get_ports s_axi_*]
set_output_delay -clock clk_100 -max 2.0 [get_ports s_axi_*]
set_output_delay -clock clk_100 -min 0.5 [get_ports s_axi_*]

set_input_delay  -clock clk_100 -max 2.0 [get_ports s_axis_*]
set_output_delay -clock clk_100 -max 2.0 [get_ports m_axis_*]

# ── Sensor ADC inputs (relaxed 5 ns — slow ADC register outputs) ─────────────
set_input_delay  -clock clk_100 -max 5.0 [get_ports adc_*]
set_input_delay  -clock clk_100 -max 5.0 [get_ports {vin_valid bus_ok vcap fault_flags}]
set_input_delay  -clock clk_100 -max 5.0 [get_ports pgood_in]

# ── Serial bus I/O (async, use false-path for bit-bang receivers) ─────────────
set_false_path -from [get_ports {pmbus_sda_i pmbus_scl_i i2c_sda_i i2c_scl_i}]
set_false_path -from [get_ports {spi_sclk spi_mosi spi_cs_n}]
set_false_path -from [get_ports uart_rx]
set_false_path -to   [get_ports {pmbus_sda_o pmbus_sda_oe i2c_sda_o i2c_sda_oe}]
set_false_path -to   [get_ports {spi_miso uart_tx}]
set_false_path -from [get_ports gpio_in]
set_false_path -to   [get_ports gpio_out]

# ── IRQ output (combinatorial, relaxed) ──────────────────────────────────────
set_output_delay -clock clk_100 -max 4.0 [get_ports irq_out]

# ── Pblock placement hints (UltraScale+ SLR0) ────────────────────────────────
# Groebner engine → high-Fmax SLR for 300 MHz
create_pblock pb_groebner
add_cells_to_pblock [get_pblocks pb_groebner] [get_cells u_gb]
resize_pblock [get_pblocks pb_groebner] -add {CLOCKREGION_X0Y2:CLOCKREGION_X1Y3}

create_pblock pb_axi
add_cells_to_pblock [get_pblocks pb_axi] [get_cells {u_axi u_ev u_gov u_seq}]
resize_pblock [get_pblocks pb_axi] -add {CLOCKREGION_X0Y0:CLOCKREGION_X1Y1}

# ── Timing exceptions for CAM (distributed RAM timing is relaxed) ─────────────
set_multicycle_path -setup 2 -from [get_cells u_causal/cam*] -to [get_cells u_causal]
set_multicycle_path -hold  1 -from [get_cells u_causal/cam*] -to [get_cells u_causal]

# ── ANOM-026 CDC Constraints (Layer 4)  ───────────────────────────────────────
# 2-FF synchroniser cells must be ASYNC_REG for STA and retiming protection.
# max_delay = 1 clk_100 period (10 ns) — synchroniser input must settle within
# one destination clock period so the 2nd FF samples a stable value.

# CDC-1: decomp_done (clk_300 → clk_100) — req signal 2-FF sync
set_property ASYNC_REG TRUE [get_cells {decomp_done_s1_100_reg decomp_done_s2_100_reg}]
set_max_delay -datapath_only \
    -from [get_cells {decomp_done_req_300_reg}] \
    -to   [get_cells {decomp_done_s1_100_reg}] \
    10.0

# CDC-2: prime_count bus (clk_300 → clk_100) — bus valid only when ack handshake fires,
# so data is stable for at least one clk_100 period before latch.
set_property ASYNC_REG TRUE [get_cells {prime_count_s1_100_reg[*] prime_count_s2_100_reg[*]}]
set_max_delay -datapath_only \
    -from [get_cells {prime_count_reg[*]}] \
    -to   [get_cells {prime_count_s1_100_reg[*]}] \
    10.0

# CDC-3: start signal (clk_100 → clk_300) — ctrl_reg[0] 2-FF sync
set_property ASYNC_REG TRUE [get_cells {start_s1_300_reg start_s2_300_reg}]
set_max_delay -datapath_only \
    -from [get_cells {ctrl_reg_reg[0]}] \
    -to   [get_cells {start_s1_300_reg}] \
    10.0

# ── Bitstream properties ──────────────────────────────────────────────────────
set_property BITSTREAM.CONFIG.SPI_BUSWIDTH 4           [current_design]
set_property BITSTREAM.CONFIG.CONFIGRATE  33           [current_design]
set_property CONFIG_VOLTAGE               1.8          [current_design]
set_property CFGBVS                       GND          [current_design]
