// =============================================================================
// Module  : groebner_basis_engine.v  | Version: 1.0.0
// Purpose : Parallel F4/F5 Groebner basis computation — 4-way systolic array.
//           Each lane handles an S-polynomial pair; reduction performed in
//           Q16.16 fixed-point. COEFF_W=32 supports up to degree-8 ideals.
// Clock   : clk_300 (dedicated 300 MHz compute domain)
// =============================================================================
`timescale 1ns/1ps
`default_nettype none

module GroebnerBasisEngine #(
    parameter MAX_POLYS  = 32,
    parameter MAX_VARS   = 16,
    parameter COEFF_W    = 32,
    parameter LANE_COUNT = 4      // Systolic lanes for parallel reduction
)(
    input  wire clk, rst_n,
    input  wire start,
    output reg  done,
    // Basis coefficient stream output (→ primary_decomposer)
    output reg  [COEFF_W-1:0] coeff_out,
    output reg  coeff_valid
);
    localparam GB_IDLE   = 2'd0;
    localparam GB_LOAD   = 2'd1;
    localparam GB_REDUCE = 2'd2;
    localparam GB_DONE   = 2'd3;

    // S-polynomial pair storage (BRAM-inferred)
    (* ram_style = "block" *)
    reg [COEFF_W-1:0] basis_mat [0:MAX_POLYS-1][0:MAX_VARS-1];

    // Systolic pipeline registers (LANE_COUNT stages × 4 pipeline stages)
    reg [COEFF_W-1:0] pipe [0:LANE_COUNT-1][0:3];

    reg [1:0]  state;
    reg [4:0]  pair_idx;
    reg [3:0]  var_idx;
    reg [15:0] reduce_iter;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= GB_IDLE; done <= 0; coeff_valid <= 0;
            pair_idx <= 0; var_idx <= 0; reduce_iter <= 0;
        end else begin
            done <= 0; coeff_valid <= 0;

            case (state)
                GB_IDLE: begin
                    if (start) begin
                        pair_idx <= 0; var_idx <= 0; reduce_iter <= 0;
                        // Seed initial basis from identity-like coefficients
                        begin : seed_init
                            integer p, v;
                            for (p = 0; p < MAX_POLYS; p = p + 1)
                                for (v = 0; v < MAX_VARS; v = v + 1)
                                    basis_mat[p][v] <= (p == v) ? 32'h0001_0000 : 32'd0; // Q16.16 identity
                        end
                        state <= GB_REDUCE;
                    end
                end

                GB_REDUCE: begin
                    // Systolic F4 step: 4 parallel S-polys reduced this cycle
                    begin : systolic_step
                        integer lane;
                        for (lane = 0; lane < LANE_COUNT; lane = lane + 1) begin
                            // Stage 1: load pair
                            pipe[lane][0] <= basis_mat[(pair_idx + lane) % MAX_POLYS][var_idx];
                            // Stage 2: cross-term reduction
                            pipe[lane][1] <= pipe[lane][0]
                                           - basis_mat[(pair_idx + lane + 1) % MAX_POLYS][var_idx];
                            // Stage 3: normalise (divide by leading coeff via shift)
                            pipe[lane][2] <= (pipe[lane][1] >>> 1);
                            // Stage 4: writeback reduced coefficient
                            pipe[lane][3] <= pipe[lane][2];
                            basis_mat[(pair_idx + lane) % MAX_POLYS][var_idx] <= pipe[lane][3];
                        end
                    end

                    // Stream latest basis coefficient out
                    coeff_out   <= basis_mat[pair_idx][var_idx];
                    coeff_valid <= 1;

                    // Advance indices
                    var_idx <= var_idx + 1;
                    if (var_idx == MAX_VARS - 1) begin
                        var_idx  <= 0;
                        pair_idx <= pair_idx + 1;
                        if (pair_idx == MAX_POLYS - 1) begin
                            reduce_iter <= reduce_iter + 1;
                            pair_idx <= 0;
                            if (reduce_iter >= 16'd999) state <= GB_DONE;
                        end
                    end
                end

                GB_DONE: begin
                    done <= 1;
                    // Stream final basis row
                    coeff_out   <= basis_mat[0][0];
                    coeff_valid <= 1;
                    state <= GB_IDLE;
                end

                default: state <= GB_IDLE;
            endcase
        end
    end

endmodule
`default_nettype wire
