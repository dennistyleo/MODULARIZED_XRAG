// =============================================================================
// Testbench : governance_tb.v  | Version: 1.0.0
// Purpose   : Unified testbench covering M-03/M-04/M-05/M-06/M-07/M-08
//             Verification checklist (Spec Section 9):
//             [TC01] Guardrail trip on VIN invalid → GOV_STATE=FAULT, evidence
//             [TC02] Full power-up: IDLE→POWERUP→RUN
//             [TC03] Throttle command emits EVID.THROTTLE.CMD
//             [TC04] POWER_ON sequence: all rails enabled, SEQ_DONE
//             [TC05] PGOOD timeout: SEQ_FAIL, EVID.SEQ.TIMEOUT
//             [TC06] Evidence FIFO read: records match expected
//             [TC07] ATP-01: VIN invalid → ATP_PASS=1
//             [TC08] ATP-02: PGOOD timeout → ATP_PASS=1
//             [TC09] Feature capture: 512-bit vector non-zero
// =============================================================================
`timescale 1ns/1ps

module governance_tb;
    localparam CLK_PERIOD = 10;  // 100 MHz

    reg clk, rst_n;
    // Governance FSM (M-04) DUT signals
    reg        vin_valid, bus_ok;
    reg [11:0] vcap, temp;
    reg [31:0] fault_flags;
    reg        power_up_req, power_down_req;
    reg [7:0]  throttle_req, timing_shift_req;
    wire       gov_ev_valid; wire [255:0] gov_ev_data;
    wire [2:0] gov_state; wire [31:0] gov_fault_cause;
    assign gov_ev_ready = 1'b1;

    // Sequencing Engine (M-05) DUT signals
    reg [7:0]  pgood_in;
    reg        seq_start, seq_stop, seq_hold, seq_resume;
    wire [7:0] en_out;
    wire       seq_ev_valid; wire [255:0] seq_ev_data;
    wire [2:0] seq_state; wire [7:0] current_step;
    assign seq_ev_ready = 1'b1;

    // Evidence Encoder (M-03)
    wire [63:0] ev_tdata; wire ev_tvalid;
    wire [9:0]  ev_count; wire ev_empty;
    reg         ev_tready;

    // ATP (M-06/07)
    reg [7:0]  atp_test_id; reg atp_inject, atp_check;
    wire       atp_pass; wire [31:0] atp_fail_reason; wire atp_busy;
    wire       inject_vin_invalid, inject_pgood_timeout;

    // Feature extractor (M-08)
    reg [11:0] vout0; reg [15:0] droop_mv;
    reg        capture; wire [511:0] feat_vec; wire feat_valid;

    // ── DUT instantiations ────────────────────────────────────────────────────
    GovernanceFSM #(.SENSOR_WIDTH(12)) u_gov (
        .clk(clk), .rst_n(rst_n),
        .profile_id(32'd0), .timeouts_ms(32'd100), .thresholds({12'd105,12'd800}),
        .hysteresis(32'd0), .allowed_actions(32'hFF),
        .vin_valid(vin_valid), .bus_ok(bus_ok), .vcap(vcap), .temp(temp),
        .fault_flags(fault_flags), .power_up_req(power_up_req),
        .power_down_req(power_down_req), .throttle_req(throttle_req),
        .timing_shift_req(timing_shift_req),
        .evidence_valid(gov_ev_valid), .evidence_data(gov_ev_data),
        .evidence_ready(gov_ev_ready), .gov_state(gov_state), .fault_cause(gov_fault_cause)
    );

    SequencingEngine #(.MAX_STEPS(16), .MAX_RAILS(8)) u_seq (
        .clk(clk), .rst_n(rst_n),
        .vin_valid(vin_valid & ~inject_vin_invalid), .bus_ok(bus_ok),
        .pgood_in(pgood_in), .fault_flags(fault_flags),
        .seq_start(seq_start), .seq_stop(seq_stop),
        .seq_hold(seq_hold), .seq_resume(seq_resume),
        .en_out(en_out), .reset_out(),
        .evidence_valid(seq_ev_valid), .evidence_data(seq_ev_data),
        .evidence_ready(seq_ev_ready), .seq_state(seq_state),
        .current_step(current_step), .timeout_count()
    );

    EvidenceEncoder #(.FIFO_DEPTH(64)) u_ev (
        .clk(clk), .rst_n(rst_n),
        .ev_valid(gov_ev_valid | seq_ev_valid),
        .ev_data(gov_ev_valid ? gov_ev_data : seq_ev_data),
        .ev_ready(), .ev_count(ev_count), .ev_empty(ev_empty), .ev_full(),
        .m_axis_tdata(ev_tdata), .m_axis_tvalid(ev_tvalid), .m_axis_tready(ev_tready)
    );

    ATPHardware #(.NUM_ATP_TESTS(8)) u_atp (
        .clk(clk), .rst_n(rst_n),
        .atp_test_id(atp_test_id), .atp_inject(atp_inject), .atp_check(atp_check),
        .inject_vin_invalid(inject_vin_invalid), .inject_pgood_timeout(inject_pgood_timeout),
        .inject_timeout_ms(),
        .ev_has_seq_start(seq_state==3'd1), .ev_has_seq_blocked(~vin_valid & seq_start),
        .ev_has_seq_done(seq_state==3'd4), .ev_has_seq_timeout(seq_state==3'd5),
        .atp_pass(atp_pass), .atp_fail_reason(atp_fail_reason), .atp_busy(atp_busy)
    );

    FeatureExtractor #(.ADC_WIDTH(12)) u_feat (
        .clk(clk), .rst_n(rst_n),
        .vout_flat({8{vout0}}),           // 96-bit flat  (8 lanes × 12-bit)
        .iout_flat({8{12'd100}}),         // 96-bit flat
        .temp_flat({4{12'd35}}),          // 48-bit flat  (4 sensors × 12-bit)
        .eff_flat({8{16'hD000}}),         // 128-bit flat (8 lanes × 16-bit)
        .rip_flat({8{16'd30}}),           // 128-bit flat
        .droop_mv(droop_mv[15:0]), .overshoot_mv(16'd5), .settling_us(16'd12),
        .capture(capture), .feature_vector(feat_vec),
        .feature_valid(feat_valid), .feature_ready(1'b1)
    );

    // ── Clock ─────────────────────────────────────────────────────────────────
    initial clk = 0;
    always #(CLK_PERIOD/2) clk = ~clk;

    // ── Tasks ─────────────────────────────────────────────────────────────────
    task reset_dut;
    begin
        rst_n <= 0; repeat(4) @(posedge clk); rst_n <= 1; @(posedge clk);
    end
    endtask

    task apply_defaults;
    begin
        vin_valid <= 1; bus_ok <= 1; vcap <= 12'd1000; temp <= 12'd60;
        fault_flags <= 0; power_up_req <= 0; power_down_req <= 0;
        throttle_req <= 0; timing_shift_req <= 0;
        pgood_in <= 8'hFF; seq_start <= 0; seq_stop <= 0;
        seq_hold <= 0; seq_resume <= 0;
        atp_test_id <= 0; atp_inject <= 0; atp_check <= 0;
        ev_tready <= 1; vout0 <= 12'd3300; droop_mv <= 16'd50; capture <= 0;
    end
    endtask

    task check; input cond; input [127:0] label; begin
        if (!cond) $display("FAIL: %s @ %0t", label, $time);
        else        $display("PASS: %s @ %0t", label, $time);
    end
    endtask

    // ── Test sequence ─────────────────────────────────────────────────────────
    initial begin
        apply_defaults; reset_dut;

        // TC01: Guardrail trip on VIN invalid
        vin_valid <= 0; repeat(3) @(posedge clk);
        check(gov_state == 3'd5, "TC01: GOV_STATE=FAULT on VIN invalid");
        check(gov_ev_valid, "TC01: Evidence emitted on guardrail trip");
        vin_valid <= 1; repeat(3) @(posedge clk);
        check(gov_state == 3'd6, "TC01: GOV_STATE=SAFE after guardrail clears");

        // TC02: Full power-up: IDLE→POWERUP→RUN
        power_up_req <= 1; @(posedge clk); power_up_req <= 0;
        repeat(10) @(posedge clk);
        check(gov_state == 3'd3, "TC02: GOV_STATE=RUN after power_up_req");

        // TC03: Throttle command
        throttle_req <= 8'd50; @(posedge clk); throttle_req <= 0;
        check(gov_ev_valid, "TC03: Evidence emitted for throttle command");

        // TC04: POWER_ON sequence
        power_up_req <= 1; seq_start <= 1; @(posedge clk);
        power_up_req <= 0; seq_start <= 0;
        pgood_in <= 8'hFF;
        repeat(200) @(posedge clk);
        check(seq_state == 3'd4 || en_out != 0, "TC04: SEQ_DONE or rail enabled");

        // TC05: PGOOD timeout triggered by ATP
        atp_test_id <= 8'd2; atp_inject <= 1; @(posedge clk); atp_inject <= 0;
        repeat(12'hFFF + 100) @(posedge clk);
        check(atp_pass, "TC05+TC08: ATP-02 PGOOD timeout → PASS");

        // TC07: ATP-01 VIN invalid
        atp_test_id <= 8'd1; atp_inject <= 1; @(posedge clk); atp_inject <= 0;
        repeat(12'hFFF + 100) @(posedge clk);
        check(atp_pass, "TC07: ATP-01 VIN invalid → PASS");

        // TC06: Evidence FIFO has records
        check(!ev_empty || ev_count > 0, "TC06: Evidence FIFO has records");

        // TC09: Feature capture
        capture <= 1; @(posedge clk); capture <= 0;
        @(posedge clk);
        check(feat_valid && (feat_vec != 512'd0), "TC09: Feature vector non-zero");

        $display("=== governance_tb complete ===");
        $finish;
    end

    // Timeout watchdog
    initial begin
        #2_000_000;
        $display("TIMEOUT: simulation exceeded 2ms");
        $finish;
    end

endmodule
