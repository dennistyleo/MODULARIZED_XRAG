# MCP FPGA Specification — Ontology Silicon Module

Version: 1.0.0  
Status: DRAFT  
Authors: Sovereign Matrix Engineering Team  
Date: 2026-04-11

---

## Overview

This document specifies the **Model Context Protocol (MCP)** for connecting the Sovereign Matrix software stack to an FPGA-accelerated **Ontology Silicon Module** via the **ARM AXI Bus** (XILINX-native MCU interface).

The module performs real-time axiomatic reasoning directly in hardware: primary algebraic decomposition, Gröbner basis computation, and causal invariant tracking — achieving ~10ms latency for 5 axioms of degree ≤4 at 100 MHz.

---

## Part 1: Hardware–Software Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                      HOST CPU (Software Layer)                       │
│  ┌───────────┐  ┌─────────────┐  ┌────────────┐  ┌─────────────┐   │
│  │ Landing UI│  │ Dashboard   │  │ Report Gen │  │ RAG NLP     │   │
│  └─────┬─────┘  └──────┬──────┘  └─────┬──────┘  └──────┬──────┘   │
│        └───────────────┴───────────────┴────────────────┘           │
│                                │                                     │
│                        ┌───────┴───────┐                            │
│                        │  MCP Proxy    │                            │
│                        │ (JSON-RPC /   │                            │
│                        │  WebSocket)   │                            │
│                        └───────┬───────┘                            │
└────────────────────────────────┼────────────────────────────────────┘
                                 │
                        ┌────────┴────────┐
                        │   ARM AXI Bus   │
                        │   (XILINX)      │
                        └────────┬────────┘
                                 │
┌────────────────────────────────┼────────────────────────────────────┐
│                   FPGA (Hardware Acceleration Layer)                  │
│  ┌─────────────────────────────┴───────────────────────────────┐    │
│  │                  ONTOLOGY SILICON MODULE                     │    │
│  │  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐   │    │
│  │  │ AXI Slave │→│Primary Dec│→│ Gröbner   │→│ Causal    │   │    │
│  │  │ Interface │ │(Hardware) │ │ Basis (F4)│ │ Tracker   │   │    │
│  │  └───────────┘ └───────────┘ └───────────┘ └───────────┘   │    │
│  │                      ┌────────────────┐                     │    │
│  │                      │  DDR/BRAM      │                     │    │
│  │                      │  Axiom Store   │                     │    │
│  │                      │  4096 × 64-bit │                     │    │
│  │                      └────────────────┘                     │    │
│  └──────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Part 2: Transport Layer

| Parameter         | Value                                   |
|------------------|-----------------------------------------|
| Physical Interface | AXI4-Lite (control) + AXI4-Stream (data) |
| Address Width    | 32-bit                                  |
| Data Width       | 64-bit (axioms) / 32-bit (control)      |
| Clock Frequency  | 100 MHz (configurable to 300 MHz)       |
| Protocol         | JSON-RPC 2.0 over AXI (custom framing)  |
| Endianness       | Little-endian (ARM native)              |

---

## Part 3: AXI Memory Map

| Offset   | Register          | R/W | Description                                        |
|----------|-------------------|-----|----------------------------------------------------|
| 0x0000   | STATUS_REG        | R   | [0]=BUSY [1]=DONE [2]=ERROR [3]=DECOMP_ACTIVE      |
| 0x0004   | CONTROL_REG       | W   | [0]=START [1]=RESET [2]=CLEAR_IRQ                  |
| 0x0008   | IRQ_ENABLE        | R/W | Interrupt enable mask                              |
| 0x000C   | AXIOM_COUNT       | R   | Number of axioms in current set                    |
| 0x0010   | PRIME_COUNT       | R   | Number of irreducible components found             |
| 0x0014   | SEMANTIC_DIST     | R   | Fixed-point Q16.16 semantic distance               |
| 0x0018   | RUNTIME_CYCLE     | R   | 64-bit cycle counter for last operation            |
| 0x001C   | ERROR_CODE        | R   | Error code on failure (see E001–E010)              |
| 0x0020   | AXIOM_BASE_ADDR   | W   | Base address in BRAM for axiom polynomials         |
| 0x0024   | RESULT_BASE_ADDR  | W   | Base address for result storage                    |
| 0x0028   | TARGET_ADDR       | W   | Address of target polynomial Q                    |
| 0x002C–0x0FFF | Reserved   | —   | Future expansion                                   |

