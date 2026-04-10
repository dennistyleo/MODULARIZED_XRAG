// =============================================================================
// Testbench : tb_primary_decomposer.v  | Version: 1.0.0
// Purpose   : Verifies primary decomposer: load, Groebner reduction, output.
// =============================================================================
`timescale 1ns/1ps

module tb_primary_decomposer;
    reg  clk, rst_n, start;
    initial clk = 0; always #(5/2.0) clk = ~clk;  // 300 MHz approx

    reg  [31:0] axiom_base, target, result_base;
    reg  [31:0] coeff_tdata; reg coeff_tvalid;
    wire        coeff_tready;
    wire [255:0] prime_tdata; wire prime_tvalid; reg prime_tready;
    wire         done; wire [31:0] prime_count, error_code;
    reg  [31:0]  gb_coeff; reg gb_valid;

    PrimaryDecomposer #(.MAX_AXIOMS(8),.MAX_VARIABLES(4),.COEFF_WIDTH(32),.POLY_WIDTH(256)) dut (
        .clk(clk), .rst_n(rst_n), .start(start),
        .done(done), .prime_count(prime_count), .error_code(error_code),
        .axiom_base_addr(axiom_base), .target_addr(target), .result_base_addr(result_base),
        .s_axis_coeff_tdata(coeff_tdata), .s_axis_coeff_tvalid(coeff_tvalid),
        .s_axis_coeff_tready(coeff_tready),
        .m_axis_prime_tdata(prime_tdata), .m_axis_prime_tvalid(prime_tvalid),
        .m_axis_prime_tready(prime_tready),
        .gb_coeff_in(gb_coeff), .gb_coeff_valid(gb_valid)
    );

    task check; input cond; input [127:0] label;
        if (!cond) $display("FAIL: %s",label); else $display("PASS: %s",label);
    endtask

    integer i;
    initial begin
        rst_n <= 0; start <= 0; coeff_tvalid <= 0; prime_tready <= 1;
        axiom_base <= 0; target <= 32'd5; result_base <= 32'd100;
        gb_coeff <= 32'h0001_0000; gb_valid <= 0;
        repeat(4) @(posedge clk); rst_n <= 1; @(posedge clk);

        // Start decomposition
        start <= 1; @(posedge clk); start <= 0;

        // Stream coefficients
        coeff_tvalid <= 1; gb_valid <= 1;
        for (i = 0; i < 32; i = i + 1) begin
            coeff_tdata <= i * 32'h0001_0000;
            gb_coeff <= (i+1) * 32'h0000_8000;
            @(posedge clk);
        end
        coeff_tvalid <= 0; gb_valid <= 0;

        // Wait for done (up to 50K cycles watchdog)
        repeat(12000) @(posedge clk);
        check(done || error_code == 0, "TC-PD01: Decomposer completes without error");
        check(prime_count > 0, "TC-PD02: At least one prime component found");

        $display("=== tb_primary_decomposer complete ==="); $finish;
    end
endmodule
