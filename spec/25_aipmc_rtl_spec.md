AI-PMC FPGA RTL Specification (Updated)
Universal Physical Admissibility and Stabilisation Layer (UPASL) — RTL Implementation
text
Document Number : SOVEREIGN-SPEC-RTL-001
Version         : 1.0.1
Status          : APPROVED-DRAFT
Design Owner    : Sovereign Matrix Engineering
Date            : 2026-04-11
Target Device   : Xilinx Zynq UltraScale+ xczu7ev-ffvc1156-2-e
                  Versal VP1002 (secondary target)
                  **Zynq 7000, Artix-7, Kintex-7, Spartan-7 (backward compatible)**
Interface       : ARM AXI4-Lite + AXI4-Stream
Reference Docs  : AI-PMC Software Spec G_26260208_V0.1
                  XR-PMC Engineering Spec Draft_20260202
                  UPASL Specification Rev 1.1
                  spec/24_mcp_fpga.md (MCP/AXI transport layer)
1. Purpose and Scope
This specification defines the complete synthesizable RTL architecture for the AI-PMC (AI-native Power Management Controller) FPGA implementation. It governs the hardware design of all 15 modules across the Ontology Silicon Module hierarchy.

Backward Compatibility Statement: This design is fully backward compatible with lower-end Xilinx 7-series families (Zynq 7000, Artix-7, Kintex-7, Spartan-7) and Zynq UltraScale+ devices. The AXI4-Lite interface is supported across all these families, enabling direct integration with ARM Cortex-A9 (Zynq 7000), Cortex-A53 (UltraScale+), and Cortex-M class MCUs via AXI4-Lite or AHB-lite (with bridge).

Xilinx Device Family	AXI4-Lite Support	Recommended Clock	Compatibility
Zynq UltraScale+	✅ Yes	100 MHz	Native — fully tested
Zynq 7000	✅ Yes	100 MHz	Native — fully compatible
Artix-7	✅ Yes	50-100 MHz	Native — clock configurable
Kintex-7	✅ Yes	100 MHz	Native — fully compatible
Spartan-7	✅ Yes	50-100 MHz	Native — clock configurable
Spartan-6	⚠️ Limited	50 MHz	Requires AXI-to-AHB bridge
Design Parameterization for Backward Compatibility:

verilog
// All clock frequencies are parameterized for lower-end device compatibility
parameter AXI_CLK_MHZ = 100,   // Configurable: 50, 100, 200
        COMPUTE_CLK_MHZ = 300; // Configurable: 200, 250, 300 (device dependent)
The FPGA implements:

Layer	Modules	Purpose
Governance Layer	M-04 GovernanceFSM, M-05 SequencingEngine	Power state machine + rail sequencing
Evidence Layer	M-03 EvidenceEncoder	NDJSON audit trail capture
Verification Layer	M-06/07 ATPHardware	Automated test pattern injection
ML Layer	M-08 FeatureExtractor	64-byte training vector generation
Domain Layer	UPASLDomainEngine	6-domain physical admissibility
Compute Layer	PrimaryDecomposer, GroebnerBasisEngine	Algebraic reasoning acceleration
Interface Layer	AXISlaveInterface, TelemetryAggregator, MCPJsonRpcDecoder	AXI + serial bus bridging
Storage Layer	BRAMAxiomStore	4096×64-bit axiom memory
Semantic Layer	SemanticDistanceEngine, CausalInvariantTracker	Distance + invariant checking
2. System Architecture
(Diagram unchanged from v1.0.0)