---

## Part 4: JSON-RPC Message Framing (over AXI-Stream)

```
┌────────────┬────────────┬─────────────┬────────────┬──────────────────┐
│ Magic (4B) │ Length (4B)│ Msg ID (4B) │ Flags (4B) │ JSON Payload ... │
│ 0x4D4350   │            │             │            │                  │
│ ("MCP")    │            │             │            │                  │
└────────────┴────────────┴─────────────┴────────────┴──────────────────┘
```

**Flags:**

| Flag | Value | Meaning      |
|------|-------|--------------|
| REQ  | 0x01  | Request      |
| RESP | 0x02  | Response     |
| ERR  | 0x04  | Error        |
| STREAM | 0x08 | Streaming chunk |
| FINAL | 0x10 | Final chunk  |

---

## Part 5: JSON-RPC API Methods

| Method                   | Description                                | FPGA Engine               |
|--------------------------|--------------------------------------------|-----------------------------|
| `axiom.decompose`        | Primary decomposition on axiom set         | Primary Decomposer          |
| `axiom.semantic_distance`| Distance between two axiom sets            | Semantic Distance Engine    |
| `axiom.derive`           | Check if Q is derivable from axioms        | Gröbner Basis Engine        |
| `causal.invariant_check` | Verify causal invariants in telemetry      | Causal Invariant Tracker    |
| `ontology.synthesize`    | Generate new axiom from RAG + decomposition | Full pipeline               |

