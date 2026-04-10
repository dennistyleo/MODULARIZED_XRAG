// =============================================================================
// Module  : bram_axiom_store.v  | Version: 1.0.0
// Purpose : True dual-port 4096×64-bit BRAM wrapper.
//           Port A: read-write (axiom storage, results)
//           Port B: read-only  (semantic engine, decomposer read-back)
// Xilinx   : Infers RAMB36 primitives via (* ram_style = "block" *)
// =============================================================================
`timescale 1ns/1ps
`default_nettype none

module BRAMAxiomStore #(
    parameter DEPTH = 4096,
    parameter WIDTH = 64
)(
    input  wire                 clk,
    // Port A (read-write)
    input  wire [$clog2(DEPTH)-1:0] addr_a,
    input  wire [WIDTH-1:0]     din_a,
    output reg  [WIDTH-1:0]     dout_a,
    input  wire                 we_a, en_a,
    // Port B (read-only)
    input  wire [$clog2(DEPTH)-1:0] addr_b,
    output reg  [WIDTH-1:0]     dout_b,
    input  wire                 en_b
);
    (* ram_style = "block" *)
    reg [WIDTH-1:0] mem [0:DEPTH-1];

    // Port A
    always @(posedge clk) begin
        if (en_a) begin
            if (we_a) mem[addr_a] <= din_a;
            dout_a <= mem[addr_a];
        end
    end

    // Port B (read-only)
    always @(posedge clk) begin
        if (en_b) dout_b <= mem[addr_b];
    end

endmodule
`default_nettype wire