┌──────────────────────────────────────────────────────────────────────────────┐
│                            OntologySiliconModule                             │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌───────────────┐    ┌──────────────────────────────────────────────────┐   │
│  │   AXI4-Lite   │◄───│               AXI Slave Interface                │   │
│  │   & Stream    │───►│          (Register Map 0x0000–0x7FFF)            │   │
│  └───────────────┘    └────────────────────────┬─────────────────────────┘   │
│                                                │                             │
│                            ┌───────────────────┴───────────────────┐         │
│                            │             Config / Cmd              │         │
│                            │                Status                 │         │
│                            ▼                                       ▼         │
│                    ┌───────────────┐                       ┌───────────────┐ │
│                    │ GovernanceFSM │                       │  Sequencing   │ │
│                    │    (M-04)     │                       │    Engine     │ │
│                    │    7-state    │                       │    (M-05)     │ │
│                    │  Guardrails   │                       │   POWER_ON    │ │
│                    └───────┬───────┘                       └───────┬───────┘ │
│                            │                                       │         │
│                            └───────────────────┬───────────────────┘         │
│                                                ▼                             │
│                             ┌─────────────────────────────────────┐          │
│                             │           EvidenceEncoder           │──► ST-out│
│                             │               (M-03)                │          │
│                             │           FIFO depth 1024           │          │
│                             └─────────────────────────────────────┘          │
│                                                                              │
│  ┌───────────────────┐  ┌───────────────────┐  ┌──────────────────────────┐  │
│  │    ATPHardware    │  │    UPASL Domain   │  │    Compute Subsystem     │  │
│  │    (M-06/M-07)    │  │    Engine (6-dom) │  │   GroebnerBasisEngine    │  │
│  │    ATP-01/ATP-02  │  │    Q16.16 limits  │  │   PrimaryDecomposer      │  │
│  │   4096-cycle dwell│  │    ALLOW/LIMIT/   │  │   SemanticDistEngine     │  │
│  │    5 fail codes   │  │    REFUSE decision│  │   CausalInvariantTrack   │  │
│  └───────────────────┘  └───────────────────┘  └──────────────────────────┘  │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │                  ML / Interface / Storage (100 MHz)                    │  │
│  │  FeatureExtractor (M-08) · TelemetryAggregator · BRAMAxiomStore        │  │
│  │  MCPJsonRpcDecoder                                                     │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────────┘
        Sensor Inputs: vin_valid, bus_ok, vcap[11:0], temp[11:0],
                       pgood[7:0], fault_flags[31:0],
                       adc_bus_voltage, adc_bus_current, adc_battery_soc,
                       adc_dose_rate, adc_fill_fraction,
                       pmbus/i2c/spi/uart/gpio

        Control Outputs: en_out[7:0], reset_out[7:0], irq_out
3. Clock Domain Architecture
Domain	Frequency	Modules	Notes
clk_100	100 MHz (configurable: 50-200 MHz)	All AXI, governance, evidence, ATP, ML, telemetry	Control path — frequency configurable for lower-end devices
clk_300	300 MHz (configurable: 200-300 MHz)	Groebner, PrimaryDecomposer	Compute path; may be reduced for Artix-7/Spartan-7 compatibility
Backward Compatibility Clock Configuration:

For lower-end Xilinx 7-series devices, the following clock frequency adjustments are recommended:

Device Family	Max AXI Clock	Max Compute Clock	Configuration
Zynq 7000	100 MHz	250 MHz	AXI_CLK_MHZ=100, COMPUTE_CLK_MHZ=250
Artix-7	80 MHz	200 MHz	AXI_CLK_MHZ=80, COMPUTE_CLK_MHZ=200
Kintex-7	100 MHz	300 MHz	Same as UltraScale+
Spartan-7	50 MHz	150 MHz	AXI_CLK_MHZ=50, COMPUTE_CLK_MHZ=150
CDC Policy: All signals crossing clk_100 ↔ clk_300 must use:

2-FF synchronizers for single-bit control

Gray-code FIFO for multi-bit data (FPGA primitive xpm_cdc_gray)

False-path constraints set in ontology_silicon.xdc

4. AXI Register Map (Complete)
*(Register map unchanged from v1.0.0 — fully compatible across all Xilinx AXI4-Lite implementations)*