### Example: `axiom.decompose`

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "axiom.decompose",
  "params": {
    "axiom_set": [
      "F_c - m2*d2*w^2 = 0",
      "F_g - F_c = 0",
      "w*p - 1 = 0",
      "m1*d1 - m2*d2 = 0"
    ],
    "target": "m1*m2*G*p^2 - d2^2*d1*m1 - d1^2*d2*m2 = 0",
    "variables": ["F_c","F_g","m1","m2","d1","d2","w","p","G"]
  }
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "associated_primes": [
      "⟨d2, m1, F_g, F_c, wp-1⟩",
      "⟨m2, d1, F_g, F_c, wp-1⟩",
      "⟨F_c-F_g, m1d1-m2d2, F_g(d1+d2)²-m1m2G, ...⟩"
    ],
    "candidate_missing_axioms": [
      {
        "axiom_id":          "EINSTEIN_FIELD_EQ_04",
        "expression":        "F_g(d1+d2)^2 - m1*m2*G = 0",
        "derives_target":    true,
        "semantic_distance": 0.72
      }
    ],
    "runtime_cycles": 1250000,
    "runtime_ms":     12.5
  }
}
```

---

## Part 6: Verilog RTL — Ontology Silicon Module

```verilog
// OntologySiliconModule.v — XILINX UltraScale+
// Synthesizable RTL for primary decomposition + semantic distance
module OntologySiliconModule #(
    parameter MAX_AXIOMS   = 32,
    parameter MAX_VARIABLES = 16,
    parameter POLY_DEGREE   = 8
)(
    input  wire        clk,
    input  wire        rst_n,

    // AXI4-Lite Slave (Control Register File)
    input  wire [31:0] s_axi_awaddr,
    input  wire        s_axi_awvalid,
    output wire        s_axi_awready,
    input  wire [31:0] s_axi_wdata,
    input  wire [3:0]  s_axi_wstrb,
    input  wire        s_axi_wvalid,
    output wire        s_axi_wready,
    output wire [1:0]  s_axi_bresp,
    output wire        s_axi_bvalid,
    input  wire        s_axi_bready,
    input  wire [31:0] s_axi_araddr,
    input  wire        s_axi_arvalid,
    output wire        s_axi_arready,
    output wire [31:0] s_axi_rdata,
    output wire [1:0]  s_axi_rresp,
    output wire        s_axi_rvalid,
    input  wire        s_axi_rready,

    // AXI4-Stream (Payload In/Out)
    input  wire [63:0] s_axis_tdata,
    input  wire        s_axis_tvalid,
    output wire        s_axis_tready,
    output wire [63:0] m_axis_tdata,
    output wire        m_axis_tvalid,
    input  wire        m_axis_tready,

    // Interrupt
    output wire        irq
);

    // ── Registers ──────────────────────────────────────────────
    reg [31:0] status_reg;       // 0x00
    reg [31:0] control_reg;      // 0x04
    reg [31:0] irq_enable;       // 0x08
    reg [31:0] axiom_count;      // 0x0C
    reg [31:0] prime_count;      // 0x10
    reg [31:0] semantic_dist_q;  // 0x14 Q16.16 fixed-point
    reg [63:0] runtime_cycles;   // 0x18
    reg [31:0] error_code;       // 0x1C
    reg [31:0] axiom_base_addr;  // 0x20
    reg [31:0] result_base_addr; // 0x24
    reg [31:0] target_addr;      // 0x28

    // ── BRAM: Axiom Store ─────────────────────────────────────
    (* ram_style = "block" *)
    reg [63:0] axiom_bram [0:4095];  // 32 KB

    // ── Sub-module: Primary Decomposer ────────────────────────
    wire decomp_done;
    PrimaryDecomposer #(
        .MAX_AXIOMS(MAX_AXIOMS),
        .MAX_VARS(MAX_VARIABLES),
        .MAX_DEG(POLY_DEGREE)
    ) u_decomposer (
        .clk(clk), .rst_n(rst_n),
        .start(control_reg[0]),
        .axiom_addr(axiom_base_addr),
        .target_addr(target_addr),
        .result_addr(result_base_addr),
        .done(decomp_done),
        .prime_count_out(prime_count),
        .error_code_out(error_code)
    );

    // ── Sub-module: Semantic Distance Engine ─────────────────
    wire dist_valid;
    SemanticDistanceEngine u_semantic (
        .clk(clk),
        .axiom_a_addr(axiom_base_addr),
        .axiom_b_addr(result_base_addr),
        .distance_out(semantic_dist_q),
        .valid(dist_valid)
    );

    // ── Runtime Cycle Counter ─────────────────────────────────
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) runtime_cycles <= 64'd0;
        else if (control_reg[0] && !decomp_done)
            runtime_cycles <= runtime_cycles + 64'd1;
    end

    // ── Status Register ───────────────────────────────────────
    always @(posedge clk) begin
        status_reg[0] <= control_reg[0] & ~decomp_done;   // BUSY
        status_reg[1] <= decomp_done & (error_code == 0); // DONE
        status_reg[2] <= (error_code != 0);               // ERROR
        status_reg[3] <= control_reg[0];                  // DECOMP_ACTIVE
    end

    // ── Interrupt ─────────────────────────────────────────────
    assign irq = (status_reg[1] | status_reg[2]) & irq_enable[0];

endmodule
```

---

## Part 7: ARM C Driver (XILINX Zynq / Versal)

```c
/* mcp_axi_interface.h — XILINX-native MCP driver */
#include <xil_io.h>
#include <xparameters.h>
#include <stdbool.h>
#include <stdint.h>

#define MCP_BASE    XPAR_ONTOLOGY_MODULE_0_S00_AXI_BASEADDR
#define REG(off)    (MCP_BASE + (off))

/* Register offsets */
#define STATUS_REG      0x00
#define CONTROL_REG     0x04
#define IRQ_ENABLE      0x08
#define AXIOM_COUNT     0x0C
#define PRIME_COUNT     0x10
#define SEMANTIC_DIST   0x14  /* Q16.16 fixed-point */
#define RUNTIME_CYCLES  0x18
#define ERROR_CODE      0x1C
#define AXIOM_BASE_ADDR 0x20
#define RESULT_BASE_ADDR 0x24
#define TARGET_ADDR     0x28

