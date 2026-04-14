# 🔍 Axiom Generator — Software Evaluation Suite

## Overview

The Axiom Generator Software Evaluation Suite is a comprehensive, standards-compliant system for evaluating software quality across **9 analytical layers** (L1-L9), aligned with **ISO/IEC 25010** quality characteristics and **CMMI Level 5** (Optimizing) maturity requirements.

It supports **multi-language evaluation** (Python, C++, Verilog, JavaScript, Firmware) with **automatic toolchain fallback** when native tools are missing.

---

## 🎯 Key Capabilities

| Capability | Description |
|------------|-------------|
| **9-Layer Pipeline** | Syntax → Logic → Axiom → Structure → Design → Maintainability → Debugability → Firmware → Common Sense |
| **ISO/IEC 25010 Compliance** | 8 quality characteristics with sub-characteristic scoring |
| **CMMI Level 5** | Quantitative management, process variation tracking, continuous improvement |
| **Multi-Language Support** | Python, C++, Verilog, SystemVerilog, JavaScript, Firmware (BIOS/EC/UEFI) |
| **Toolchain Fallback** | Automatically detects missing tools and provides fallback analysis |
| **Audit Reports** | Professional HTML/JSON reports with remediation plans |

---

## 📊 Evaluation Layers

| Layer | Name | What It Evaluates |
|-------|------|-------------------|
| **L1** | Syntax | Basic syntax errors, compilation failures |
| **L2** | Logic | Algorithm correctness, infinite loops, logic errors |
| **L3** | Axiom | Causality, determinism, memory conservation, input validation |
| **L4** | Structure | Cyclomatic complexity, nesting depth, coupling |
| **L5** | Design | Design patterns, SOLID principles, anti-patterns |
| **L6** | Maintainability | Comment density, magic numbers, naming conventions |
| **L7** | Debugability | Testability, serviceability, scalability, extendibility |
| **L8** | Firmware | BIOS/EC/UEFI specific (POST, IVT, Secure Boot, Watchdog) |
| **L9** | Common Sense | Zero timeouts, hardcoded credentials, infinite retries |

---

## 📋 ISO/IEC 25010 Quality Characteristics

| Characteristic | Weight | Sub-characteristics |
|----------------|--------|---------------------|
| Functional Suitability | 10 | Completeness, Correctness, Appropriateness |
| Performance Efficiency | 8 | Time behaviour, Resource utilization, Capacity |
| Compatibility | 6 | Co-existence, Interoperability |
| Usability | 7 | Learnability, Operability, Error protection, Accessibility |
| Reliability | 9 | Maturity, Availability, Fault tolerance, Recoverability |
| Security | 10 | Confidentiality, Integrity, Authenticity |
| Maintainability | 8 | Modularity, Reusability, Analysability, Modifiability, Testability |
| Portability | 5 | Adaptability, Installability, Replaceability |

---

## 🏗️ CMMI Level 5 (Optimizing) Features

| Feature | Description |
|---------|-------------|
| **Quantitative Management** | Metrics database with targets and performance tracking |
| **Statistical Process Control** | Mean, std dev, UCL/LCL calculations |
| **Defect Prevention** | Root cause analysis, prevention action generation |
| **Continuous Improvement** | Opportunity identification from defect trends |
| **Innovation Pipeline** | Suggests improvements based on data analysis |

---

## 🛠️ Supported Languages & Tools

| Language | Extensions | Primary Tool | Fallback |
|----------|------------|--------------|----------|
| Python | `.py` | AST parsing | Static analysis |
| C++ | `.cpp`, `.cc`, `.cxx` | g++ / GoogleTest | Static analysis |
| Verilog/SystemVerilog | `.v`, `.sv` | iverilog | Regex syntax check |
| JavaScript | `.js` | Regex parsing | N/A |
| Firmware (BIOS/EC/UEFI) | `.bin`, `.hex`, `.elf`, `.rom` | QEMU | Binary analysis |
| HTML/CSS | `.html`, `.css` | Playwright | N/A |
| JSON | `.json` | Schema validation | N/A |

---

## 🚀 Usage

### Command Line

