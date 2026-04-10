// =============================================================================
// Testbench : tb_groebner_basis.v  | Version: 1.0.0
// Purpose   : Verifies Groebner basis engine: start, reduction, coeff output.
// =============================================================================
`timescale 1ns/1ps

module tb_groebner_basis;
    reg  clk, rst_n, start;
    wire done; wire [31:0] coeff_out; wire coeff_valid;
    initial clk = 0; always #(5/2.0) clk = ~clk;

    GroebnerBasisEngine #(.MAX_POLYS(8),.MAX_VARS(4),.COEFF_W(32),.LANE_COUNT(4)) dut (
        .clk(clk), .rst_n(rst_n), .start(start),
        .done(done), .coeff_out(coeff_out), .coeff_valid(coeff_valid)
    );

    task check; input cond; input [127:0] label;
        if (!cond) $display("FAIL: %s",label); else $display("PASS: %s",label);
    endtask

    integer coeff_count; initial coeff_count=0;
    always @(posedge clk) if (coeff_valid) coeff_count <= coeff_count + 1;

    initial begin
        rst_n <= 0; start <= 0;
        repeat(4) @(posedge clk); rst_n <= 1; @(posedge clk);

        start <= 1; @(posedge clk); start <= 0;
        // Groebner runs for 1000 iterations × MAX_POLYS × MAX_VARS
        repeat(40000) @(posedge clk);

        check(done, "TC-GB01: Groebner engine completes");
        check(coeff_count > 0, "TC-GB02: Coefficient stream produced");
        check(coeff_out != 32'd0, "TC-GB03: Final coeff non-zero (basis non-trivial)");

        $display("coeff_count=%0d", coeff_count);
        $display("=== tb_groebner_basis complete ==="); $finish;
    end
endmodule