4.1 Core Control Block — 0x0000–0x0FFF
Offset	Name	R/W	Reset	Description
0x0000	STATUS	R	0	[0]=BUSY [1]=DONE [2]=ERROR [3]=DECOMP_ACTIVE [4]=GOV_FAULT [5]=ATP_BUSY
0x0004	CONTROL	W	0	[0]=START [1]=RESET [2]=CLEAR_IRQ [3]=ML_CAPTURE [4]=ATP_INJECT [5]=ATP_CHECK
0x0008	IRQ_ENABLE	R/W	0	Bit mask: [0]=done [1]=error [2]=gov_fault [3]=seq_done [4]=atp_done
0x000C	AXIOM_COUNT	R	0	Number of axioms loaded into BRAM
0x0010	PRIME_COUNT	R	0	Irreducible component count (PrimaryDecomposer result)
0x0014	SEMANTIC_DIST	R	0	Q16.16 fixed-point semantic distance
0x0018	RUNTIME_LSW	R	0	Runtime cycle counter [31:0]
0x001C	RUNTIME_MSW	R	0	Runtime cycle counter [63:32]
0x0020	AXIOM_BASE_ADDR	W	0	BRAM base address for axiom polynomials
0x0024	RESULT_BASE_ADDR	W	0	BRAM base address for decomposition results
0x0028	TARGET_ADDR	W	0	BRAM address of target polynomial Q
0x002C	ERROR_CODE	R	0	Last error: 0=none, E001=FILE_NOT_FOUND … E010=HITL_TIMEOUT
4.2 Governance Config Block — 0x1000–0x1FFF
(Unchanged — see v1.0.0)

4.3 Evidence FIFO Block — 0x2000–0x2FFF
(Unchanged — see v1.0.0)

4.4 Governance FSM Block — 0x3000–0x3FFF
(Unchanged — see v1.0.0)

4.5 Sequencing Engine Block — 0x4000–0x4FFF
(Unchanged — see v1.0.0)

4.6 ATP Harness Block — 0x5000–0x5FFF
(Unchanged — see v1.0.0)

4.7 UPASL Domain Block — 0x6000–0x6FFF
(Unchanged — see v1.0.0)

4.8 Feature Extractor Block — 0x7000–0x7FFF
(Unchanged — see v1.0.0)

5. Module Specifications
(All module specifications unchanged from v1.0.0 — see original document for full details)

5.1 M-01: AXI Slave Interface
File: fpga/rtl/axi_slave_interface.v

Parameter	Value
Address width	15-bit (32 KB window)
Data width	32-bit
Register count	256 (word-addressed)
Write latency	2 cycles (AW + W accepted simultaneously)
Read latency	2 cycles
Command outputs	seq_start/stop/hold/resume, atp_inject/check, ml_capture (single-cycle strobes)
Backward Compatibility Note: AXI4-Lite is supported on all Xilinx 7-series and Zynq families. For Spartan-6 devices (which lack native AXI), an AXI-to-AHB bridge is available from Xilinx IP Catalog.

5.2 M-03: Evidence Encoder
(Unchanged — see v1.0.0)

5.3 M-04: Governance FSM
(Unchanged — see v1.0.0)

5.4 M-05: Sequencing Engine
(Unchanged — see v1.0.0)

5.5 M-06 / M-07: ATP Hardware
(Unchanged — see v1.0.0)

5.6 M-08: Feature Extractor
(Unchanged — see v1.0.0)

5.7 UPASL Domain Engine
(Unchanged — see v1.0.0)

5.8 Compute Subsystem
(Unchanged — see v1.0.0)

5.9 Interface Modules
(Unchanged — see v1.0.0)

