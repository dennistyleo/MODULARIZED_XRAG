// =============================================================================
// Module  : evidence_encoder.v  | Version: 1.2.0
// Purpose : Encodes telemetry evidence into 256-bit records for axiom engine
// FIXED   : Consolidated multiple drivers into single always block
// =============================================================================
`timescale 1ns/1ps
`default_nettype none

module evidence_encoder #(
    parameter FIFO_DEPTH = 1024,
    parameter FIFO_WIDTH = 256
)(
    input  wire clk, rst_n,
    
    // Write side (telemetry input)
    input  wire        ev_valid,
    output reg         ev_ready,
    input  wire [31:0] ts_ns,
    input  wire [63:0] event_id,
    input  wire [31:0] state_id,
    input  wire [31:0] severity,
    input  wire [95:0] payload,
    
    // Read side (axiom engine output)
    output reg         ev_has_data,
    input  wire        ev_read_ready,
    output reg  [FIFO_WIDTH-1:0] ev_read_data,
    
    // Status
    output reg  [9:0]  ev_count,
    output reg  [31:0] dropped_count,
    output reg         overflow_flag
);

    // FIFO storage
    reg [FIFO_WIDTH-1:0] fifo [0:FIFO_DEPTH-1];
    reg [9:0] wr_ptr, rd_ptr;
    reg [9:0] count;
    
    // Internal signals
    wire write_en;
    wire read_en;
    wire full;
    wire empty;
    
    assign full  = (count == FIFO_DEPTH);
    assign empty = (count == 0);
    assign write_en = ev_valid && ev_ready && !full;
    assign read_en  = ev_has_data && ev_read_ready && !empty;
    
    // Pack data into 256-bit record
    wire [FIFO_WIDTH-1:0] packed_data;
    assign packed_data = {ts_ns, event_id, state_id, severity, payload};
    
    // ============================================================
    // UNIFIED ALWAYS BLOCK — ALL REGISTERS IN ONE PLACE
    // ============================================================
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            wr_ptr <= 0;
            rd_ptr <= 0;
            count <= 0;
            ev_count <= 0;
            dropped_count <= 0;
            overflow_flag <= 0;
            ev_ready <= 1;
            ev_has_data <= 0;
            ev_read_data <= 0;
        end else begin
            // Defaults
            ev_ready <= 1;
            
            // ========================================================
            // FIFO write operation
            // ========================================================
            if (write_en) begin
                fifo[wr_ptr] <= packed_data;
                wr_ptr <= wr_ptr + 1;
                count <= count + 1;
                ev_count <= ev_count + 1;
            end
            
            // ========================================================
            // FIFO read operation
            // ========================================================
            if (read_en) begin
                ev_read_data <= fifo[rd_ptr];
                rd_ptr <= rd_ptr + 1;
                count <= count - 1;
                ev_count <= ev_count - 1;
            end
            
            // ========================================================
            // Overflow handling (dropped events)
            // ========================================================
            if (ev_valid && full) begin
                dropped_count <= dropped_count + 1;
                overflow_flag <= 1;
            end else begin
                overflow_flag <= 0;
            end
            
            // ========================================================
            // Reset dropped_count when it reaches max (optional)
            // ========================================================
            if (dropped_count == 32'hFFFF_FFFF) begin
                dropped_count <= 0;
            end
            
            // ========================================================
            // Status outputs
            // ========================================================
            ev_has_data <= !empty;
            
        end
    end

endmodule
`default_nettype wire
