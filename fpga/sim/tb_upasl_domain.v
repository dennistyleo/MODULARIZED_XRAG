// =============================================================================
// Testbench : tb_upasl_domain.v  | Version: 1.0.0
// Purpose   : Verifies all 6 UPASL domain evaluations, limit fractions,
//             stability index, and decision output.
// =============================================================================
`timescale 1ns/1ps

module tb_upasl_domain;
    reg clk, rst_n;
    initial clk = 0;
    always #5 clk = ~clk;

    // Threshold defaults (matching UPASL spec typical values)
    reg [31:0] t_max,t_dot_max,h_t_min,sigma_max,sigma_dot_max,d_m_max;
    reg [31:0] v_min,i_dot_max,soc_min,p_margin_min;
    reg [31:0] d_max,d_dot_max,r_see_max,tau_s_max,pi_max,l_max,j_max;

    reg [11:0] temp_hotspot, temp_rate, stress_mech, stress_rate;
    reg [11:0] bus_voltage, bus_current, battery_soc, dose_rate, fill_fraction;
    reg [31:0] loop_latency, jitter;
    reg [5:0]  evidence_valid;

    wire [2:0]  domain_status [0:5];
    wire [31:0] limit_fraction [0:5];
    wire [31:0] global_hazard, stability_index;
    wire [1:0]  decision;

    UPASLDomainEngine #(.NUM_DOMAINS(6), .ADC_WIDTH(12)) dut (
        .clk(clk), .rst_n(rst_n),
        .temp_hotspot(temp_hotspot), .temp_rate(temp_rate),
        .stress_mech(stress_mech), .stress_rate(stress_rate),
        .bus_voltage(bus_voltage), .bus_current(bus_current), .battery_soc(battery_soc),
        .dose_rate(dose_rate), .fill_fraction(fill_fraction),
        .loop_latency(loop_latency), .jitter(jitter),
        .evidence_valid(evidence_valid),
        .t_max(t_max), .t_dot_max(t_dot_max), .h_t_min(h_t_min),
        .sigma_max(sigma_max), .sigma_dot_max(sigma_dot_max), .d_m_max(d_m_max),
        .v_min(v_min), .i_dot_max(i_dot_max), .soc_min(soc_min), .p_margin_min(p_margin_min),
        .d_max(d_max), .d_dot_max(d_dot_max), .r_see_max(r_see_max),
        .tau_s_max(tau_s_max), .pi_max(pi_max), .l_max(l_max), .j_max(j_max),
        .domain_status(domain_status), .limit_fraction(limit_fraction),
        .global_hazard(global_hazard), .stability_index(stability_index), .decision(decision)
    );

    task check; input cond; input [127:0] label;
        if (!cond) $display("FAIL: %s",label); else $display("PASS: %s",label);
    endtask

    initial begin
        rst_n <= 0;
        // Set default thresholds
        t_max <= 32'd1200; t_dot_max <= 32'd50; h_t_min <= 32'd20;
        sigma_max <= 32'd2000; sigma_dot_max <= 32'd200; d_m_max <= 32'd100;
        v_min <= 32'd2800; i_dot_max <= 32'd3000; soc_min <= 32'd500; p_margin_min <= 32'd200;
        d_max <= 32'd200; d_dot_max <= 32'd20; r_see_max <= 32'd10;
        tau_s_max <= 32'd3000; pi_max <= 32'd4000; l_max <= 32'd2000; j_max <= 32'd300;
        evidence_valid <= 6'b111111;
        // All-nominal sensor values
        temp_hotspot <= 12'd60; temp_rate <= 12'd5;
        stress_mech  <= 12'd500; stress_rate <= 12'd50;
        bus_voltage  <= 12'd3300; bus_current <= 12'd1000; battery_soc <= 12'd800;
        dose_rate    <= 12'd10; fill_fraction <= 12'd1000;
        loop_latency <= 32'd500; jitter <= 32'd50;
        repeat(4) @(posedge clk); rst_n <= 1; repeat(3) @(posedge clk);

        // TC-U01: All domains SAT
        check(domain_status[0]==3'b001, "TC-U01 Thermal SAT");
        check(domain_status[1]==3'b001, "TC-U01 Mech SAT");
        check(domain_status[2]==3'b001, "TC-U01 EPS SAT");
        check(domain_status[3]==3'b001, "TC-U01 Radiation SAT");
        check(domain_status[4]==3'b001, "TC-U01 Fluid SAT");
        check(domain_status[5]==3'b001, "TC-U01 Info SAT");
        check(decision == 2'b10, "TC-U01 Decision=ALLOW");

        // TC-U02: Thermal violation
        temp_hotspot <= 12'd1300;  // > t_max(1200)
        repeat(3) @(posedge clk);
        check(domain_status[0]==3'b010, "TC-U02 Thermal VIOL");
        check(decision == 2'b00, "TC-U02 Decision=REFUSE on violation");

        // TC-U03: EPS undetermined (evidence_valid[2]=0)
        temp_hotspot <= 12'd60; evidence_valid <= 6'b111011;
        repeat(3) @(posedge clk);
        check(domain_status[2]==3'b100, "TC-U03 EPS UND");
        check(decision == 2'b00, "TC-U03 Decision=REFUSE on UND");

        // TC-U04: Limit fraction non-zero when SAT
        evidence_valid <= 6'b111111;
        repeat(3) @(posedge clk);
        check(limit_fraction[0] > 0, "TC-U04 Thermal limit_fraction >0");
        check(stability_index > 0,   "TC-U04 Stability index >0");

        $display("=== tb_upasl_domain complete ==="); $finish;
    end
endmodule
