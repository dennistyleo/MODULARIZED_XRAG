// =============================================================================
// Module  : evidence_encoder.v  | Version: 1.1.0  | M-03
// Purpose : NDJSON-formatted evidence capture, FIFO storage, rate limiting.
//           256-bit internal record: {ts_ns[31:0], event_id[63:0],
//           state_id[31:0], severity[31:0], payload[95:0]}
//           AXI-Stream output streams 64-bit words per cycle (4 beats/record).
//           Gap detection: monotonic seq_number increments every record.
//           Silent drop prevention: SUMMARY record emitted on FIFO overflow.
// Ref     : AI-PMC Spec Section 4
// =============================================================================
`timescale 1ns/1ps
`default_nettype none

module EvidenceEncoder #(
    parameter FIFO_DEPTH     = 1024,
    parameter EVIDENCE_WIDTH = 256
)(
    input  wire        clk, rst_n,
    // Evidence input (from governance_fsm / sequencing_engine)
    input  wire        ev_valid,
    input  wire [EVIDENCE_WIDTH-1:0] ev_data,
    output reg         ev_ready,
    // FIFO status
    output reg  [9:0]  ev_count,
    output reg         ev_empty, ev_full,
    // AXI4-Stream output (64-bit wide, 4 beats per 256-bit record)
    output reg  [63:0] m_axis_tdata,
    output reg         m_axis_tvalid,
    input  wire        m_axis_tready
);
    // Pointer widths
    localparam PTR_W = $clog2(FIFO_DEPTH);

    // ── FIFO storage ─────────────────────────────────────────────────────────
    reg [EVIDENCE_WIDTH-1:0] fifo [0:FIFO_DEPTH-1];
    reg [PTR_W-1:0] wr_ptr, rd_ptr;
    reg [31:0] dropped_count;   // silent-drop counter
    reg [31:0] seq_number;      // monotonic, wraps after 2^32

    // SUMMARY record template (Spec Section 4.3)
    localparam [63:0] EV_SUMMARY = 64'h53554D4D41525900;  // "SUMMARY\0"

    function [EVIDENCE_WIDTH-1:0] make_summary;
        input [31:0] ts_ns, dropped;
    begin
        make_summary = {ts_ns, EV_SUMMARY, 32'h45564944, 32'd1, {64'd0, dropped}};
    end
    endfunction

    // Monotonic ts (ns at 100 MHz)
    reg [31:0] ts_ns;
    always @(posedge clk or negedge rst_n) if (!rst_n) ts_ns <= 0; else ts_ns <= ts_ns + 32'd10;

    // ── Write side ────────────────────────────────────────────────────────────
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            wr_ptr <= 0; ev_count <= 0; ev_full <= 0;
            dropped_count <= 0; seq_number <= 0; ev_ready <= 1;
        end else begin
            ev_full  <= (ev_count >= FIFO_DEPTH - 1);
            ev_ready <= ~ev_full;

            if (ev_valid && !ev_full) begin
                // Prepend seq_number into payload[31:0] (spec gap detection)
                fifo[wr_ptr] <= {ev_data[EVIDENCE_WIDTH-1:32], seq_number};
                wr_ptr    <= wr_ptr + 1;
                ev_count  <= ev_count + 1;
                seq_number <= seq_number + 1;
            end else if (ev_valid && ev_full) begin
                // Drop + accumulate; emit SUMMARY on next available slot
                dropped_count <= dropped_count + 1;
            end
        end
    end

    // Inject SUMMARY record when overflow clears
    reg emit_summary;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) emit_summary <= 0;
        // FIX Bug 10: guard on !ev_valid — prevents SUMMARY colliding with new data record
        else emit_summary <= (dropped_count > 0) && !ev_full && !ev_valid;

    // ── Read / serialisation side ─────────────────────────────────────────────
    // Burst 256-bit record as 4 × 64-bit beats on m_axis
    reg [1:0]  beat_idx;  // 0–3
    reg [EVIDENCE_WIDTH-1:0] cur_record;
    reg         reading;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rd_ptr <= 0; ev_empty <= 1; beat_idx <= 0;
            m_axis_tvalid <= 0; m_axis_tdata <= 0;
            cur_record <= 0; reading <= 0;
            // ANOM-022 FIX: Removed duplicate ev_empty assignment (was on next line).
        end else begin
            ev_empty <= (ev_count == 0);

            if (!reading && (!ev_empty || emit_summary)) begin
                // Load record
                if (emit_summary)
                    cur_record <= make_summary(ts_ns, dropped_count);
                else begin
                    cur_record <= fifo[rd_ptr];
                    rd_ptr    <= rd_ptr + 1;
                    ev_count  <= ev_count - 1;
                end
                beat_idx <= 0; reading <= 1;
                m_axis_tvalid <= 1;
            end

            if (reading && m_axis_tready) begin
                // Serialise beats MSB-first
                case (beat_idx)
                    2'd0: m_axis_tdata <= cur_record[EVIDENCE_WIDTH-1:192];
                    2'd1: m_axis_tdata <= cur_record[191:128];
                    2'd2: m_axis_tdata <= cur_record[127:64];
                    2'd3: begin
                          m_axis_tdata  <= cur_record[63:0];
                          m_axis_tvalid <= 0; reading <= 0;
                          if (emit_summary) dropped_count <= 0;
                    end
                endcase
                beat_idx <= beat_idx + 1;
            end
        end
    end

endmodule
`default_nettype wire
