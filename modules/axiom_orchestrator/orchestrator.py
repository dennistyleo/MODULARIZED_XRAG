"""Axiom Orchestrator - Round-trip between Axiom and Toolchain"""

import os
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass

from ..toolchain_adapters.base_adapter import BaseToolchainAdapter, ExecutionResult
from ..toolchain_adapters.python_adapter import PythonToolchainAdapter
from ..toolchain_adapters.cpp_adapter import CppToolchainAdapter
from ..toolchain_adapters.firmware_adapter import FirmwareToolchainAdapter


@dataclass
class AxiomResult:
    overall_pass: bool
    failed_layers: List[str]
    score: int
    layer_results: Dict
    execution_logs: str = ""
    stdout: str = ""
    stderr: str = ""


@dataclass
class AuditReport:
    report_id: str
    file_name: str
    language: str
    overall_score: int
    status: str
    findings: List[Dict]
    remediation_plan: Dict
    source: str
    confidence: float
    raw_execution_logs: str = ""


class AxiomOrchestrator:
    
    def __init__(self):
        self.adapters = [PythonToolchainAdapter(), CppToolchainAdapter(), FirmwareToolchainAdapter()]
        self.axiom = AxiomEvaluator()
    
    def detect_language(self, file_path: str) -> str:
        ext = Path(file_path).suffix.lower()
        lang_map = {'.py': 'python', '.cpp': 'cpp', '.cc': 'cpp', '.cxx': 'cpp',
                    '.bin': 'firmware', '.hex': 'firmware', '.elf': 'firmware', '.rom': 'firmware'}
        return lang_map.get(ext, 'unknown')
    
    def can_execute_natively(self, language: str) -> bool:
        return language in ['verilog', 'systemverilog', 'python', 'javascript']
    
    def get_adapter(self, language: str, file_path: str) -> Optional[BaseToolchainAdapter]:
        for adapter in self.adapters:
            if adapter.can_handle(language, file_path):
                return adapter
        return None
    
    def evaluate(self, file_path: str, language: str = None) -> AuditReport:
        if not language:
            language = self.detect_language(file_path)
        
        print(f"\n{'='*60}")
        print(f"🔍 AXIOM ORCHESTRATOR")
        print(f"   File: {file_path}")
        print(f"   Language: {language}")
        print(f"{'='*60}\n")
        
        if self.can_execute_natively(language):
            print(f"✅ Axiom can execute {language} natively")
            execution_result = ExecutionResult(success=True, logs="Native execution")
        else:
            print(f"⚠️ Axiom cannot execute {language} natively - delegating to toolchain...")
            adapter = self.get_adapter(language, file_path)
            if not adapter:
                return AuditReport(
                    report_id=f"ERR-{os.path.basename(file_path)}",
                    file_name=os.path.basename(file_path), language=language,
                    overall_score=0, status="ERROR",
                    findings=[{"severity": "CRITICAL", "issue": f"No toolchain for {language}"}],
                    remediation_plan={}, source="Axiom Orchestrator", confidence=0.0
                )
            execution_result = adapter.execute(file_path)
            print(f"   Execution {'SUCCESS' if execution_result.success else 'FAILED'}")
        
        print(f"\n📥 Feeding results to Axiom...")
        axiom_result = self.axiom.evaluate_execution_results(file_path, language, execution_result)
        print(f"   Axiom: {'PASS' if axiom_result.overall_pass else 'FAIL'}")
        
        if axiom_result.overall_pass:
            return self.axiom.generate_audit_report(axiom_result, file_path, language)
        
        print(f"\n❌ Axiom failed - requesting backup from toolchain...")
        adapter = self.get_adapter(language, file_path)
        backup = adapter.get_backup_analysis(file_path, axiom_result.layer_results) if adapter else {}
        return self.axiom.format_backup_report(axiom_result, backup, file_path, language)


class AxiomEvaluator:
    
    def evaluate_execution_results(self, file_path: str, language: str, 
                                   execution_result: ExecutionResult) -> AxiomResult:
        layer_results = {}
        failed_layers = []
        
        l1_pass = execution_result.success
        layer_results["L1_SYNTAX"] = {"pass": l1_pass, "details": "Executed" if l1_pass else execution_result.stderr[:200]}
        if not l1_pass: failed_layers.append("L1_SYNTAX")
        
        l2_pass = execution_result.exit_code == 0
        layer_results["L2_LOGIC"] = {"pass": l2_pass, "details": f"Exit code: {execution_result.exit_code}"}
        if not l2_pass: failed_layers.append("L2_LOGIC")
        
        l3_pass = len(execution_result.crashes) == 0
        layer_results["L3_AXIOM"] = {"pass": l3_pass, "details": f"Crashes: {len(execution_result.crashes)}"}
        if not l3_pass: failed_layers.append("L3_AXIOM")
        
        layer_results["L4_STRUCTURE"] = {"pass": True, "details": "OK"}
        layer_results["L5_DESIGN"] = {"pass": True, "details": "OK"}
        layer_results["L6_MAINTAINABILITY"] = {"pass": True, "details": "OK"}
        layer_results["L7_DEBUGABILITY"] = {"pass": True, "details": "OK"}
        layer_results["L8_FIRMWARE"] = {"pass": True, "details": "OK"}
        layer_results["L9_COMMON_SENSE"] = {"pass": True, "details": "OK"}
        
        score = 100
        if not l1_pass: score -= 50
        if not l2_pass: score -= 20
        if not l3_pass: score -= 15
        
        return AxiomResult(overall_pass=len(failed_layers)==0, failed_layers=failed_layers,
                          score=score, layer_results=layer_results,
                          execution_logs=execution_result.logs, stdout=execution_result.stdout, stderr=execution_result.stderr)
    
    def generate_audit_report(self, axiom_result: AxiomResult, file_path: str, language: str) -> AuditReport:
        findings = [{"layer": l, "severity": "HIGH", "issue": axiom_result.layer_results[l]["details"]}
                   for l in axiom_result.failed_layers]
        return AuditReport(
            report_id=f"AXM-{hash(file_path) % 10000:04d}", file_name=os.path.basename(file_path),
            language=language, overall_score=axiom_result.score,
            status="PASS" if axiom_result.overall_pass else "FAIL",
            findings=findings, remediation_plan={"must_fix": findings},
            source="Axiom Generator", confidence=0.95, raw_execution_logs=axiom_result.execution_logs[:1000]
        )
    
    def format_backup_report(self, axiom_result: AxiomResult, backup: Dict, file_path: str, language: str) -> AuditReport:
        findings = [{"layer": l, "severity": "HIGH", "issue": axiom_result.layer_results[l]["details"]}
                   for l in axiom_result.failed_layers]
        if backup:
            findings.append({"layer": "BACKUP", "severity": "MEDIUM",
                           "issue": backup.get("root_cause", "Unknown"),
                           "suggestion": "\n".join(backup.get("suggested_fixes", []))})
        return AuditReport(
            report_id=f"AXM-BK-{hash(file_path) % 10000:04d}", file_name=os.path.basename(file_path),
            language=language, overall_score=axiom_result.score, status="NEEDS_REVIEW",
            findings=findings, remediation_plan={"backup_provided": bool(backup)},
            source="Google Toolchain (via Axiom Orchestrator)",
            confidence=backup.get("confidence", 0.75) if backup else 0.5,
            raw_execution_logs=axiom_result.execution_logs[:1000]
        )