6. Timing Budget
Path	Frequency	Budget	Status
AXI4-Lite read	100 MHz (50-200 configurable)	10.0 ns (20 ns at 50 MHz)	✅ Closed
AXI4-Lite write	100 MHz	10.0 ns	✅ Closed
GovernanceFSM guardrail	100 MHz	10.0 ns	✅ Closed
UPASLDomainEngine all 6	100 MHz	10.0 ns	✅ Closed with 1-cycle reg
GroebnerBasisEngine systolic	300 MHz (200-300 configurable)	3.33 ns (5 ns at 200 MHz)	⚠️ Requires ExtraTimingOpt placement
PrimaryDecomposer BRAM	300 MHz	3.33 ns	⚠️ BRAM output registered (2-cycle latency)
SemanticDistance 4-stage	100 MHz	10.0 ns	✅ Closed
EvidenceEncoder FIFO	100 MHz	10.0 ns	✅ Closed
Timing closure note for lower-end devices: When targeting Artix-7 or Spartan-7, reduce COMPUTE_CLK_MHZ to 200 MHz and AXI_CLK_MHZ to 50-80 MHz to meet timing requirements.

7. Resource Utilisation (Estimated)
7.1 UltraScale+ (xczu7ev) — Primary Target
(Unchanged from v1.0.0 — see original)

Module	LUTs	FFs	BRAM36	DSP48
Total	~16,350	~14,750	~26	~104
ZU7EV Capacity	230,400	460,800	312	1,728
Utilisation	7.1%	3.2%	8.3%	6.0%
7.2 Zynq 7000 (xc7z020) — Backward Compatibility Target
Module	LUTs	FFs	BRAM36	DSP48
Total	~16,350	~14,750	~26	~104
Z7-020 Capacity	53,200	106,400	140	220
Utilisation	30.7%	13.9%	18.6%	47.3%
Note: Zynq 7000 xc7z020 has sufficient capacity for the full design. For smaller devices (xc7z010), consider:

Reducing BRAM depth from 4096 to 2048 entries

Reducing MAX_POLYS from 32 to 16

Disabling compute subsystem if not required

7.3 Artix-7 (xc7a100t) — Lower-End Compatibility
Module	LUTs	FFs	BRAM36	DSP48
Total	~16,350	~14,750	~26	~104
A7-100T Capacity	63,400	126,800	270	240
Utilisation	25.8%	11.6%	9.6%	43.3%
8. Interrupt Architecture
(Unchanged from v1.0.0)

text
                GOV_FAULT  → irq_sources[2]
                SEQ_DONE   → irq_sources[3]
                ATP_DONE   → irq_sources[4]
                EVID_FULL  → irq_sources[5]
                DECOMP_DONE→ irq_sources[1]
                ML_READY   → irq_sources[6]
                         └──────► AND └── irq_out (edge to PS GIC)
                                  irq_enable[7:0]
All IRQ sources gate through irq_enable mask (AXI register 0x0008). Software must:

Read STATUS to decode source

Handle the event

Write CONTROL[2]=1 to clear

9. Error Code Reference
(Unchanged from v1.0.0)

Code	Name	Source	Recovery
E001	FILE_NOT_FOUND	PrimaryDecomposer watchdog	No retry — reload axiom BRAM
E002	GEMINI_API_TIMEOUT	MCP Proxy (SW)	Retry up to 3×
E003	INVALID_JSON_RESPONSE	MCPJsonRpcDecoder	Retry up to 2×
E004	SCHEMA_VALIDATION_FAILED	UPASLDomainEngine	Check threshold config
E005	MODULE_TIMEOUT	GovernanceFSM step timeout	Retry up to 3×
E006	DRIFT_DETECTION_FAILED	CausalInvariantTracker	Manual axiom review
E007	CAUSAL_CHAIN_BROKEN	CausalInvariantTracker	HITL escalation
E008	DATABASE_CONNECTION_FAILED	BRAMAxiomStore (SW)	Retry up to 3×
E009	BUS_ROUTING_FAILED	AXISlaveInterface	Reset CONTROL[1]
E010	HITL_TIMEOUT	SW HITL modal	Escalate to audit
10. Security Considerations
(Unchanged from v1.0.0)

