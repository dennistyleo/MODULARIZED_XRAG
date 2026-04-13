// =============================================================================
// Module  : upasl_domain_engine.v  | Version: 1.1.0
// Purpose : UPASL 6-Domain Engine (Thermal / Mechanical / EPS / Radiation /
//           Fluid / Information). Evaluates SAT/VIOL/UND per domain every clock.
//           All arithmetic in Q16.16 fixed-point (65536 = 1.0).
// Ref     : UPASL Specification Sections 5–11
// =============================================================================
`timescale 1ns/1ps
`default_nettype none

module UPASLDomainEngine #(
    parameter NUM_DOMAINS = 6,
    parameter ADC_WIDTH   = 12
)(
    input  wire clk, rst_n,
    // ── Telemetry inputs ──────────────────────────────────────────────────────
    input  wire [ADC_WIDTH-1:0] temp_hotspot, temp_rate,
    input  wire [ADC_WIDTH-1:0] stress_mech, stress_rate,
    input  wire [ADC_WIDTH-1:0] bus_voltage, bus_current, battery_soc,
    input  wire [ADC_WIDTH-1:0] dose_rate, fill_fraction,
    input  wire [31:0]          loop_latency, jitter,
    input  wire [NUM_DOMAINS-1:0] evidence_valid,
    // ── Threshold configuration (from AXI register file) ─────────────────────
    input  wire [31:0] t_max, t_dot_max, h_t_min,
    input  wire [31:0] sigma_max, sigma_dot_max, d_m_max,
    input  wire [31:0] v_min, i_dot_max, soc_min, p_margin_min,
    input  wire [31:0] d_max, d_dot_max, r_see_max,
    input  wire [31:0] tau_s_max, pi_max, l_max, j_max,
    // ── Outputs ───────────────────────────────────────────────────────────────
    // ANOM-001/002 FIX: Flattened to packed buses (Verilog-2001 synthesis compliant)
    // domain_status_flat[d*3+2 -: 3] = domain_status[d]
    // limit_fraction_flat[d*32+31 -: 32] = limit_fraction[d]
    output wire [NUM_DOMAINS*3-1:0]  domain_status_flat,
    output wire [NUM_DOMAINS*32-1:0] limit_fraction_flat,
    output reg  [31:0] global_hazard,
    output reg  [31:0] stability_index,
    output reg  [1:0]  decision
);
    localparam SAT  = 3'b001;
    localparam VIOL = 3'b010;
    localparam UND  = 3'b100;

    localparam DEC_REFUSE = 2'b00;
    localparam DEC_LIMIT  = 2'b01;
    localparam DEC_ALLOW  = 2'b10;

    // ── Safe division helper (returns Q16.16; avoids div-by-zero) ─────────────
    function [31:0] safe_div_q1616;
        input [31:0] num, den;
    begin
        safe_div_q1616 = (den == 0) ? 32'hFFFF_FFFF :
                         (num >= den) ? 32'h0001_0000 :
                         (num * 32'h0001_0000) / den;
    end
    endfunction

    // ── Domain combinatorial evaluation ──────────────────────────────────────
    // Domain 0: Thermal (UPASL §5)
    wire th_sat  = (temp_hotspot <= t_max[ADC_WIDTH-1:0]) &&
                   (temp_rate    <= t_dot_max[ADC_WIDTH-1:0]) &&
                   ((t_max[ADC_WIDTH-1:0] - temp_hotspot) >= h_t_min[ADC_WIDTH-1:0]);
    wire th_und  = ~evidence_valid[0];
    wire th_viol = ~th_sat && ~th_und;

    // Domain 1: Mechanical (UPASL §6)
    wire mc_sat  = (stress_mech <= sigma_max[ADC_WIDTH-1:0]) &&
                   (stress_rate <= sigma_dot_max[ADC_WIDTH-1:0]);
    wire mc_und  = ~evidence_valid[1];
    wire mc_viol = ~mc_sat && ~mc_und;

    // Domain 2: EPS / Power (UPASL §7)
    wire ep_sat  = (bus_voltage  >= v_min[ADC_WIDTH-1:0]) &&
                   (bus_current  <= i_dot_max[ADC_WIDTH-1:0]) &&
                   (battery_soc  >= soc_min[ADC_WIDTH-1:0]);
    wire ep_und  = ~evidence_valid[2];
    wire ep_viol = ~ep_sat && ~ep_und;

    // Domain 3: Radiation (UPASL §8)
    wire rd_sat  = (dose_rate <= d_max[ADC_WIDTH-1:0]);
    wire rd_und  = ~evidence_valid[3];
    wire rd_viol = ~rd_sat && ~rd_und;

    // Domain 4: Fluid (UPASL §9)
    wire fl_sat  = (fill_fraction <= tau_s_max[ADC_WIDTH-1:0]);
    wire fl_und  = ~evidence_valid[4];
    wire fl_viol = ~fl_sat && ~fl_und;

    // Domain 5: Information (UPASL §10)
    wire in_sat  = (loop_latency <= l_max) && (jitter <= j_max);
    wire in_und  = ~evidence_valid[5];
    wire in_viol = ~in_sat && ~in_und;

    // Global violation / undetermined flags
    wire any_viol = th_viol | mc_viol | ep_viol | rd_viol | fl_viol | in_viol;
    wire any_und  = th_und  | mc_und  | ep_und  | rd_und  | fl_und  | in_und;

    // ── Internal registers — module scope (ANOM-001/002 FIX) ─────────────────
    reg [2:0]  ds [0:NUM_DOMAINS-1];
    reg [31:0] lf [0:NUM_DOMAINS-1];

    // ── Sequential register update ────────────────────────────────────────────
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            global_hazard   <= 32'd0;
            stability_index <= 32'd0;
            decision        <= DEC_REFUSE;
        end else begin
            // Domain status — written to module-scope ds[]
            ds[0] <= th_und ? UND : th_viol ? VIOL : SAT;
            ds[1] <= mc_und ? UND : mc_viol ? VIOL : SAT;
            ds[2] <= ep_und ? UND : ep_viol ? VIOL : SAT;
            ds[3] <= rd_und ? UND : rd_viol ? VIOL : SAT;
            ds[4] <= fl_und ? UND : fl_viol ? VIOL : SAT;
            ds[5] <= in_und ? UND : in_viol ? VIOL : SAT;

            // Limit fractions — written to module-scope lf[]
            lf[0] <= safe_div_q1616(
                {20'd0, t_max[ADC_WIDTH-1:0] - temp_hotspot},
                {20'd0, t_max[ADC_WIDTH-1:0] - h_t_min[ADC_WIDTH-1:0]});
            lf[1] <= safe_div_q1616(
                {20'd0, sigma_max[ADC_WIDTH-1:0] - stress_mech},
                {20'd0, sigma_max[ADC_WIDTH-1:0]});
            lf[2] <= safe_div_q1616(
                {20'd0, bus_voltage - v_min[ADC_WIDTH-1:0]},
                {20'd0, {ADC_WIDTH{1'b1}} - v_min[ADC_WIDTH-1:0]});
            lf[3] <= safe_div_q1616(
                {20'd0, d_max[ADC_WIDTH-1:0] - dose_rate},
                {20'd0, d_max[ADC_WIDTH-1:0]});
            lf[4] <= safe_div_q1616(
                {20'd0, tau_s_max[ADC_WIDTH-1:0] - fill_fraction},
                {20'd0, tau_s_max[ADC_WIDTH-1:0]});
            lf[5] <= safe_div_q1616(
                l_max - loop_latency, l_max);

            // Stability index = mean of limit fractions (UPASL §11)
            stability_index <= (lf[0] + lf[1] + lf[2] + lf[3] + lf[4] + lf[5]) / 6;

            // Global hazard = inverse of stability
            global_hazard <= 32'h0001_0000 - stability_index;

            // Decision (UPASL §3.2)
            decision <= (any_viol | any_und) ? DEC_REFUSE :
                        (stability_index > 32'h0000_8000) ? DEC_ALLOW : DEC_LIMIT;
        end
    end

    // ── Flatten internal arrays to output ports (NAMED generate block) ─────────
    genvar g;
    generate
        for (g = 0; g < NUM_DOMAINS; g = g + 1) begin : flatten_outputs
            assign domain_status_flat[g*3+2 -: 3]      = ds[g];
            assign limit_fraction_flat[g*32+31 -: 32]  = lf[g];
        end
    endgenerate

endmodule
`default_nettype wire
