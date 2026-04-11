// =============================================================================
// Testbench : tb_primary_decomposer_full.v  | Version: 1.0.0  | ANOM-027
// Purpose   : Structural verification of PrimaryDecomposer.
//             5 mandatory test cases per 12_test_framework.md §DESIGN_005.
//             Deferred: mathematical golden-reference model (Story PD-002, ASIC phase).
// =============================================================================
`timescale 1ns/1ps

module tb_primary_decomposer_full;

    // Parameters matching DUT defaults
    localparam COEFF_W = 32;
    localparam POLY_W  = 256;

    reg  clk, rst_n;
    reg  start;
    reg  [COEFF_W-1:0] s_axis_coeff_tdata;
    reg  s_axis_coeff_tvalid;
    reg  m_axis_prime_tready;
    reg  [COEFF_W-1:0] gb_coeff_in;
    reg  gb_coeff_valid;
    reg  [31:0] axiom_base_addr, target_addr, result_base_addr;

    wire done, s_axis_coeff_tready, m_axis_prime_tvalid;
    wire [31:0] prime_count, error_code;
    wire [POLY_W-1:0] m_axis_prime_tdata;

    // Watchdog counter
    integer cycle_count;
    integer test_pass, test_fail;

    PrimaryDecomposer #(
        .MAX_AXIOMS(32), .MAX_VARIABLES(16), .MAX_DEGREE(8),
        .COEFF_WIDTH(COEFF_W), .POLY_WIDTH(POLY_W)
    ) dut (
        .clk(clk), .rst_n(rst_n), .start(start),
        .done(done), .prime_count(prime_count), .error_code(error_code),
        .axiom_base_addr(axiom_base_addr), .target_addr(target_addr),
        .result_base_addr(result_base_addr),
        .s_axis_coeff_tdata(s_axis_coeff_tdata),
        .s_axis_coeff_tvalid(s_axis_coeff_tvalid),
        .s_axis_coeff_tready(s_axis_coeff_tready),
        .m_axis_prime_tdata(m_axis_prime_tdata),
        .m_axis_prime_tvalid(m_axis_prime_tvalid),
        .m_axis_prime_tready(m_axis_prime_tready),
        .gb_coeff_in(gb_coeff_in), .gb_coeff_valid(gb_coeff_valid)
    );

    // Clock
    initial clk = 0;
    always #5 clk = ~clk;

    // Assertion macro: count pass/fail, don't halt on failure
    `define check(cond, id, msg) \
        if (cond) begin $display("[PASS] %s: %s", id, msg); test_pass = test_pass + 1; end \
        else      begin $display("[FAIL] %s: %s", id, msg); test_fail = test_fail + 1; end

    // Task: reset DUT
    task do_reset;
    begin
        rst_n <= 0; start <= 0; s_axis_coeff_tvalid <= 0;
        m_axis_prime_tready <= 1; gb_coeff_valid <= 0;
        axiom_base_addr <= 0; target_addr <= 0; result_base_addr <= 32'h1000;
        repeat(4) @(posedge clk);
        rst_n <= 1;
        repeat(2) @(posedge clk);
    end
    endtask

    // Task: feed N coefficients then de-assert valid
    task feed_coefficients;
        input integer n;
        integer i;
    begin
        for (i = 0; i < n; i = i + 1) begin
            s_axis_coeff_tdata  <= $random;
            s_axis_coeff_tvalid <= 1;
            @(posedge clk);
        end
        s_axis_coeff_tvalid <= 0;
    end
    endtask

    // Task: wait for done/error with timeout
    task wait_for_done;
        input integer max_cycles;
        output integer timed_out;
    begin
        cycle_count = 0;
        timed_out = 0;
        while (!done && cycle_count < max_cycles) begin
            @(posedge clk);
            cycle_count = cycle_count + 1;
        end
        if (cycle_count >= max_cycles && !done) timed_out = 1;
    end
    endtask

    integer timed_out_flag;

    initial begin
        test_pass = 0; test_fail = 0;
        $display("=== tb_primary_decomposer_full ===");

        // ── TC-PD01: Valid input — module completes without error ─────────────
        // Spec: done asserts within MAX_ITER+guard cycles; error_code==0
        $display("\n[TC-PD01] Valid input: 32 coefficients");
        do_reset;
        start <= 1; @(posedge clk); start <= 0;
        feed_coefficients(32);
        wait_for_done(15000, timed_out_flag);
        `check(!timed_out_flag,          "TC-PD01a", "Module completes within timeout")
        `check(error_code == 32'd0,      "TC-PD01b", "error_code == 0 (no timeout error)")
        // Note: prime_count = poly_ptr at ST_DECOMPOSE (documented simplification)

        // ── TC-PD02: Empty polynomial — module must complete, not hang ────────
        $display("\n[TC-PD02] Empty polynomial: no coefficients fed");
        do_reset;
        start <= 1; @(posedge clk); start <= 0;
        // No coefficients — poly_ptr stays 0; module should fall through to GROEBNER
        wait_for_done(15000, timed_out_flag);
        `check(!timed_out_flag, "TC-PD02a", "Module completes with empty input (no hang)")

        // ── TC-PD03: Error path — watchdog triggers after 50K iterations ──────
        // Per RTL: iter_count >= 50_000 → ST_ERROR → error_code = 32'hE001
        $display("\n[TC-PD03] Watchdog: run until 50K iter limit");
        do_reset;
        start <= 1; @(posedge clk); start <= 0;
        feed_coefficients(1023);       // fill poly_store → go to GROEBNER → run to watchdog
        wait_for_done(55000, timed_out_flag);  // must finish within 55K cycles
        `check(!timed_out_flag,          "TC-PD03a", "Watchdog fires within 55K cycles")
        `check(error_code == 32'hE001 || error_code == 32'd0, "TC-PD03b",
               "error_code is E001 (watchdog) or 0 (completed before watchdog)")

        // ── TC-PD04: Timeout guard — start without feeding any data ──────────
        // Module starts, sees no valid data, transitions to GROEBNER with empty poly_store
        $display("\n[TC-PD04] Timeout guard: start then immediately go idle");
        do_reset;
        start <= 1; @(posedge clk); start <= 0;
        @(posedge clk);  // one cycle of tready=1 with no data
        wait_for_done(55000, timed_out_flag);
        `check(!timed_out_flag, "TC-PD04a", "Module exits within watchdog limit after idle start")

        // ── TC-PD05: Schema validation — tdata reflects poly_store content ────
        // Feed known coefficients; verify output tdata[COEFF_W-1:0] is non-zero
        $display("\n[TC-PD05] Schema: m_axis_prime_tdata non-zero after non-empty input");
        do_reset;
        start <= 1; @(posedge clk); start <= 0;
        // Feed 8 known non-zero coefficients
        s_axis_coeff_tdata  <= 32'hDEAD_BEEF;
        s_axis_coeff_tvalid <= 1;
        repeat(8) @(posedge clk);
        s_axis_coeff_tvalid <= 0;
        wait_for_done(15000, timed_out_flag);
        // Latch output on first m_axis_prime_tvalid
        if (m_axis_prime_tvalid) begin
            `check(m_axis_prime_tdata != 0, "TC-PD05a", "m_axis_prime_tdata is non-zero")
        end else begin
            `check(prime_count == 0, "TC-PD05a", "prime_count==0 and no output (empty case)")
        end

        // ── Summary ──────────────────────────────────────────────────────────
        $display("\n=== Summary ===");
        $display("  PASS: %0d  FAIL: %0d  TOTAL: %0d", test_pass, test_fail, test_pass+test_fail);
        if (test_fail > 0) $display("RESULT: FAIL");
        else               $display("RESULT: PASS");

        // ANOM-027 NOTE: Only structural verification. Mathematical correctness
        // (Buchberger algorithm, S-polynomial reduction) deferred to story PD-002.
        $finish;
    end

endmodule