Item	Requirement	Implementation
Register access	AXI4-Lite protection via PS TrustZone	Config registers in NS=0 (Secure) zone
Evidence FIFO	Non-writable from NS domain	AXI-Lite awprot[1] checked for write
ATP injection	Restricted to production test mode	allowed_actions[7] gating
Feature vectors	ML data must not leak axiom internals	FEATURE_VALID cleared after first read
Bitstream	AES-256 encrypted, BBRAM key	Set in Vivado Security tab
11. Backward Compatibility Matrix (NEW SECTION)
11.1 Xilinx Family Compatibility
Device Family	AXI4-Lite	Max AXI Clock	Max Compute Clock	Design Status
Zynq UltraScale+	✅ Native	200 MHz	300 MHz	✅ Verified
Zynq 7000	✅ Native	100 MHz	250 MHz	✅ Compatible
Artix-7	✅ Native	80 MHz	200 MHz	✅ Compatible (clock adj)
Kintex-7	✅ Native	100 MHz	300 MHz	✅ Compatible
Spartan-7	✅ Native	50 MHz	150 MHz	✅ Compatible (clock adj)
Spartan-6	⚠️ Bridge	50 MHz	—	⚠️ Requires AXI-to-AHB
11.2 Lower-End MCU Interface Compatibility
MCU Type	Interface	Compatibility	Notes
ARM Cortex-M4/M7	AXI4-Lite / AHB-Lite	✅ Direct	Memory-mapped register access
ARM Cortex-M0/M0+	AHB-Lite	✅ Via bridge	Xilinx AXI-to-AHB IP available
RISC-V (low-end)	AXI4-Lite	✅ Direct	SiFive, PicoRV32 with AXI
8051 / legacy MCU	Custom	⚠️ Requires translation	Use AXI-to-UART bridge
11.3 Clock Configuration Example for Lower-End Devices
tcl
# For Artix-7 compatibility (80 MHz AXI, 200 MHz compute)
set_property -dict {
    CONFIG.CLK_AXI_FREQ_MHZ {80}
    CONFIG.CLK_COMPUTE_FREQ_MHZ {200}
} [get_ports {clk_100 clk_300}]
12. Revision History
Version	Date	Author	Change
0.1	2026-04-09	Sovereign Matrix Eng	Initial draft
0.9	2026-04-10	Sovereign Matrix Eng	All 15 modules defined
1.0.0	2026-04-11	Sovereign Matrix Eng	APPROVED-DRAFT — AXI map, timing, resources
1.0.1	2026-04-11	Sovereign Matrix Eng	Added Backward Compatibility Matrix (Section 11) — Zynq 7000, Artix-7, Kintex-7, Spartan-7 support; MCU interface compatibility; resource estimates for lower-end devices
Summary of Changes (v1.0.0 → v1.0.1)
Section	Change
Document Header	Added backward compatible device list (Zynq 7000, Artix-7, Kintex-7, Spartan-7)
Section 1	Added Backward Compatibility Statement and parameterization guidance
Section 3	Added Backward Compatibility Clock Configuration table
Section 6	Added timing note for lower-end devices
Section 7	Added resource utilisation for Zynq 7000 and Artix-7
Section 11 (NEW)	Added Backward Compatibility Matrix — device families, MCU interfaces, clock configuration examples