```bash
# ISO/IEC 25010 Evaluation
python3 modules/axiom_orchestrator/iso25010_evaluator.py <file_path> [language]

# CMMI Level 5 Evaluation
python3 modules/axiom_orchestrator/cmmi_level5_evaluator.py

# Full Axiom Orchestrator (L1-L9 with toolchain fallback)
python3 modules/axiom_orchestrator/orchestrator.py
Python API
python
from modules.axiom_orchestrator.iso25010_evaluator import ISO25010Evaluator

evaluator = ISO25010Evaluator()
report = evaluator.evaluate("my_script.py", "python")
evaluator.print_report(report)

print(f"Overall Quality Score: {report.overall_quality_score}/100")
print(f"Grade: {report.overall_grade}")

for qs in report.quality_scores:
    print(f"{qs.characteristic}: {qs.score}/100 ({qs.grade})")
Test Suite
bash
# Run complete test suite
python3 tests/orchestrator/test_complete.py

# Run individual tests
python3 tests/orchestrator/test_examples.py
📊 Sample Output
ISO/IEC 25010 Report
text
======================================================================
█  ISO/IEC 25010 COMPLIANT AUDIT REPORT
█  Systems and Software Quality Requirements and Evaluation
======================================================================

   Report ID: ISO25010-5133
   File: test_examples.py
   Language: python
   
   📊 OVERALL QUALITY SCORE: 89/100
   📈 GRADE: A-
   ✅ Standards Compliance: 7/8 characteristics

----------------------------------------------------------------------
📋 QUALITY CHARACTERISTICS
----------------------------------------------------------------------

   ✅ Functional Suitability: 100/100 (A+)
   ✅ Performance Efficiency: 100/100 (A+)
   ✅ Compatibility: 100/100 (A+)
   ✅ Usability: 70/100 (B-)
   ⚠️ Reliability: 65/100 (C+)
   ✅ Security: 100/100 (A+)
   ✅ Maintainability: 85/100 (A-)
   ✅ Portability: 95/100 (A+)

----------------------------------------------------------------------
🔧 RECOMMENDATIONS
----------------------------------------------------------------------
   1. [Usability] Add command-line interface
   2. [Usability] Add try/except error handling
   3. [Reliability] Add exception handling
   4. [Reliability] Add retry logic for transient failures
   5. [Maintainability] Add documentation comments
CMMI Level 5 Report
text
======================================================================
█  CMMI LEVEL 5 - OPTIMIZING
█  Capability Maturity Model Integration
======================================================================

   Maturity Level: 5 - Optimizing
   Overall Maturity Score: 83/100

----------------------------------------------------------------------
📊 QUANTITATIVE MANAGEMENT
----------------------------------------------------------------------
   ⚠️ defect_detection_rate: 85.5/95.0 percent
   ✅ evaluation_time: 2.5/3.0 seconds

----------------------------------------------------------------------
🔧 CONTINUOUS IMPROVEMENT OPPORTUNITIES
----------------------------------------------------------------------
   📌 PROCESS_IMPROVEMENT: Layer L3
      Highest defect concentration (1 defects)
      → Action: Implement additional validation rules for L3
      Expected Impact: 30% reduction in defects
📁 Architecture
text
modules/axiom_orchestrator/
├── orchestrator.py           # L1-L9 pipeline with toolchain fallback
├── iso25010_evaluator.py     # ISO/IEC 25010 compliance
├── cmmi_level5_evaluator.py  # CMMI Level 5 maturity
└── __init__.py

modules/toolchain_adapters/
├── base_adapter.py           # Base class for all adapters
├── python_adapter.py         # Python execution with venv
├── cpp_adapter.py            # C++ with g++/GoogleTest
├── firmware_adapter.py       # Firmware with QEMU
└── __init__.py

tests/orchestrator/
├── test_examples.py          # Basic test examples
└── test_complete.py          # Complete test suite (15 scenarios)
🧪 Test Coverage
#	Test Scenario	Language	Status
1	Successful execution	Python	✅ PASS
2	Syntax error	Python	✅ PASS
3	Logic error	Python	✅ PASS
4	Causal drift (crash)	Python	✅ PASS
5	Infinite loop	Python	✅ PASS
6	Successful compilation	C++	✅ PASS
7	Compilation error with fallback	C++	✅ NEEDS_REVIEW
8	Memory leak detection	C++	✅ PASS
9	Firmware/BIOS emulation	Binary	✅ NEEDS_REVIEW
10	Web/JavaScript	HTML/JS	⏸️ SKIPPED
11	Verilog/FPGA	.v	⏸️ SKIPPED
12	Backup fallback	Python	✅ PASS
13	All layers failing	Python	✅ PASS
14	JSON validation	JSON	⏸️ SKIPPED
15	Unsupported language	Rust	❌ ERROR
🔧 Installation
bash
# Clone repository
git clone https://github.com/dennistyleo/MODULARIZED_XRAG.git
cd MODULARIZED_XRAG

# Install Python dependencies
pip install playwright pytest pytest-playwright
playwright install chromium

# Install language-specific tools (optional, for full functionality)
brew install icarus-verilog  # Verilog/SystemVerilog
brew install qemu            # Firmware emulation
brew install gcc             # C++ compilation
📚 Standards Compliance
Standard	Description	Implemented
ISO/IEC 25010	Software product quality	✅ Yes
ISO/IEC 25000 (SQuaRE)	Quality requirements and evaluation	✅ Yes
CMMI-DEV V2.0	Capability Maturity Model Integration	✅ Level 5
ISO 26262	Automotive functional safety (axioms)	✅ Partial
DO-178C	Avionics software (axioms)	✅ Partial
MISRA C/C++	Coding standards (axioms)	✅ Partial
PCI DSS v4.0	Payment security (axioms)	✅ Partial
NIST SP 800-53	Security controls (axioms)	✅ Partial
🤝 Contributing
Run the test suite: python3 tests/orchestrator/test_complete.py

Ensure all tests pass or are properly documented

Add new language adapters to modules/toolchain_adapters/

Update this documentation

📄 License
Proprietary — AICHIP Corporation

👤 Author
Dennis T.Y. Leo

🔗 Related Documentation
AXIOM REPO — Complete axiom repository (33 axioms)

Placement Spec — UI placement specification

Software Debugger — Self-contained software debugger

Version: 3.0
Last Updated: 2026-04-14
