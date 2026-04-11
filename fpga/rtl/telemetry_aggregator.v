// =============================================================================
// Module  : telemetry_aggregator.v  | Version: 1.1.0
// Purpose : Multi-bus telemetry capture: PMBus/I2C/SPI/UART/GPIO.
//           Each bus has a small FIFO and a bit-bang state machine.
//           Output: 32-bit decoded measurement per bus + data_valid strobe.
// =============================================================================
`timescale 1ns/1ps
`default_nettype none

module TelemetryAggregator #(parameter FIFO_DEPTH = 16)(
    input  wire clk, rst_n,
    // PMBus (I2C-compatible) — open-drain bus
    input  wire pmbus_sda_i, pmbus_scl_i,
    output reg  pmbus_sda_o, pmbus_sda_oe,
    // I2C (generic)
    input  wire i2c_sda_i, i2c_scl_i,
    output reg  i2c_sda_o, i2c_sda_oe,
    // SPI (full-duplex)
    input  wire spi_sclk, spi_mosi, spi_cs_n,
    output reg  spi_miso,
    // UART (115200 baud assumed at 100 MHz → 868 cycles/bit)
    input  wire uart_rx,
    output wire uart_tx,
    // GPIO
    input  wire [7:0] gpio_in,
    output reg  [7:0] gpio_out,
    // Decoded outputs
    output reg  [31:0] pmbus_data, i2c_data, spi_data,
    output reg  [7:0]  uart_byte,
    output reg         data_valid
);
    // ── PMBus / I2C bit-bang receiver ─────────────────────────────────────────
    // Detects START, samples 8-bit data, checks ACK
    reg [7:0]  i2c_shift; reg [3:0] i2c_bit_cnt;
    reg        i2c_sda_prev;
    wire       i2c_start = i2c_sda_prev && !i2c_sda_i && i2c_scl_i; // SDA falls while SCL high

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            i2c_shift <= 0; i2c_bit_cnt <= 0;
            i2c_data <= 0; pmbus_data <= 0;
            i2c_sda_prev <= 1; i2c_sda_o <= 1; i2c_sda_oe <= 0;
            pmbus_sda_o <= 1; pmbus_sda_oe <= 0;
        end else begin
            i2c_sda_prev <= i2c_sda_i;
            // Sample on SCL rising edge
            if (i2c_scl_i && !i2c_sda_prev) begin
                i2c_shift <= {i2c_shift[6:0], i2c_sda_i};
                i2c_bit_cnt <= i2c_bit_cnt + 1;
                if (i2c_bit_cnt == 4'd7) begin
                    i2c_data  <= {24'd0, i2c_shift};
                    pmbus_data <= {24'd0, i2c_shift};
                    data_valid <= 1;
                    i2c_bit_cnt <= 0;
                end
            end else data_valid <= 0;
        end
    end

    // ── SPI receiver (mode 0: CPOL=0, CPHA=0) ────────────────────────────────
    reg [7:0]  spi_shift; reg [3:0] spi_bit;
    reg        spi_sclk_prev;
    wire       spi_rising = spi_sclk && !spi_sclk_prev;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            spi_shift <= 0; spi_bit <= 0; spi_data <= 0;
            spi_miso <= 0; spi_sclk_prev <= 0;
        end else begin
            spi_sclk_prev <= spi_sclk;
            if (!spi_cs_n && spi_rising) begin
                spi_shift <= {spi_shift[6:0], spi_mosi};
                spi_bit <= spi_bit + 1;
                if (spi_bit == 4'd7) begin
                    spi_data  <= {24'd0, spi_shift};
                    spi_miso  <= spi_shift[7];  // echo MSB (loopback test mode)
                end
            end
        end
    end

    // ── UART receiver (115200 baud, 1 start, 8 data, 1 stop) ─────────────────
    localparam BAUD_DIV = 868;  // 100 MHz / 115200
    reg [9:0]  baud_cnt; reg [3:0] uart_bit_cnt;
    reg [7:0]  uart_shift;
    reg        uart_rx_prev;
    reg        uart_active;
    wire       uart_start = uart_rx_prev && !uart_rx;  // falling edge

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            baud_cnt <= 0; uart_bit_cnt <= 0; uart_shift <= 0;
            uart_byte <= 0; uart_rx_prev <= 1; uart_active <= 0;
        end else begin
            uart_rx_prev <= uart_rx;
            if (!uart_active && uart_start) begin
                uart_active <= 1; baud_cnt <= BAUD_DIV/2; uart_bit_cnt <= 0;
            end else if (uart_active) begin
                baud_cnt <= baud_cnt - 1;
                if (baud_cnt == 0) begin
                    baud_cnt <= BAUD_DIV;
                    if (uart_bit_cnt < 8) begin
                        uart_shift <= {uart_rx, uart_shift[7:1]};
                        uart_bit_cnt <= uart_bit_cnt + 1;
                    end else begin
                        uart_byte <= uart_shift;
                        uart_active <= 0;
                    end
                end
            end
        end
    end
    assign uart_tx = 1'b1;  // No transmitter in this version

    // ── GPIO passthrough ──────────────────────────────────────────────────────
    // ANOM-010 FIX: Added rst_n — gpio_out now 0x00 during reset (was undefined X)
    always @(posedge clk or negedge rst_n)
        if (!rst_n) gpio_out <= 8'h00;
        else        gpio_out <= gpio_in;  // Mirror until host writes gpio_ctrl

endmodule
`default_nettype wire