AI-PMC FPGA RTL 實作規範 (優化版)文件編號：SOVEREIGN-SPEC-RTL-001版本：1.0.1 (實作導向優化) | 狀態：已核准草案日期：2026-04-111. 快速導覽與核心目標本規範旨在引導工程師在 Xilinx 各系列 FPGA 上實作 Ontology Silicon Module。核心功能：實現 AI 原生電源管理，包含治理 FSM、代數運算加速與審計追蹤。開發重點：確保在不同性能等級的晶片間（從 UltraScale+ 到 Spartan-7）保持介面一致性。1.1 跨平台相容性概覽Xilinx 系列AXI 支援推薦時鐘 (AXI/Compute)注意事項Zynq UltraScale+原生100 / 300 MHz效能基準，完整實作Kintex-7原生100 / 300 MHz效能與基準一致Zynq-7000 / Artix-7原生80 / 200 MHz需調整頻率參數以閉合時序Spartan-7原生50 / 150 MHz適合輕量化實作2. 系統架構圖 (實作佈局)開發提示：所有模組封裝在 OntologySiliconModule 頂層內。工程師應優先確保 AXI Slave Interface 通訊正常，再依序掛載各子系統。Plaintext       [ AXI4-Lite Master ] <────┐
                                 │
    ┌────────────────────────────┴─────────────────────────────┐
    │                OntologySiliconModule (Top)               │
    │ ┌──────────────────────────────────────────────────────┐ │
    │ │ M-01: AXI Slave Interface (Addr: 0x0000-0x7FFF)      │ │
    │ └──────┬───────────────┬───────────────────────┬───────┘ │
    │        ▼               ▼                       ▼         │
    │ [治理子系統]        [計算子系統]            [證據/驗證]    │
    │ M-04 Gov. FSM      Groebner Engine        M-03 Encoder   │
    │ M-05 Seq Engine    Primary Decomposer     M-06/07 ATP    │
    └──────────────────────────────────────────────────────────┘
3. 時鐘與跨時域 (CDC) 策略本設計分為兩個主要時鐘域。請嚴格執行以下 CDC 規範以防止亞穩態。3.1 時鐘域定義clk_100 (Control Path)：100 MHz (可降至 50 MHz)。負責 AXI、FSM、Telemetry。clk_300 (Data Path)：300 MHz (可降至 150 MHz)。負責代數引擎 (Groebner/Decomposer)。3.2 CDC 實作要求單位元 (Single-bit)：使用兩級觸發器 (2-FF) 同步。多位元 (Multi-bit)：必須使用 Gray-code FIFO (推薦呼叫 xpm_cdc_gray)。約束文件：務必在 .xdc 中定義 set_false_path 於跨時域路徑上。4. 工程師實作手冊：AXI 暫存器空間此表格為軟硬體對接的唯一標準，地址偏移量基於 AXI Base Address。4.1 核心控制 (0x0000–0x002C)偏移量名稱R/W位元描述0x0000STATUSR[0]Busy, [1]Done, [4]GovFault, [5]ATP_Busy0x0004CONTROLW[0]Start, [1]Reset, [2]ClearIRQ, [4]ATP_Inject0x000CAXIOM_CNTR當前載入的 Axiom 數量0x002CERR_CODER錯誤代碼 (參見第 9 節)4.2 模組化地址分配0x1000 - 0x1FFF：治理參數配置 (Governance Config)0x2000 - 0x2FFF：證據收集 (Evidence FIFO)0x6000 - 0x6FFF：UPASL 域引擎 (物理限制設定)5. 硬體資源分配預算工程師應根據目標晶片剩餘空間決定是否啟用「計算子系統」。目標設備LUT 佔用率FF 佔用率DSP 消耗建議優化方案ZU7EV7.1%3.2%104保持預設，全速運行Z7-02030.7%13.9%104建議降低 BRAM 深度至 2048A7-100T25.8%11.6%104需注意 DSP 散熱佈局6. 異常處理與錯誤碼 (Error Codes)當 STATUS[2] (Error) 置位時，讀取 0x002C。代碼名稱原因恢復建議E001FILE_NOT_FOUND計算引擎超時或 BRAM 未載入重新載入 Axiom BRAME004SCHEMA_VAL_FAILUPASL 物理限制越權檢查參數配置與傳感器輸入E009BUS_ROUT_FAILAXI 內部路由崩潰執行 CONTROL[1] 硬體重置7. 後向相容性實作建議 (Backward Compatibility)對於低端設備 (如 Artix-7, Spartan-7)，請修改 RTL 中的參數：Verilog// 範例：針對 Spartan-7 的降頻配置
parameter AXI_CLK_MHZ     = 50;  
parameter COMPUTE_CLK_MHZ = 150; 
時序閉合提示：若 GroebnerBasisEngine 報時序違例，請在 Vivado 中啟用 ExtraTimingOpt 或增加 systolic lane 的流水線級數。