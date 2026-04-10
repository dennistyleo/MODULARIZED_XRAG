// =============================================================================
// Module  : ontology_silicon_module.v  | Version: 1.1.0
// Project : Sovereign Matrix — MCP FPGA Accelerator
// Purpose : Top-level wrapper. Clk 100 MHz (control) + 300 MHz (compute).
// Target  : Xilinx Zynq UltraScale+  |  Ref: AI-PMC Spec G_26260208_V0.1
// =============================================================================
`timescale 1ns/1ps
`default_nettype none

module OntologySiliconModule #(
    parameter BASE_ADDR     = 32'h4000_0000,
    parameter MAX_AXIOMS    = 32,
    parameter MAX_VARIABLES = 16,
    parameter COEFF_WIDTH   = 32,
    parameter POLY_WIDTH    = 256,
    parameter ADC_WIDTH     = 12,
    parameter NUM_DOMAINS   = 6,
    parameter MAX_RAILS     = 8,
    parameter BRAM_DEPTH    = 4096,
    parameter BRAM_WIDTH    = 64,
    parameter EV_FIFO_DEPTH = 1024
)(
    input  wire        clk_100, clk_300, rst_n,
    // AXI4-Lite Slave
    input  wire [31:0] s_axi_awaddr,  input  wire s_axi_awvalid, output wire s_axi_awready,
    input  wire [31:0] s_axi_wdata,   input  wire [3:0] s_axi_wstrb,
    input  wire        s_axi_wvalid,  output wire s_axi_wready,
    output wire [1:0]  s_axi_bresp,   output wire s_axi_bvalid,  input  wire s_axi_bready,
    input  wire [31:0] s_axi_araddr,  input  wire s_axi_arvalid, output wire s_axi_arready,
    output wire [31:0] s_axi_rdata,   output wire [1:0] s_axi_rresp,
    output wire        s_axi_rvalid,  input  wire s_axi_rready,
    // AXI4-Stream
    input  wire [63:0] s_axis_tdata,  input  wire s_axis_tvalid, output wire s_axis_tready,
    output wire [63:0] m_axis_tdata,  output wire m_axis_tvalid, input  wire m_axis_tready,
    // ADC / UPASL sensors
    input  wire [ADC_WIDTH-1:0] adc_temp_hotspot, adc_temp_rate,
    input  wire [ADC_WIDTH-1:0] adc_stress_mech,  adc_stress_rate,
    input  wire [ADC_WIDTH-1:0] adc_bus_voltage,  adc_bus_current, adc_battery_soc,
    input  wire [ADC_WIDTH-1:0] adc_dose_rate,    adc_fill_fraction,
    input  wire [31:0]          telemetry_latency, telemetry_jitter,
    input  wire [NUM_DOMAINS-1:0] evidence_valid_mask,
    // Governance sensors (M-04)
    input  wire        vin_valid, bus_ok,
    input  wire [ADC_WIDTH-1:0] vcap,
    input  wire [31:0] fault_flags,
    input  wire        power_up_req, power_down_req,
    input  wire [7:0]  throttle_req, timing_shift_req,
    // Sequencing (M-05)
    input  wire [MAX_RAILS-1:0] pgood_in,
    // Physical buses
    input  wire pmbus_sda_i, pmbus_scl_i,  output wire pmbus_sda_o, pmbus_sda_oe,
    input  wire i2c_sda_i,   i2c_scl_i,   output wire i2c_sda_o,   i2c_sda_oe,
    input  wire spi_sclk, spi_mosi, spi_cs_n, output wire spi_miso,
    input  wire uart_rx,  output wire uart_tx,
    input  wire [7:0] gpio_in, output wire [7:0] gpio_out,
    // Interrupt
    output wire irq_out
);
    // ── Internal wires ────────────────────────────────────────────────────────
    wire [31:0] ctrl_reg, prime_count, decomp_error, semantic_dist;
    wire [31:0] axiom_base_addr, result_base_addr, target_addr;
    wire [31:0] t_max, t_dot_max, h_t_min, sigma_max, sigma_dot_max, d_m_max;
    wire [31:0] v_min, i_dot_max, soc_min, p_margin_min;
    wire [31:0] d_max, d_dot_max, r_see_max, tau_s_max, pi_max, l_max, j_max;
    wire [31:0] gov_profile_id, gov_timeout_ms, gov_thresholds, gov_hysteresis, gov_allowed_actions;
    wire [31:0] global_hazard, stability_index, invariant_violations, gov_fault_cause;
    wire [2:0]  gov_state; wire [1:0] upasl_decision;
    wire [2:0]  domain_status [0:NUM_DOMAINS-1];
    wire [31:0] limit_fraction [0:NUM_DOMAINS-1];
    // Flatten domain_status for AXI port (Verilog-2001: no unpacked in port list)
    wire [17:0] domain_status_flat;
    assign domain_status_flat = {domain_status[5], domain_status[4], domain_status[3],
                                  domain_status[2], domain_status[1], domain_status[0]};
    wire        decomp_done, gb_done, gb_coeff_valid, invariant_irq;
    wire [COEFF_WIDTH-1:0] gb_basis_coeff;
    wire [POLY_WIDTH-1:0]  prime_tdata; wire prime_tvalid, prime_tready;
    wire        gov_ev_valid, seq_ev_valid;
    wire [255:0] gov_ev_data, seq_ev_data;
    wire [9:0]  ev_fifo_count; wire ev_empty, ev_full;
    wire        seq_start_cmd, seq_stop_cmd, seq_hold_cmd, seq_resume_cmd;
    wire [2:0]  seq_state; wire [7:0] current_seq_step;
    wire [7:0]  atp_test_id; wire atp_inject_cmd, atp_check_cmd;
    wire        atp_pass; wire [31:0] atp_fail_reason; wire atp_busy;
    wire        inject_vin_invalid, inject_pgood_timeout;
    wire [31:0] inject_timeout_ms;
    wire [63:0] ev_stream_tdata; wire ev_stream_tvalid;
    wire [MAX_RAILS-1:0] en_out;
    wire [BRAM_WIDTH-1:0] bram_din_a;
    wire        ml_capture; wire [511:0] feature_vector; wire feat_valid;
    wire        tel_data_valid; wire [31:0] tel_pmbus_data;
    wire [63:0] mcp_payload; wire mcp_valid; wire [7:0] mcp_method_id;
    reg  [63:0] runtime_cycles;

    // Effective VIN / fault considering ATP injection
    wire eff_vin_valid   = vin_valid   & ~inject_vin_invalid;
    wire eff_pgood_fault = inject_pgood_timeout;

    always @(posedge clk_100 or negedge rst_n)
        if (!rst_n) runtime_cycles <= 0; else runtime_cycles <= runtime_cycles + 1;

    wire any_ev_valid = gov_ev_valid | seq_ev_valid;
    wire [255:0] any_ev_data = gov_ev_valid ? gov_ev_data : seq_ev_data;
    wire gov_ev_ready = ~ev_full;
    wire seq_ev_ready = ~ev_full & ~gov_ev_valid;

    // ── Submodule instantiations ──────────────────────────────────────────────
    AXI_SlaveInterface   #(.BASE_ADDR(BASE_ADDR)) u_axi (
        .clk(clk_100), .rst_n(rst_n),
        .s_axi_awaddr(s_axi_awaddr), .s_axi_awvalid(s_axi_awvalid), .s_axi_awready(s_axi_awready),
        .s_axi_wdata(s_axi_wdata), .s_axi_wstrb(s_axi_wstrb), .s_axi_wvalid(s_axi_wvalid), .s_axi_wready(s_axi_wready),
        .s_axi_bresp(s_axi_bresp), .s_axi_bvalid(s_axi_bvalid), .s_axi_bready(s_axi_bready),
        .s_axi_araddr(s_axi_araddr), .s_axi_arvalid(s_axi_arvalid), .s_axi_arready(s_axi_arready),
        .s_axi_rdata(s_axi_rdata), .s_axi_rresp(s_axi_rresp), .s_axi_rvalid(s_axi_rvalid), .s_axi_rready(s_axi_rready),
        .s_axis_tdata(s_axis_tdata), .s_axis_tvalid(s_axis_tvalid), .s_axis_tready(s_axis_tready),
        .m_axis_tdata(m_axis_tdata), .m_axis_tvalid(m_axis_tvalid), .m_axis_tready(m_axis_tready),
        .control_reg(ctrl_reg), .prime_count(prime_count), .semantic_dist(semantic_dist),
        .runtime_cycles(runtime_cycles), .error_code(decomp_error),
        .axiom_base_addr(axiom_base_addr), .result_base_addr(result_base_addr), .target_addr(target_addr),
        .t_max(t_max), .t_dot_max(t_dot_max), .h_t_min(h_t_min),
        .sigma_max(sigma_max), .sigma_dot_max(sigma_dot_max), .d_m_max(d_m_max),
        .v_min(v_min), .i_dot_max(i_dot_max), .soc_min(soc_min), .p_margin_min(p_margin_min),
        .d_max(d_max), .d_dot_max(d_dot_max), .r_see_max(r_see_max),
        .tau_s_max(tau_s_max), .pi_max(pi_max), .l_max(l_max), .j_max(j_max),
        .global_hazard(global_hazard), .stability_index(stability_index), .upasl_decision(upasl_decision),
        .invariant_violations(invariant_violations),
        .gov_profile_id(gov_profile_id), .gov_timeout_ms(gov_timeout_ms), .gov_thresholds(gov_thresholds),
        .gov_hysteresis(gov_hysteresis), .gov_allowed_actions(gov_allowed_actions),
        .gov_state(gov_state), .gov_fault_cause(gov_fault_cause),
        .seq_state(seq_state), .current_seq_step(current_seq_step),
        .seq_start_cmd(seq_start_cmd), .seq_stop_cmd(seq_stop_cmd),
        .seq_hold_cmd(seq_hold_cmd), .seq_resume_cmd(seq_resume_cmd),
        .ev_fifo_count(ev_fifo_count), .atp_test_id(atp_test_id),
        .atp_inject_cmd(atp_inject_cmd), .atp_check_cmd(atp_check_cmd),
        .atp_pass(atp_pass), .atp_fail_reason(atp_fail_reason),
        .feature_vector_lsw(feature_vector[63:0]), .ml_capture(ml_capture),
        .domain_status_flat(domain_status_flat),
        .decomp_done(decomp_done)
    );
    PrimaryDecomposer    #(.MAX_AXIOMS(MAX_AXIOMS),.MAX_VARIABLES(MAX_VARIABLES),.COEFF_WIDTH(COEFF_WIDTH),.POLY_WIDTH(POLY_WIDTH)) u_decomp (
        .clk(clk_300), .rst_n(rst_n), .start(ctrl_reg[0]),
        .done(decomp_done), .prime_count(prime_count), .error_code(decomp_error),
        .axiom_base_addr(axiom_base_addr), .target_addr(target_addr), .result_base_addr(result_base_addr),
        .s_axis_coeff_tdata(s_axis_tdata[COEFF_WIDTH-1:0]), .s_axis_coeff_tvalid(s_axis_tvalid), .s_axis_coeff_tready(),
        .m_axis_prime_tdata(prime_tdata), .m_axis_prime_tvalid(prime_tvalid), .m_axis_prime_tready(prime_tready),
        .gb_coeff_in(gb_basis_coeff), .gb_coeff_valid(gb_coeff_valid)
    );
    GroebnerBasisEngine  #(.MAX_POLYS(MAX_AXIOMS),.MAX_VARS(MAX_VARIABLES),.COEFF_W(COEFF_WIDTH)) u_gb (
        .clk(clk_300), .rst_n(rst_n), .start(ctrl_reg[0]),
        .done(gb_done), .coeff_out(gb_basis_coeff), .coeff_valid(gb_coeff_valid)
    );
    SemanticDistanceEngine #(.COEFF_WIDTH(COEFF_WIDTH)) u_sem (
        .clk(clk_100), .rst_n(rst_n), .axiom_a(s_axis_tdata[31:0]), .axiom_b(target_addr),
        .dist_valid_in(s_axis_tvalid), .semantic_dist(semantic_dist)
    );
    CausalInvariantTracker #(.NUM_INVARIANTS(MAX_AXIOMS)) u_causal (
        .clk(clk_100), .rst_n(rst_n), .axiom_id_in(s_axis_tdata[7:0]), .axiom_valid(s_axis_tvalid),
        .violation_count(invariant_violations), .irq_out(invariant_irq)
    );
    UPASLDomainEngine    #(.NUM_DOMAINS(NUM_DOMAINS),.ADC_WIDTH(ADC_WIDTH)) u_upasl (
        .clk(clk_100), .rst_n(rst_n),
        .temp_hotspot(adc_temp_hotspot), .temp_rate(adc_temp_rate),
        .stress_mech(adc_stress_mech), .stress_rate(adc_stress_rate),
        .bus_voltage(adc_bus_voltage), .bus_current(adc_bus_current), .battery_soc(adc_battery_soc),
        .dose_rate(adc_dose_rate), .fill_fraction(adc_fill_fraction),
        .loop_latency(telemetry_latency), .jitter(telemetry_jitter),
        .evidence_valid(evidence_valid_mask),
        .t_max(t_max), .t_dot_max(t_dot_max), .h_t_min(h_t_min),
        .sigma_max(sigma_max), .sigma_dot_max(sigma_dot_max), .d_m_max(d_m_max),
        .v_min(v_min), .i_dot_max(i_dot_max), .soc_min(soc_min), .p_margin_min(p_margin_min),
        .d_max(d_max), .d_dot_max(d_dot_max), .r_see_max(r_see_max),
        .tau_s_max(tau_s_max), .pi_max(pi_max), .l_max(l_max), .j_max(j_max),
        .domain_status(domain_status), .limit_fraction(limit_fraction),
        .global_hazard(global_hazard), .stability_index(stability_index), .decision(upasl_decision)
    );
    TelemetryAggregator  #(.FIFO_DEPTH(16)) u_tel (
        .clk(clk_100), .rst_n(rst_n),
        .pmbus_sda_i(pmbus_sda_i), .pmbus_scl_i(pmbus_scl_i), .pmbus_sda_o(pmbus_sda_o), .pmbus_sda_oe(pmbus_sda_oe),
        .i2c_sda_i(i2c_sda_i), .i2c_scl_i(i2c_scl_i), .i2c_sda_o(i2c_sda_o), .i2c_sda_oe(i2c_sda_oe),
        .spi_sclk(spi_sclk), .spi_mosi(spi_mosi), .spi_miso(spi_miso), .spi_cs_n(spi_cs_n),
        .uart_rx(uart_rx), .uart_tx(uart_tx), .gpio_in(gpio_in), .gpio_out(gpio_out),
        .pmbus_data(tel_pmbus_data), .i2c_data(), .spi_data(), .uart_byte(), .data_valid(tel_data_valid)
    );
    BRAMAxiomStore       #(.DEPTH(BRAM_DEPTH),.WIDTH(BRAM_WIDTH)) u_bram (
        .clk(clk_100),
        .addr_a(axiom_base_addr[11:0]), .din_a(bram_din_a), .dout_a(), .we_a(decomp_done), .en_a(1'b1),
        .addr_b(result_base_addr[11:0]), .dout_b(), .en_b(1'b1)
    );
    MCPJsonRpcDecoder    u_mcp (
        .clk(clk_100), .rst_n(rst_n),
        .s_axis_tdata(s_axis_tdata), .s_axis_tvalid(s_axis_tvalid), .s_axis_tready(),
        .payload_out(mcp_payload), .payload_valid(mcp_valid), .method_id(mcp_method_id)
    );
    GovernanceFSM        #(.SENSOR_WIDTH(ADC_WIDTH)) u_gov (
        .clk(clk_100), .rst_n(rst_n),
        .profile_id(gov_profile_id), .timeouts_ms(gov_timeout_ms),
        .thresholds(gov_thresholds), .hysteresis(gov_hysteresis), .allowed_actions(gov_allowed_actions),
        .vin_valid(eff_vin_valid), .bus_ok(bus_ok), .vcap(vcap),
        .temp(adc_temp_hotspot), .fault_flags(fault_flags),
        .power_up_req(power_up_req), .power_down_req(power_down_req),
        .throttle_req(throttle_req), .timing_shift_req(timing_shift_req),
        .evidence_valid(gov_ev_valid), .evidence_data(gov_ev_data), .evidence_ready(gov_ev_ready),
        .gov_state(gov_state), .fault_cause(gov_fault_cause)
    );
    SequencingEngine     #(.MAX_STEPS(16),.MAX_RAILS(MAX_RAILS)) u_seq (
        .clk(clk_100), .rst_n(rst_n),
        .vin_valid(eff_vin_valid), .bus_ok(bus_ok), .pgood_in(pgood_in), .fault_flags(fault_flags),
        .seq_start(seq_start_cmd), .seq_stop(seq_stop_cmd), .seq_hold(seq_hold_cmd), .seq_resume(seq_resume_cmd),
        .en_out(en_out), .reset_out(),
        .evidence_valid(seq_ev_valid), .evidence_data(seq_ev_data), .evidence_ready(seq_ev_ready),
        .seq_state(seq_state), .current_step(current_seq_step), .timeout_count()
    );
    EvidenceEncoder      #(.FIFO_DEPTH(EV_FIFO_DEPTH)) u_ev (
        .clk(clk_100), .rst_n(rst_n),
        .ev_valid(any_ev_valid), .ev_data(any_ev_data), .ev_ready(),
        .ev_count(ev_fifo_count), .ev_empty(ev_empty), .ev_full(ev_full),
        .m_axis_tdata(ev_stream_tdata), .m_axis_tvalid(ev_stream_tvalid), .m_axis_tready(m_axis_tready)
    );
    ATPHardware          #(.NUM_ATP_TESTS(8)) u_atp (
        .clk(clk_100), .rst_n(rst_n),
        .atp_test_id(atp_test_id), .atp_inject(atp_inject_cmd), .atp_check(atp_check_cmd),
        .inject_vin_invalid(inject_vin_invalid), .inject_pgood_timeout(inject_pgood_timeout),
        .inject_timeout_ms(inject_timeout_ms),
        .ev_has_seq_start(seq_state==3'd1), .ev_has_seq_blocked(~eff_vin_valid & power_up_req),
        .ev_has_seq_done(seq_state==3'd4), .ev_has_seq_timeout(seq_state==3'd5),
        .atp_pass(atp_pass), .atp_fail_reason(atp_fail_reason), .atp_busy(atp_busy)
    );
    FeatureExtractor     #(.ADC_WIDTH(ADC_WIDTH)) u_feat (
        .clk(clk_100), .rst_n(rst_n),
        // Flat packed buses: {lane[7], lane[6], ... lane[0]}
        .vout_flat({adc_bus_voltage, {7{12'd0}}}),
        .iout_flat({adc_bus_current, {7{12'd0}}}),
        .temp_flat({adc_temp_rate, adc_temp_hotspot, {2{12'd0}}}),
        .eff_flat(128'd0),    // not wired in this build
        .rip_flat(128'd0),
        .droop_mv(gov_fault_cause[15:0]), .overshoot_mv(16'd0), .settling_us(16'd0),
        .capture(ml_capture),
        .feature_vector(feature_vector), .feature_valid(feat_valid), .feature_ready(1'b1)
    );

    assign bram_din_a  = {32'd0, prime_count};
    assign prime_tready = m_axis_tready & ~ev_stream_tvalid;
    assign irq_out = (ctrl_reg[8]  & decomp_done)             |
                     (ctrl_reg[9]  & invariant_irq)            |
                     (ctrl_reg[10] & (upasl_decision==2'b00))  |
                     (ctrl_reg[11] & (gov_state==3'd5))        |
                     (ctrl_reg[12] & (seq_state ==3'd5));

endmodule
`default_nettype wire
