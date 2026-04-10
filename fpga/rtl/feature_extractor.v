// =============================================================================
// Module  : feature_extractor.v  | Version: 1.0.0  | M-08
// Purpose : 64-byte feature vector generation for ML training pipeline.
//           Layout per AI-PMC Spec Section 6.1:
//           Bytes 0–7:  VOUT per rail (8×12-bit → packed 16-bit Q4.8)
//           Bytes 8–15: IOUT per rail
//           Bytes 16–23: Efficiency (Q8.8 fixed-point)
//           Bytes 24–31: Ripple mVpp
//           Bytes 32–39: Temperature sensors (4×12-bit → 16-bit)
//           Bytes 40–41: Droop (mV)
//           Bytes 42–43: Overshoot (mV)
//           Bytes 44–45: Settling time (μs)
//           Bytes 46–63: Reserved
// =============================================================================
`timescale 1ns/1ps
`default_nettype none

module FeatureExtractor #(
    parameter NUM_FEATURES = 64,
    parameter ADC_WIDTH    = 12
)(
    input  wire        clk, rst_n,
    // Sensor inputs
    input  wire [ADC_WIDTH-1:0] vout    [0:7],
    input  wire [ADC_WIDTH-1:0] iout    [0:7],
    input  wire [ADC_WIDTH-1:0] temp_in [0:3],
    input  wire [15:0] droop_mv, overshoot_mv, settling_us,
    // Efficiency / ripple (Q8.8 or mVpp, 16-bit effective)
    // (computed externally; passed directly into vector)
    input  wire [15:0] efficiency [0:7],
    input  wire [15:0] ripple_mv  [0:7],
    // Control
    input  wire        capture,
    // Output (512 bits = 64 bytes)
    output reg  [511:0] feature_vector,
    output reg          feature_valid,
    input  wire         feature_ready
);
    // Convert 12-bit ADC to 16-bit fixed-point (zero-extend upper nibble)
    function [15:0] adc_to_fp16;
        input [ADC_WIDTH-1:0] adc_val;
    begin
        adc_to_fp16 = {4'b0000, adc_val};
    end
    endfunction

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            feature_vector <= 512'd0;
            feature_valid  <= 1'b0;
        end else begin
            feature_valid <= 1'b0;  // default de-assert

            if (capture && feature_ready) begin
                // ── VOUT (bytes 0–7) ─────────────────────────────────────────
                feature_vector[511:448] <= {
                    adc_to_fp16(vout[7]), adc_to_fp16(vout[6]),
                    adc_to_fp16(vout[5]), adc_to_fp16(vout[4]),
                    adc_to_fp16(vout[3]), adc_to_fp16(vout[2]),
                    adc_to_fp16(vout[1]), adc_to_fp16(vout[0])
                };
                // ── IOUT (bytes 8–15) ────────────────────────────────────────
                feature_vector[447:384] <= {
                    adc_to_fp16(iout[7]), adc_to_fp16(iout[6]),
                    adc_to_fp16(iout[5]), adc_to_fp16(iout[4]),
                    adc_to_fp16(iout[3]), adc_to_fp16(iout[2]),
                    adc_to_fp16(iout[1]), adc_to_fp16(iout[0])
                };
                // ── Efficiency (bytes 16–23) ──────────────────────────────────
                feature_vector[383:320] <= {
                    efficiency[7], efficiency[6], efficiency[5], efficiency[4],
                    efficiency[3], efficiency[2], efficiency[1], efficiency[0]
                };
                // ── Ripple mVpp (bytes 24–31) ─────────────────────────────────
                feature_vector[319:256] <= {
                    ripple_mv[7], ripple_mv[6], ripple_mv[5], ripple_mv[4],
                    ripple_mv[3], ripple_mv[2], ripple_mv[1], ripple_mv[0]
                };
                // ── Temperature (bytes 32–39) ─────────────────────────────────
                feature_vector[255:192] <= {
                    16'd0, 16'd0,
                    adc_to_fp16(temp_in[3]), adc_to_fp16(temp_in[2]),
                    adc_to_fp16(temp_in[1]), adc_to_fp16(temp_in[0])
                };
                // ── Transient metrics (bytes 40–45) ──────────────────────────
                feature_vector[191:160] <= {droop_mv, overshoot_mv};
                feature_vector[159:144] <= settling_us;
                // ── Reserved (bytes 46–63) ────────────────────────────────────
                feature_vector[143:0]   <= 144'd0;

                feature_valid <= 1'b1;
            end
        end
    end

endmodule
`default_nettype wire