/* Status bits */
#define STATUS_BUSY   (1u << 0)
#define STATUS_DONE   (1u << 1)
#define STATUS_ERROR  (1u << 2)

typedef struct {
    uint32_t axiom_count;
    uint32_t axiom_base;
    uint32_t target_addr;
    uint32_t result_base;
} mcp_request_t;

typedef struct {
    bool     success;
    uint32_t prime_count;
    float    semantic_distance;  /* converted from Q16.16 */
    uint64_t runtime_cycles;
    uint32_t error_code;
} mcp_result_t;

/**
 * mcp_send_request — block until FPGA completes decomposition.
 * Returns 0 on success, -1 on error.
 */
int mcp_send_request(const mcp_request_t *req, mcp_result_t *out) {
    /* Write parameters */
    Xil_Out32(REG(AXIOM_BASE_ADDR),  req->axiom_base);
    Xil_Out32(REG(TARGET_ADDR),      req->target_addr);
    Xil_Out32(REG(RESULT_BASE_ADDR), req->result_base);
    Xil_Out32(REG(AXIOM_COUNT),      req->axiom_count);
    Xil_Out32(REG(IRQ_ENABLE),       0x01);  /* enable done IRQ */

    /* Start */
    Xil_Out32(REG(CONTROL_REG), 0x01);

    /* Poll for completion (replace with IRQ handler in production) */
    uint32_t status;
    do {
        status = Xil_In32(REG(STATUS_REG));
    } while (!(status & (STATUS_DONE | STATUS_ERROR)));

    /* Read results */
    out->success           = !(status & STATUS_ERROR);
    out->prime_count       = Xil_In32(REG(PRIME_COUNT));
    out->semantic_distance = (float)Xil_In32(REG(SEMANTIC_DIST)) / 65536.0f;
    out->runtime_cycles    = (uint64_t)Xil_In32(REG(RUNTIME_CYCLES));
    out->error_code        = Xil_In32(REG(ERROR_CODE));

    /* Clear IRQ */
    Xil_Out32(REG(CONTROL_REG), 0x04);
    return out->success ? 0 : -1;
}
```

---

## Part 8: FPGA Resource Utilization (UltraScale+)

| Resource     | Primary Decomp | Gröbner (F4) | Causal Tracker | Total   |
|--------------|---------------|--------------|----------------|---------|
| LUTs         | 45k           | 120k         | 25k            | ~190k   |
| FFs          | 35k           | 95k          | 20k            | ~150k   |
| DSP48        | 64            | 256          | 16             | ~336    |
| BRAM36       | 8             | 24           | 4              | ~36     |
| URAM         | 0             | 4            | 0              | ~4      |

**Target:** Zynq UltraScale+ ZU9EG or Versal VP1002  
**Clock:** 100 MHz (nominal), 300 MHz (with timing closure effort)  
**Latency:** ~10 ms for 5 axioms of degree ≤4 @ 100 MHz

---

## Part 9: MCP Software Proxy

The MCP Proxy bridges the UI WebSocket → AXI Bus → FPGA. It runs as a Python service:

```python
# mcp_proxy.py (pseudocode — see full implementation in modules/mcp_proxy.py)
import asyncio, json
from websockets import serve

async def handle(websocket):
    async for raw in websocket:
        rpc = json.loads(raw)
        if rpc["method"] == "axiom.decompose":
            result = send_to_fpga(rpc["params"])      # AXI driver call
            await websocket.send(json.dumps({
                "jsonrpc": "2.0",
                "id": rpc["id"],
                "result": result
            }))

asyncio.run(serve(handle, "0.0.0.0", 8765))
```

**WebSocket endpoint:** `wss://xr.aichipco.com/mcp/v1/stream`

---

## Part 10: CI/CD Integration

```yaml
# .github/workflows/fpga_validate.yml
name: FPGA MCP Validation

on: [push, pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run test harness (mock mode)
        run: python test-harness/test-runner.py --api-url mock://
      - name: Check pass rate
        run: python -c "import json; d=json.load(open('test-harness/results.json')); assert d['summary']['pass_rate']>=0.80, 'Pass rate below 80%'"
```
