#!/usr/bin/env python3
"""Complete Axiom Evaluator - L1 through L9 with toolchain fallback for missing tools"""

import os
import sys
import subprocess
import tempfile
import re
import ast
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

# ============================================================
# DATA CLASSES
# ============================================================

@dataclass
class AxiomViolation:
    """Single axiom violation"""
    axiom_id: str
    axiom_name: str
    category: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    description: str
    location: Optional[str] = None
    suggestion: Optional[str] = None


@dataclass
class LayerResult:
    """Result for a single layer (L1-L9)"""
    layer: str
    name: str
    passed: bool
    score: int
    violations: List[AxiomViolation] = field(default_factory=list)
    details: str = ""
    tool_used: str = "Axiom Generator"


@dataclass
class FullAuditReport:
    """Complete audit report with all 9 layers"""
    report_id: str
    file_name: str
    language: str
    timestamp: str
    overall_score: int
    overall_grade: str
    overall_status: str
    layers: List[LayerResult]
    summary: Dict
    remediation_plan: Dict
    toolchain_fallbacks_used: List[str] = field(default_factory=list)


# ============================================================
# TOOLCHAIN DETECTION AND FALLBACK
# ============================================================

class ToolchainManager:
    """Detects available tools and provides fallbacks"""
    
    @staticmethod
    def is_tool_available(tool_name: str) -> bool:
        """Check if a tool is installed"""
        try:
            result = subprocess.run(
                [tool_name, "--version"] if tool_name != "iverilog" else [tool_name, "-V"],
                capture_output=True, timeout=5
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
    
    @staticmethod
    def get_fallback_message(tool_name: str, purpose: str) -> str:
        """Generate fallback message when tool is missing"""
        install_commands = {
            "iverilog": "brew install icarus-verilog  # macOS\nsudo apt-get install iverilog  # Ubuntu",
            "playwright": "pip install playwright && playwright install chromium",
            "qemu": "brew install qemu  # macOS\nsudo apt-get install qemu-system-x86  # Ubuntu",
            "g++": "brew install gcc  # macOS\nsudo apt-get install g++  # Ubuntu"
        }
        return f"⚠️ {tool_name} not installed. {purpose} will use fallback analysis. Install with:\n  {install_commands.get(tool_name, 'Check documentation')}"


# ============================================================
# L1: SYNTAX EVALUATION
# ============================================================

class L1SyntaxEvaluator:
    """Evaluate syntax correctness"""
    
    def evaluate(self, file_path: str, language: str) -> LayerResult:
        violations = []
        
        if language == "python":
            return self._eval_python(file_path)
        elif language in ["verilog", "systemverilog"]:
            return self._eval_verilog(file_path)
        elif language == "cpp":
            return self._eval_cpp(file_path)
        elif language == "javascript":
            return self._eval_javascript(file_path)
        else:
            return LayerResult(
                layer="L1", name="Syntax", passed=False, score=0,
                violations=[AxiomViolation(
                    axiom_id="SYNTAX_001", axiom_name="Language Support",
                    category="Syntax", severity="MEDIUM",
                    description=f"Language '{language}' not fully supported",
                    suggestion="Use Python, Verilog, C++, or JavaScript"
                )],
                details=f"Unsupported language: {language}"
            )
    
    def _eval_python(self, file_path: str) -> LayerResult:
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            ast.parse(content)
            return LayerResult(layer="L1", name="Syntax", passed=True, score=100,
                              details="Python syntax is valid")
        except SyntaxError as e:
            return LayerResult(layer="L1", name="Syntax", passed=False, score=0,
                              violations=[AxiomViolation(
                                  axiom_id="SYNTAX_001", axiom_name="Python Syntax Error",
                                  category="Syntax", severity="CRITICAL",
                                  description=str(e), location=f"Line {e.lineno}",
                                  suggestion=f"Fix syntax at line {e.lineno}: {e.text}"
                              )],
                              details=f"Syntax error: {e}")
    
    def _eval_verilog(self, file_path: str) -> LayerResult:
        if ToolchainManager.is_tool_available("iverilog"):
            result = subprocess.run(
                ["iverilog", "-o", "/dev/null", file_path],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                return LayerResult(layer="L1", name="Syntax", passed=True, score=100,
                                  details="Verilog syntax is valid", tool_used="iverilog")
            else:
                return LayerResult(layer="L1", name="Syntax", passed=False, score=0,
                                  violations=[AxiomViolation(
                                      axiom_id="SYNTAX_002", axiom_name="Verilog Syntax Error",
                                      category="Syntax", severity="CRITICAL",
                                      description=result.stderr[:500],
                                      suggestion="Fix Verilog syntax errors"
                                  )],
                                  details=result.stderr[:200], tool_used="iverilog")
        else:
            # Fallback: basic regex syntax check
            with open(file_path, 'r') as f:
                content = f.read()
            
            violations = []
            if not re.search(r'module\s+\w+', content):
                violations.append(AxiomViolation(
                    axiom_id="SYNTAX_002", axiom_name="Missing Module Declaration",
                    category="Syntax", severity="CRITICAL",
                    description="No 'module ...' declaration found",
                    suggestion="Add module declaration: module name (ports);"
                ))
            if content.count('(') != content.count(')'):
                violations.append(AxiomViolation(
                    axiom_id="SYNTAX_003", axiom_name="Unbalanced Parentheses",
                    category="Syntax", severity="HIGH",
                    description=f"Parentheses mismatch: {content.count('(')} open, {content.count(')')} close",
                    suggestion="Balance all parentheses"
                ))
            
            passed = len(violations) == 0
            return LayerResult(
                layer="L1", name="Syntax", passed=passed,
                score=100 if passed else 30,
                violations=violations,
                details="Fallback syntax check (iverilog not installed)",
                tool_used="Fallback Regex Check"
            )
    
    def _eval_cpp(self, file_path: str) -> LayerResult:
        if ToolchainManager.is_tool_available("g++"):
            result = subprocess.run(
                ["g++", "-fsyntax-only", file_path],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                return LayerResult(layer="L1", name="Syntax", passed=True, score=100,
                                  details="C++ syntax is valid", tool_used="g++")
            else:
                return LayerResult(layer="L1", name="Syntax", passed=False, score=0,
                                  violations=[AxiomViolation(
                                      axiom_id="SYNTAX_004", axiom_name="C++ Syntax Error",
                                      category="Syntax", severity="CRITICAL",
                                      description=result.stderr[:500],
                                      suggestion="Fix C++ syntax errors"
                                  )],
                                  details=result.stderr[:200], tool_used="g++")
        else:
            return LayerResult(
                layer="L1", name="Syntax", passed=False, score=0,
                violations=[AxiomViolation(
                    axiom_id="SYNTAX_004", axiom_name="C++ Compiler Missing",
                    category="Syntax", severity="HIGH",
                    description="g++ not installed",
                    suggestion="Install g++: brew install gcc (macOS) or sudo apt-get install g++ (Ubuntu)"
                )],
                details="C++ compilation requires g++",
                tool_used="None (fallback failed)"
            )
    
    def _eval_javascript(self, file_path: str) -> LayerResult:
        # Basic JS syntax check (Node.js not required for basic check)
        with open(file_path, 'r') as f:
            content = f.read()
        
        violations = []
        if content.count('{') != content.count('}'):
            violations.append(AxiomViolation(
                axiom_id="SYNTAX_005", axiom_name="Unbalanced Braces",
                category="Syntax", severity="HIGH",
                description="Braces {} are not balanced",
                suggestion="Balance all braces"
            ))
        
        passed = len(violations) == 0
        return LayerResult(
            layer="L1", name="Syntax", passed=passed,
            score=100 if passed else 50,
            violations=violations,
            details="Basic JavaScript syntax check",
            tool_used="Regex Check"
        )


# ============================================================
# L2: LOGIC EVALUATION
# ============================================================

class L2LogicEvaluator:
    """Evaluate algorithm correctness, control flow, data flow"""
    
    def evaluate(self, file_path: str, language: str) -> LayerResult:
        violations = []
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        if language == "python":
            # Check for common logic errors
            if "while True:" in content and "break" not in content:
                violations.append(AxiomViolation(
                    axiom_id="LOGIC_001", axiom_name="Potential Infinite Loop",
                    category="Logic", severity="CRITICAL",
                    description="while True: without break may cause infinite loop",
                    suggestion="Add break condition or timeout"
                ))
            
            if "except:" in content and "Exception" not in content:
                violations.append(AxiomViolation(
                    axiom_id="LOGIC_002", axiom_name="Bare Exception",
                    category="Logic", severity="HIGH",
                    description="except: catches all exceptions including SystemExit",
                    suggestion="Use 'except Exception as e:' instead"
                ))
            
            if re.search(r'return\s+.*\s+or\s+.*\s+or', content):
                violations.append(AxiomViolation(
                    axiom_id="LOGIC_003", axiom_name="Complex Boolean Logic",
                    category="Logic", severity="MEDIUM",
                    description="Complex OR chain may hide logic errors",
                    suggestion="Break into multiple conditions"
                ))
        
        elif language in ["verilog", "systemverilog"]:
            # Check for common Verilog logic issues
            if "always @" in content and "begin" not in content:
                violations.append(AxiomViolation(
                    axiom_id="LOGIC_004", axiom_name="Missing begin/end",
                    category="Logic", severity="HIGH",
                    description="always block missing begin/end for multiple statements",
                    suggestion="Add begin/end around multiple statements"
                ))
            
            if "=" in content and "<=" in content and "always @(posedge" in content:
                violations.append(AxiomViolation(
                    axiom_id="LOGIC_005", axiom_name="Mixed Blocking/Non-blocking",
                    category="Logic", severity="CRITICAL",
                    description="Mixed = and <= in sequential always block",
                    suggestion="Use <= for sequential logic, = for combinational"
                ))
        
        passed = len(violations) == 0
        score = 100 - sum(20 for v in violations if v.severity == "CRITICAL") - sum(10 for v in violations if v.severity == "HIGH") - sum(5 for v in violations if v.severity == "MEDIUM")
        score = max(0, score)
        
        return LayerResult(
            layer="L2", name="Logic", passed=passed, score=score,
            violations=violations,
            details=f"Found {len(violations)} logic issues",
            tool_used="Static Analysis"
        )


# ============================================================
# L3: AXIOM COMPLIANCE (Causality, Determinism, Conservation)
# ============================================================

class L3AxiomEvaluator:
    """Evaluate against physical/ontological axioms"""
    
    AXIOMS = {
        "CAUSAL_001": {"name": "Conservation of Causality", "severity": "CRITICAL",
                       "description": "Every effect must have a traceable cause"},
        "CAUSAL_002": {"name": "Temporal Ordering", "severity": "HIGH",
                       "description": "Causes must precede effects in time"},
        "DET_001": {"name": "Deterministic Output", "severity": "HIGH",
                    "description": "Same input must produce same output"},
        "RES_001": {"name": "Conservation of Memory", "severity": "HIGH",
                    "description": "Every allocation must have deallocation"},
        "DATA_001": {"name": "Input Validation", "severity": "CRITICAL",
                     "description": "All external inputs must be validated"}
    }
    
    def evaluate(self, file_path: str, language: str) -> LayerResult:
        violations = []
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check for causality violations
        if "random" in content.lower() and "seed" not in content.lower():
            violations.append(AxiomViolation(
                axiom_id="CAUSAL_001", axiom_name=self.AXIOMS["CAUSAL_001"]["name"],
                category="Axiom", severity="HIGH",
                description="Random without seed may cause non-deterministic behavior",
                suggestion="Set random seed for reproducibility"
            ))
        
        # Check for memory conservation (Python)
        if language == "python":
            open_count = content.count('open(')
            close_count = content.count('.close()')
            if open_count > close_count:
                violations.append(AxiomViolation(
                    axiom_id="RES_001", axiom_name=self.AXIOMS["RES_001"]["name"],
                    category="Axiom", severity="HIGH",
                    description=f"Potential resource leak: {open_count} opens, {close_count} closes",
                    suggestion="Use 'with open() as f:' context manager"
                ))
        
        # Check for input validation
        if "input(" in content and "try:" not in content:
            violations.append(AxiomViolation(
                axiom_id="DATA_001", axiom_name=self.AXIOMS["DATA_001"]["name"],
                category="Axiom", severity="CRITICAL",
                description="User input without validation or error handling",
                suggestion="Wrap input() in try/except and validate values"
            ))
        
        # Check for temporal ordering (race conditions in threads)
        if "Thread" in content and "lock" not in content.lower():
            violations.append(AxiomViolation(
                axiom_id="CAUSAL_002", axiom_name=self.AXIOMS["CAUSAL_002"]["name"],
                category="Axiom", severity="HIGH",
                description="Threads used without locks - potential race condition",
                suggestion="Add threading.Lock() to synchronize shared data"
            ))
        
        passed = len(violations) == 0
        score = 100 - sum(30 for v in violations if v.severity == "CRITICAL") - sum(15 for v in violations if v.severity == "HIGH")
        score = max(0, score)
        
        return LayerResult(
            layer="L3", name="Axiom Compliance", passed=passed, score=score,
            violations=violations,
            details=f"Axiom violations: {len(violations)}",
            tool_used="Axiom Rule Engine"
        )


# ============================================================
# L4: STRUCTURAL REASONABLENESS
# ============================================================

class L4StructuralEvaluator:
    """Evaluate architecture, complexity, coupling"""
    
    def evaluate(self, file_path: str, language: str) -> LayerResult:
        violations = []
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Calculate cyclomatic complexity proxy (function count, branch count)
        lines = len(content.split('\n'))
        if_count = content.count('if ')
        for_count = content.count('for ')
        while_count = content.count('while ')
        
        complexity = if_count + for_count + while_count
        complexity_score = max(0, 100 - complexity * 2)
        
        if complexity > 20:
            violations.append(AxiomViolation(
                axiom_id="STRUCT_001", axiom_name="High Cyclomatic Complexity",
                category="Structure", severity="MEDIUM",
                description=f"Complexity score ~{complexity} (threshold: 20)",
                suggestion="Refactor into smaller functions"
            ))
        
        # Check function length (proxy)
        functions = re.findall(r'def\s+\w+\s*\([^)]*\):', content)
        if len(functions) > 0:
            avg_func_length = len(content) / max(len(functions), 1)
            if avg_func_length > 200:
                violations.append(AxiomViolation(
                    axiom_id="STRUCT_002", axiom_name="Long Functions",
                    category="Structure", severity="LOW",
                    description=f"Average function length ~{avg_func_length:.0f} lines",
                    suggestion="Break long functions into smaller ones"
                ))
        
        # Check nesting depth
        max_indent = 0
        for line in content.split('\n'):
            indent = len(line) - len(line.lstrip())
            if indent > max_indent and line.strip():
                max_indent = indent
        nest_depth = max_indent // 4
        if nest_depth > 4:
            violations.append(AxiomViolation(
                axiom_id="STRUCT_003", axiom_name="Deep Nesting",
                category="Structure", severity="MEDIUM",
                description=f"Nesting depth ~{nest_depth} levels (recommended: <4)",
                suggestion="Restructure nested conditionals"
            ))
        
        passed = len(violations) == 0
        score = complexity_score
        
        return LayerResult(
            layer="L4", name="Structural Reasonableness", passed=passed, score=score,
            violations=violations,
            details=f"Complexity: {complexity}, Nesting: {nest_depth}",
            tool_used="Static Analysis"
        )


# ============================================================
# L5: DESIGN METHODOLOGY
# ============================================================

class L5DesignEvaluator:
    """Evaluate against design patterns and SOLID principles"""
    
    def evaluate(self, file_path: str, language: str) -> LayerResult:
        violations = []
        good_patterns = []
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Detect good patterns
        if "class " in content:
            if "Singleton" in content or re.search(r'class\s+\w+Singleton', content):
                good_patterns.append("Singleton pattern detected")
            if "Factory" in content:
                good_patterns.append("Factory pattern detected")
            if "Observer" in content:
                good_patterns.append("Observer pattern detected")
        
        # Detect anti-patterns
        if "global " in content:
            violations.append(AxiomViolation(
                axiom_id="DESIGN_001", axiom_name="Global Variables",
                category="Design", severity="MEDIUM",
                description="Global variables reduce testability",
                suggestion="Encapsulate in class or pass as parameters"
            ))
        
        if len(re.findall(r'def\s+\w+\s*\([^,)]*,[^,)]*,[^,)]*,[^,)]*,[^,)]*\)', content)) > 0:
            violations.append(AxiomViolation(
                axiom_id="DESIGN_002", axiom_name="Too Many Parameters",
                category="Design", severity="LOW",
                description="Function with >5 parameters",
                suggestion="Group parameters into a class or use named arguments"
            ))
        
        if "except:" in content and "Exception" not in content:
            violations.append(AxiomViolation(
                axiom_id="DESIGN_003", axiom_name="Bare Except",
                category="Design", severity="HIGH",
                description="Bare except hides errors",
                suggestion="Specify exception type"
            ))
        
        score = 100 - len(violations) * 10
        score = max(0, score)
        
        details = f"Good patterns: {', '.join(good_patterns) if good_patterns else 'None detected'}"
        
        return LayerResult(
            layer="L5", name="Design Methodology", passed=len(violations) == 0, score=score,
            violations=violations, details=details,
            tool_used="Pattern Detection"
        )


# ============================================================
# L6: MAINTAINABILITY
# ============================================================

class L6MaintainabilityEvaluator:
    """Evaluate comment density, function length, naming consistency"""
    
    def evaluate(self, file_path: str, language: str) -> LayerResult:
        violations = []
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        lines = content.split('\n')
        total_lines = len(lines)
        
        # Comment density
        comment_lines = sum(1 for line in lines if line.strip().startswith('#') or line.strip().startswith('//'))
        comment_density = (comment_lines / max(total_lines, 1)) * 100
        
        if comment_density < 10:
            violations.append(AxiomViolation(
                axiom_id="MAINT_001", axiom_name="Low Comment Density",
                category="Maintainability", severity="MEDIUM",
                description=f"Only {comment_density:.1f}% comments (recommended: >15%)",
                suggestion="Add documentation comments for complex logic"
            ))
        
        # Magic numbers
        magic_numbers = re.findall(r'\b\d{2,}\b', content)
        magic_numbers = [n for n in magic_numbers if n not in ['0', '1', '100'] and not re.search(r'\d{4}-\d{2}-\d{2}', content)]
        if len(magic_numbers) > 5:
            violations.append(AxiomViolation(
                axiom_id="MAINT_002", axiom_name="Magic Numbers",
                category="Maintainability", severity="LOW",
                description=f"{len(magic_numbers)} magic numbers found",
                suggestion="Define named constants for numeric literals"
            ))
        
        score = int(comment_density * 2) if comment_density < 50 else 100
        score = min(100, score)
        
        return LayerResult(
            layer="L6", name="Maintainability", passed=comment_density >= 10, score=score,
            violations=violations,
            details=f"Comment density: {comment_density:.1f}%, Magic numbers: {len(magic_numbers)}",
            tool_used="Static Analysis"
        )


# ============================================================
# L7: DEBUGABILITY (Testability, Serviceability, Scalability, Extendibility)
# ============================================================

class L7DebugabilityEvaluator:
    """Evaluate testability, serviceability, scalability, extendibility"""
    
    def evaluate(self, file_path: str, language: str) -> LayerResult:
        violations = []
        metrics = {}
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Testability
        has_tests = "test_" in content or "pytest" in content or "unittest" in content
        has_assert = "assert" in content
        testability_score = 100 if has_tests and has_assert else 50 if has_assert else 25
        
        if not has_tests:
            violations.append(AxiomViolation(
                axiom_id="DEBUG_001", axiom_name="No Tests Detected",
                category="Debugability", severity="MEDIUM",
                description="No unit tests found",
                suggestion="Add test files or use pytest/unittest"
            ))
        
        # Serviceability (logging)
        has_logging = "logging." in content or "print(" in content
        serviceability_score = 100 if has_logging else 50
        
        if not has_logging:
            violations.append(AxiomViolation(
                axiom_id="DEBUG_002", axiom_name="No Logging",
                category="Debugability", severity="LOW",
                description="No logging statements found",
                suggestion="Add logging for production monitoring"
            ))
        
        # Scalability
        has_global = "global " in content
        has_state = "self." in content or "this." in content
        scalability_score = 70 if has_global else 90 if has_state else 80
        
        if has_global:
            violations.append(AxiomViolation(
                axiom_id="DEBUG_003", axiom_name="Global State",
                category="Debugability", severity="MEDIUM",
                description="Global variables hinder parallel execution",
                suggestion="Encapsulate state in objects"
            ))
        
        # Extendibility
        has_classes = "class " in content
        has_interfaces = "ABC" in content or "abstract" in content
        extendibility_score = 90 if has_classes and has_interfaces else 70 if has_classes else 50
        
        if not has_classes:
            violations.append(AxiomViolation(
                axiom_id="DEBUG_004", axiom_name="No Object Orientation",
                category="Debugability", severity="LOW",
                description="No classes found, may limit extensibility",
                suggestion="Consider OOP design for extensibility"
            ))
        
        overall_score = int((testability_score + serviceability_score + scalability_score + extendibility_score) / 4)
        
        return LayerResult(
            layer="L7", name="Debugability", passed=overall_score >= 60, score=overall_score,
            violations=violations,
            details=f"Testability: {testability_score}, Serviceability: {serviceability_score}, Scalability: {scalability_score}, Extendibility: {extendibility_score}",
            tool_used="Quality Metrics"
        )


# ============================================================
# L8: FIRMWARE EVALUATION (BIOS, EC, UEFI)
# ============================================================

class L8FirmwareEvaluator:
    """Evaluate firmware-specific code (BIOS, EC, UEFI)"""
    
    FIRMWARE_AXIOMS = {
        "FW_001": {"name": "POST Sequence Integrity", "severity": "CRITICAL",
                   "description": "Power-on self-test must complete in correct order"},
        "FW_002": {"name": "Interrupt Vector Table Validity", "severity": "CRITICAL",
                   "description": "All interrupt vectors must point to valid handlers"},
        "FW_003": {"name": "Secure Boot Chain", "severity": "CRITICAL",
                   "description": "Boot chain must be cryptographically verified"},
        "FW_004": {"name": "Watchdog Timer", "severity": "HIGH",
                   "description": "Critical loops must reset watchdog timer"}
    }
    
    def evaluate(self, file_path: str, language: str) -> LayerResult:
        violations = []
        
        # Detect if this is firmware
        is_firmware = file_path.endswith(('.bin', '.hex', '.elf', '.rom')) or "bios" in file_path.lower() or "uefi" in file_path.lower()
        
        if not is_firmware:
            return LayerResult(
                layer="L8", name="Firmware", passed=True, score=100,
                details="Not a firmware file (skipped)",
                tool_used="N/A"
            )
        
        with open(file_path, 'rb') as f:
            content = f.read()
        
        # Check for valid binary header
        if len(content) < 512:
            violations.append(AxiomViolation(
                axiom_id="FW_001", axiom_name=self.FIRMWARE_AXIOMS["FW_001"]["name"],
                category="Firmware", severity="CRITICAL",
                description=f"Firmware too small ({len(content)} bytes)",
                suggestion="Valid firmware should be at least 512 bytes"
            ))
        
        # Check for known firmware signatures
        if content[:4] == b'\x7fELF':
            # ELF format (UEFI applications)
            violations.append(AxiomViolation(
                axiom_id="FW_003", axiom_name=self.FIRMWARE_AXIOMS["FW_003"]["name"],
                category="Firmware", severity="HIGH",
                description="ELF format detected - Secure Boot verification required",
                suggestion="Ensure image is signed and verified at load time"
            ))
        
        # Check for UEFI GUIDs
        uefi_pattern = re.compile(rb'{[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}}', re.IGNORECASE)
        if uefi_pattern.search(content):
            violations.append(AxiomViolation(
                axiom_id="FW_004", axiom_name=self.FIRMWARE_AXIOMS["FW_004"]["name"],
                category="Firmware", severity="MEDIUM",
                description="UEFI GUIDs detected - watchdog timer recommended",
                suggestion="Implement watchdog timer for critical sections"
            ))
        
        passed = len(violations) == 0
        score = 100 - sum(30 for v in violations if v.severity == "CRITICAL") - sum(15 for v in violations if v.severity == "HIGH")
        score = max(0, score)
        
        return LayerResult(
            layer="L8", name="Firmware", passed=passed, score=score,
            violations=violations,
            details=f"Firmware analysis: {len(violations)} issues",
            tool_used="Binary Analysis"
        )


# ============================================================
# L9: COMMON SENSE
# ============================================================

class L9CommonSenseEvaluator:
    """Evaluate practical reasonableness"""
    
    def evaluate(self, file_path: str, language: str) -> LayerResult:
        violations = []
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Check for zero timeouts
        if "timeout=0" in content or "timeout = 0" in content:
            violations.append(AxiomViolation(
                axiom_id="CS_001", axiom_name="Zero Timeout",
                category="Common Sense", severity="HIGH",
                description="Timeout set to 0 - will never wait",
                suggestion="Set positive timeout value"
            ))
        
        # Check for hardcoded credentials
        credentials = re.findall(r'(password|secret|key|token)\s*=\s*[\'"](\w+)[\'"]', content, re.IGNORECASE)
        if credentials:
            violations.append(AxiomViolation(
                axiom_id="CS_002", axiom_name="Hardcoded Credentials",
                category="Common Sense", severity="CRITICAL",
                description=f"Hardcoded {credentials[0][0]} detected",
                suggestion="Use environment variables or secrets manager"
            ))
        
        # Check for infinite retry loops
        if "while True:" in content and "retry" in content and "break" not in content:
            violations.append(AxiomViolation(
                axiom_id="CS_003", axiom_name="Infinite Retry",
                category="Common Sense", severity="HIGH",
                description="Infinite retry loop without break condition",
                suggestion="Add max retries and exponential backoff"
            ))
        
        # Check for unreasonable buffer sizes
        small_buffers = re.findall(r'\[(\d+)\]', content)
        for buf in small_buffers:
            if int(buf) == 1:
                violations.append(AxiomViolation(
                    axiom_id="CS_004", axiom_name="1-byte Buffer",
                    category="Common Sense", severity="MEDIUM",
                    description="1-byte buffer may be insufficient",
                    suggestion="Increase buffer size"
                ))
                break
        
        passed = len(violations) == 0
        score = 100 - sum(30 for v in violations if v.severity == "CRITICAL") - sum(15 for v in violations if v.severity == "HIGH") - sum(5 for v in violations if v.severity == "MEDIUM")
        score = max(0, score)
        
        return LayerResult(
            layer="L9", name="Common Sense", passed=passed, score=score,
            violations=violations,
            details=f"Common sense issues: {len(violations)}",
            tool_used="Rule Check"
        )


# ============================================================
# MAIN ORCHESTRATOR
# ============================================================

class FullAxiomOrchestrator:
    """Complete orchestrator with all 9 layers and toolchain fallback"""
    
    def __init__(self):
        self.evaluators = {
            "L1": L1SyntaxEvaluator(),
            "L2": L2LogicEvaluator(),
            "L3": L3AxiomEvaluator(),
            "L4": L4StructuralEvaluator(),
            "L5": L5DesignEvaluator(),
            "L6": L6MaintainabilityEvaluator(),
            "L7": L7DebugabilityEvaluator(),
            "L8": L8FirmwareEvaluator(),
            "L9": L9CommonSenseEvaluator(),
        }
        self.toolchain_fallbacks = []
    
    def detect_language(self, file_path: str) -> str:
        ext = Path(file_path).suffix.lower()
        lang_map = {
            '.py': 'python', '.cpp': 'cpp', '.cc': 'cpp', '.cxx': 'cpp',
            '.v': 'verilog', '.sv': 'systemverilog',
            '.js': 'javascript', '.html': 'web', '.json': 'json',
            '.bin': 'firmware', '.hex': 'firmware', '.elf': 'firmware', '.rom': 'firmware'
        }
        return lang_map.get(ext, 'unknown')
    
    def evaluate(self, file_path: str, language: str = None) -> FullAuditReport:
        if not language:
            language = self.detect_language(file_path)
        
        print(f"\n{'='*70}")
        print(f"🔍 AXIOM ORCHESTRATOR v3.0 - Full Evaluation")
        print(f"   File: {os.path.basename(file_path)}")
        print(f"   Language: {language}")
        print(f"{'='*70}\n")
        
        layer_results = []
        total_score = 0
        weights = {"L1": 5, "L2": 15, "L3": 15, "L4": 10, "L5": 10, "L6": 10, "L7": 15, "L8": 10, "L9": 10}
        
        for layer in ["L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8", "L9"]:
            print(f"📋 Evaluating {layer}...")
            result = self.evaluators[layer].evaluate(file_path, language)
            layer_results.append(result)
            total_score += result.score * (weights[layer] / 100)
            print(f"   Score: {result.score}/100 | {'✅ PASS' if result.passed else '❌ FAIL'}")
            if result.violations:
                for v in result.violations[:3]:
                    print(f"     - [{v.severity}] {v.axiom_name}: {v.description[:60]}")
            if result.tool_used != "Axiom Generator":
                self.toolchain_fallbacks.append(f"{layer}: {result.tool_used}")
        
        overall_score = int(total_score)
        
        if overall_score >= 90:
            overall_grade = "A+"
            overall_status = "EXCELLENT"
        elif overall_score >= 80:
            overall_grade = "A"
            overall_status = "VERY GOOD"
        elif overall_score >= 70:
            overall_grade = "B"
            overall_status = "GOOD"
        elif overall_score >= 60:
            overall_grade = "C"
            overall_status = "NEEDS IMPROVEMENT"
        elif overall_score >= 50:
            overall_grade = "D"
            overall_status = "POOR"
        else:
            overall_grade = "F"
            overall_status = "CRITICAL"
        
        # Generate summary
        summary = {
            "total_layers": 9,
            "passed_layers": sum(1 for r in layer_results if r.passed),
            "failed_layers": sum(1 for r in layer_results if not r.passed),
            "total_violations": sum(len(r.violations) for r in layer_results),
            "critical_violations": sum(1 for r in layer_results for v in r.violations if v.severity == "CRITICAL"),
            "high_violations": sum(1 for r in layer_results for v in r.violations if v.severity == "HIGH"),
        }
        
        # Generate remediation plan
        remediation_plan = {
            "must_fix_before_deployment": [
                {"layer": r.layer, "issue": v.axiom_name, "suggestion": v.suggestion}
                for r in layer_results for v in r.violations if v.severity == "CRITICAL"
            ],
            "should_fix_soon": [
                {"layer": r.layer, "issue": v.axiom_name, "suggestion": v.suggestion}
                for r in layer_results for v in r.violations if v.severity == "HIGH"
            ],
            "nice_to_have": [
                {"layer": r.layer, "issue": v.axiom_name, "suggestion": v.suggestion}
                for r in layer_results for v in r.violations if v.severity in ["MEDIUM", "LOW"]
            ]
        }
        
        return FullAuditReport(
            report_id=f"AXM-FULL-{hash(file_path) % 10000:04d}",
            file_name=os.path.basename(file_path),
            language=language,
            timestamp=datetime.now().isoformat(),
            overall_score=overall_score,
            overall_grade=overall_grade,
            overall_status=overall_status,
            layers=layer_results,
            summary=summary,
            remediation_plan=remediation_plan,
            toolchain_fallbacks_used=self.toolchain_fallbacks
        )
    
    def print_report(self, report: FullAuditReport):
        """Print full audit report"""
        print("\n" + "█"*70)
        print("█  AXIOM GENERATOR - FULL AUDIT REPORT")
        print("█"*70)
        print(f"   Report ID: {report.report_id}")
        print(f"   File: {report.file_name}")
        print(f"   Language: {report.language}")
        print(f"   Timestamp: {report.timestamp}")
        print(f"   Overall Score: {report.overall_score}/100")
        print(f"   Grade: {report.overall_grade}")
        print(f"   Status: {report.overall_status}")
        print(f"   Toolchain Fallbacks: {', '.join(report.toolchain_fallbacks) if report.toolchain_fallbacks else 'None'}")
        
        print("\n" + "-"*70)
        print("📊 LAYER SUMMARY")
        print("-"*70)
        print(f"   {'Layer':<6} {'Score':<8} {'Status':<12} {'Issues':<8}")
        print(f"   {'-'*6} {'-'*8} {'-'*12} {'-'*8}")
        for layer in report.layers:
            status_icon = "✅" if layer.passed else "❌"
            print(f"   {layer.layer:<6} {layer.score:<8} {status_icon} {layer.name:<11} {len(layer.violations)}")
        
        print("\n" + "-"*70)
        print("🔍 VIOLATIONS DETAIL")
        print("-"*70)
        for layer in report.layers:
            if layer.violations:
                print(f"\n   📌 {layer.layer}: {layer.name}")
                for v in layer.violations:
                    print(f"      [{v.severity}] {v.axiom_name}")
                    print(f"          → {v.description}")
                    if v.suggestion:
                        print(f"          🔧 Fix: {v.suggestion}")
        
        print("\n" + "-"*70)
        print("🔧 REMEDIATION PLAN")
        print("-"*70)
        
        if report.remediation_plan["must_fix_before_deployment"]:
            print(f"\n   🚨 MUST FIX BEFORE DEPLOYMENT ({len(report.remediation_plan['must_fix_before_deployment'])} items):")
            for item in report.remediation_plan["must_fix_before_deployment"][:5]:
                print(f"      - {item['layer']}: {item['issue']}")
                print(f"        → {item['suggestion']}")
        
        if report.remediation_plan["should_fix_soon"]:
            print(f"\n   ⚠️ SHOULD FIX SOON ({len(report.remediation_plan['should_fix_soon'])} items):")
            for item in report.remediation_plan["should_fix_soon"][:5]:
                print(f"      - {item['layer']}: {item['issue']}")
        
        print("\n" + "█"*70)
        print("█  END OF REPORT")
        print("█"*70)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python full_evaluator.py <file_path> [language]")
        sys.exit(1)
    
    file_path = sys.argv[1]
    language = sys.argv[2] if len(sys.argv) > 2 else None
    
    orchestrator = FullAxiomOrchestrator()
    report = orchestrator.evaluate(file_path, language)
    orchestrator.print_report(report)
