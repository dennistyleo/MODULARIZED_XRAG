#!/usr/bin/env python3
"""
ISO/IEC 25010 Compliant Axiom Generator
Maps 8 quality characteristics to L1-L9 evaluation layers
"""

import os
import re
import ast
import subprocess
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

# ============================================================
# ISO/IEC 25010 Quality Model
# ============================================================

@dataclass
class ISO25010Characteristic:
    """ISO/IEC 25010 quality characteristic"""
    name: str
    subcharacteristics: List[str]
    weight: int  # 1-10 importance weight
    axiom_layers: List[str]  # Which Axiom layers evaluate this


ISO_25010_MODEL = {
    "Functional Suitability": ISO25010Characteristic(
        name="Functional Suitability",
        subcharacteristics=["Functional completeness", "Functional correctness", "Functional appropriateness"],
        weight=10,
        axiom_layers=["L2", "L5"]
    ),
    "Performance Efficiency": ISO25010Characteristic(
        name="Performance Efficiency",
        subcharacteristics=["Time behaviour", "Resource utilization", "Capacity"],
        weight=8,
        axiom_layers=["L4", "L7"]
    ),
    "Compatibility": ISO25010Characteristic(
        name="Compatibility",
        subcharacteristics=["Co-existence", "Interoperability"],
        weight=6,
        axiom_layers=["L8", "L1"]
    ),
    "Usability": ISO25010Characteristic(
        name="Usability",
        subcharacteristics=["Appropriateness recognizability", "Learnability", "Operability", "User error protection", "User interface aesthetics", "Accessibility"],
        weight=7,
        axiom_layers=["L9", "L7"]
    ),
    "Reliability": ISO25010Characteristic(
        name="Reliability",
        subcharacteristics=["Maturity", "Availability", "Fault tolerance", "Recoverability"],
        weight=9,
        axiom_layers=["L3", "L2"]
    ),
    "Security": ISO25010Characteristic(
        name="Security",
        subcharacteristics=["Confidentiality", "Integrity", "Non-repudiation", "Accountability", "Authenticity"],
        weight=10,
        axiom_layers=["L3", "L9"]
    ),
    "Maintainability": ISO25010Characteristic(
        name="Maintainability",
        subcharacteristics=["Modularity", "Reusability", "Analysability", "Modifiability", "Testability"],
        weight=8,
        axiom_layers=["L4", "L5", "L6"]
    ),
    "Portability": ISO25010Characteristic(
        name="Portability",
        subcharacteristics=["Adaptability", "Installability", "Replaceability"],
        weight=5,
        axiom_layers=["L7", "L8"]
    )
}


@dataclass
class QualityScore:
    """Score for a quality characteristic"""
    characteristic: str
    score: int
    grade: str
    violations: List[Dict]
    subcharacteristic_scores: Dict[str, int]


@dataclass
class ISO25010Report:
    """Full ISO/IEC 25010 compliant audit report"""
    report_id: str
    file_name: str
    language: str
    timestamp: str
    overall_quality_score: int
    overall_grade: str
    quality_scores: List[QualityScore]
    recommendations: List[str]
    standards_compliance: Dict[str, bool]


class ISO25010Evaluator:
    """
    Axiom Generator with ISO/IEC 25010 compliance
    Evaluates all 8 quality characteristics
    """
    
    def __init__(self):
        self.quality_results = {}
    
    def detect_language(self, file_path: str) -> str:
        ext = Path(file_path).suffix.lower()
        lang_map = {
            '.py': 'python', '.cpp': 'cpp', '.cc': 'cpp', '.cxx': 'cpp',
            '.v': 'verilog', '.sv': 'systemverilog',
            '.js': 'javascript', '.html': 'web',
            '.bin': 'firmware', '.hex': 'firmware', '.elf': 'firmware'
        }
        return lang_map.get(ext, 'unknown')
    
    def evaluate(self, file_path: str, language: str = None) -> ISO25010Report:
        if not language:
            language = self.detect_language(file_path)
        
        print(f"\n{'='*70}")
        print(f"📋 ISO/IEC 25010 COMPLIANT EVALUATION")
        print(f"   File: {os.path.basename(file_path)}")
        print(f"   Language: {language}")
        print(f"{'='*70}\n")
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        quality_scores = []
        recommendations = []
        standards_compliance = {}
        
        # Evaluate each ISO/IEC 25010 characteristic
        for name, char in ISO_25010_MODEL.items():
            print(f"\n📊 Evaluating: {name} (Weight: {char.weight}/10)")
            
            score, violations, sub_scores = self._evaluate_characteristic(
                name, char, content, language, file_path
            )
            
            grade = self._score_to_grade(score)
            
            quality_scores.append(QualityScore(
                characteristic=name,
                score=score,
                grade=grade,
                violations=violations,
                subcharacteristic_scores=sub_scores
            ))
            
            # Generate recommendations from violations
            for v in violations:
                recommendations.append(f"[{name}] {v.get('subcharacteristic', 'General')}: {v.get('issue', '')}")
            
            # Check standards compliance
            standards_compliance[name] = score >= 70
            
            print(f"   Score: {score}/100 ({grade})")
            if violations:
                for v in violations[:2]:
                    print(f"     ⚠️ {v.get('issue', '')[:80]}")
        
        # Calculate overall quality score (weighted average)
        total_weighted = sum(qs.score * ISO_25010_MODEL[qs.characteristic].weight for qs in quality_scores)
        total_weight = sum(char.weight for char in ISO_25010_MODEL.values())
        overall_score = total_weighted // total_weight if total_weight > 0 else 0
        overall_grade = self._score_to_grade(overall_score)
        
        return ISO25010Report(
            report_id=f"ISO25010-{hash(file_path) % 10000:04d}",
            file_name=os.path.basename(file_path),
            language=language,
            timestamp=datetime.now().isoformat(),
            overall_quality_score=overall_score,
            overall_grade=overall_grade,
            quality_scores=quality_scores,
            recommendations=recommendations[:20],
            standards_compliance=standards_compliance
        )
    
    def _evaluate_characteristic(self, name: str, char: ISO25010Characteristic,
                                  content: str, language: str, file_path: str) -> tuple:
        """Evaluate a single ISO/IEC 25010 characteristic"""
        
        violations = []
        sub_scores = {}
        
        if name == "Functional Suitability":
            # L2: Logic correctness, L5: Design patterns
            score, v, subs = self._eval_functional_suitability(content, language)
            violations.extend(v)
            sub_scores.update(subs)
            
        elif name == "Performance Efficiency":
            # L4: Structure, complexity, L7: Scalability
            score, v, subs = self._eval_performance_efficiency(content, language)
            violations.extend(v)
            sub_scores.update(subs)
            
        elif name == "Compatibility":
            # L8: Firmware, environment, L1: Syntax compatibility
            score, v, subs = self._eval_compatibility(content, language, file_path)
            violations.extend(v)
            sub_scores.update(subs)
            
        elif name == "Usability":
            # L9: Common sense, error messages, L7: Serviceability
            score, v, subs = self._eval_usability(content, language)
            violations.extend(v)
            sub_scores.update(subs)
            
        elif name == "Reliability":
            # L3: Axiom (causality, determinism), L2: Logic
            score, v, subs = self._eval_reliability(content, language)
            violations.extend(v)
            sub_scores.update(subs)
            
        elif name == "Security":
            # L3: Data integrity, L9: Hardcoded secrets
            score, v, subs = self._eval_security(content, language)
            violations.extend(v)
            sub_scores.update(subs)
            
        elif name == "Maintainability":
            # L4: Structure, L5: Design, L6: Comments, magic numbers
            score, v, subs = self._eval_maintainability(content, language)
            violations.extend(v)
            sub_scores.update(subs)
            
        elif name == "Portability":
            # L7: Extendibility, L8: Firmware portability
            score, v, subs = self._eval_portability(content, language, file_path)
            violations.extend(v)
            sub_scores.update(subs)
            
        else:
            score = 50
            violations.append({"subcharacteristic": "General", "issue": f"Unknown characteristic: {name}"})
        
        return score, violations, sub_scores
    
    def _eval_functional_suitability(self, content: str, language: str) -> tuple:
        """Functional completeness, correctness, appropriateness"""
        score = 100
        violations = []
        sub_scores = {}
        
        # Functional completeness
        functions = len(re.findall(r'def\s+\w+|function\s+\w+', content))
        if functions == 0 and len(content.split('\n')) > 20:
            violations.append({
                "subcharacteristic": "Functional completeness",
                "issue": "No functions defined in file with >20 lines",
                "severity": "MEDIUM"
            })
            score -= 20
        sub_scores["Functional completeness"] = 50 if functions == 0 else 100
        
        # Functional correctness (basic checks)
        if "return" in content and "assert" not in content:
            violations.append({
                "subcharacteristic": "Functional correctness",
                "issue": "Functions return values but no assertions/validation",
                "severity": "MEDIUM"
            })
            score -= 15
        sub_scores["Functional correctness"] = 85 if "return" in content else 100
        
        # Functional appropriateness
        if "TODO" in content or "FIXME" in content:
            violations.append({
                "subcharacteristic": "Functional appropriateness",
                "issue": f"Incomplete code: {content.count('TODO')} TODO markers",
                "severity": "LOW"
            })
            score -= 5
        sub_scores["Functional appropriateness"] = 95 if "TODO" in content else 100
        
        return max(0, score), violations, sub_scores
    
    def _eval_performance_efficiency(self, content: str, language: str) -> tuple:
        """Time behaviour, resource utilization, capacity"""
        score = 100
        violations = []
        sub_scores = {}
        
        # Time behaviour - check for potential performance issues
        nested_loops = len(re.findall(r'for.*for', content))
        if nested_loops > 3:
            violations.append({
                "subcharacteristic": "Time behaviour",
                "issue": f"Deep nested loops ({nested_loops} levels) may cause O(n²) complexity",
                "severity": "HIGH"
            })
            score -= 30
        sub_scores["Time behaviour"] = max(0, 100 - nested_loops * 10)
        
        # Resource utilization
        if "while True:" in content and "sleep" not in content:
            violations.append({
                "subcharacteristic": "Resource utilization",
                "issue": "Infinite loop without sleep may consume 100% CPU",
                "severity": "HIGH"
            })
            score -= 25
        sub_scores["Resource utilization"] = 75 if "while True:" in content else 100
        
        # Capacity
        large_lists = len(re.findall(r'\[\s*\]\s*\*\s*\d+', content))
        if large_lists > 0:
            violations.append({
                "subcharacteristic": "Capacity",
                "issue": "Pre-allocating large lists may cause memory issues",
                "severity": "LOW"
            })
            score -= 5
        sub_scores["Capacity"] = 95 if large_lists == 0 else 100
        
        return max(0, score), violations, sub_scores
    
    def _eval_compatibility(self, content: str, language: str, file_path: str) -> tuple:
        """Co-existence, interoperability"""
        score = 100
        violations = []
        sub_scores = {}
        
        # Co-existence - check for version dependencies
        if "import" in content and language == "python":
            imports = re.findall(r'import\s+(\w+)', content)
            if imports:
                sub_scores["Co-existence"] = 90
            else:
                sub_scores["Co-existence"] = 100
        
        # Interoperability - check for API usage
        if "api" in content.lower() or "request" in content.lower():
            sub_scores["Interoperability"] = 85
            if "try" not in content:
                violations.append({
                    "subcharacteristic": "Interoperability",
                    "issue": "API calls without error handling",
                    "severity": "MEDIUM"
                })
                score -= 15
        else:
            sub_scores["Interoperability"] = 100
        
        # Check for toolchain availability (iverilog for Verilog)
        if language in ["verilog", "systemverilog"]:
            try:
                subprocess.run(["iverilog", "-V"], capture_output=True, timeout=5)
                sub_scores["Interoperability"] = 100
            except FileNotFoundError:
                violations.append({
                    "subcharacteristic": "Interoperability",
                    "issue": "iverilog not installed - Verilog synthesis requires this tool",
                    "severity": "HIGH",
                    "suggestion": "brew install icarus-verilog  # macOS\nsudo apt-get install iverilog  # Ubuntu"
                })
                score -= 30
                sub_scores["Interoperability"] = 0
        
        return max(0, score), violations, sub_scores
    
    def _eval_usability(self, content: str, language: str) -> tuple:
        """Learnability, operability, user error protection, aesthetics, accessibility"""
        score = 100
        violations = []
        sub_scores = {}
        
        # Operability - command line interface
        if "argparse" in content or "sys.argv" in content:
            sub_scores["Operability"] = 100
        else:
            sub_scores["Operability"] = 70
            violations.append({
                "subcharacteristic": "Operability",
                "issue": "No command-line interface detected",
                "severity": "LOW",
                "suggestion": "Add argparse for better usability"
            })
            score -= 10
        
        # User error protection
        if "try" in content and "except" in content:
            sub_scores["User error protection"] = 100
        else:
            sub_scores["User error protection"] = 50
            violations.append({
                "subcharacteristic": "User error protection",
                "issue": "Missing error handling (try/except)",
                "severity": "MEDIUM",
                "suggestion": "Add try/except blocks for user input"
            })
            score -= 20
        
        # Error message quality
        if "print" in content and "Error" in content:
            sub_scores["Error message quality"] = 90
        else:
            sub_scores["Error message quality"] = 60
        
        return max(0, score), violations, sub_scores
    
    def _eval_reliability(self, content: str, language: str) -> tuple:
        """Maturity, availability, fault tolerance, recoverability"""
        score = 100
        violations = []
        sub_scores = {}
        
        # Maturity - error handling
        exception_count = content.count("except")
        if exception_count == 0 and len(content.split('\n')) > 50:
            violations.append({
                "subcharacteristic": "Maturity",
                "issue": "No exception handling in large codebase",
                "severity": "HIGH"
            })
            score -= 25
        sub_scores["Maturity"] = 75 if exception_count == 0 else 100
        
        # Fault tolerance
        if "retry" in content.lower():
            sub_scores["Fault tolerance"] = 90
        else:
            sub_scores["Fault tolerance"] = 60
            violations.append({
                "subcharacteristic": "Fault tolerance",
                "issue": "No retry logic for transient failures",
                "severity": "LOW"
            })
            score -= 10
        
        # Recoverability
        if "backup" in content.lower() or "restore" in content.lower():
            sub_scores["Recoverability"] = 90
        else:
            sub_scores["Recoverability"] = 50
        
        # Check for causal drift (race conditions)
        if "threading" in content and "lock" not in content:
            violations.append({
                "subcharacteristic": "Maturity",
                "issue": "Threads without locks - potential race condition",
                "severity": "HIGH"
            })
            score -= 20
        
        return max(0, score), violations, sub_scores
    
    def _eval_security(self, content: str, language: str) -> tuple:
        """Confidentiality, integrity, non-repudiation, accountability, authenticity"""
        score = 100
        violations = []
        sub_scores = {}
        
        # Confidentiality - hardcoded secrets
        secrets = re.findall(r'(password|secret|key|token)\s*=\s*[\'"](\w+)[\'"]', content, re.IGNORECASE)
        if secrets:
            violations.append({
                "subcharacteristic": "Confidentiality",
                "issue": f"Hardcoded {secrets[0][0]} detected",
                "severity": "CRITICAL",
                "suggestion": "Use environment variables or secrets manager"
            })
            score -= 50
        sub_scores["Confidentiality"] = 0 if secrets else 100
        
        # Integrity - input validation
        if "input(" in content and "try" not in content:
            violations.append({
                "subcharacteristic": "Integrity",
                "issue": "User input without validation",
                "severity": "HIGH",
                "suggestion": "Validate and sanitize all user inputs"
            })
            score -= 25
        sub_scores["Integrity"] = 75 if "input(" in content else 100
        
        # Authenticity
        if "auth" in content.lower() or "login" in content.lower():
            sub_scores["Authenticity"] = 85
            if "https" not in content.lower():
                violations.append({
                    "subcharacteristic": "Authenticity",
                    "issue": "Authentication without HTTPS",
                    "severity": "HIGH"
                })
                score -= 20
        else:
            sub_scores["Authenticity"] = 100
        
        return max(0, score), violations, sub_scores
    
    def _eval_maintainability(self, content: str, language: str) -> tuple:
        """Modularity, reusability, analysability, modifiability, testability"""
        score = 100
        violations = []
        sub_scores = {}
        
        # Modularity
        functions = len(re.findall(r'def\s+\w+|function\s+\w+', content))
        lines = len(content.split('\n'))
        if functions == 0 and lines > 100:
            violations.append({
                "subcharacteristic": "Modularity",
                "issue": f"Large file ({lines} lines) with no functions",
                "severity": "MEDIUM"
            })
            score -= 20
        sub_scores["Modularity"] = min(100, functions * 10)
        
        # Analysability - comment density
        comments = len(re.findall(r'#.*$|//.*$', content, re.MULTILINE))
        comment_density = (comments / max(lines, 1)) * 100
        if comment_density < 10:
            violations.append({
                "subcharacteristic": "Analysability",
                "issue": f"Low comment density ({comment_density:.1f}%)",
                "severity": "MEDIUM",
                "suggestion": "Add documentation comments"
            })
            score -= 15
        sub_scores["Analysability"] = int(min(100, comment_density * 5))
        
        # Testability
        if "test" in content.lower():
            sub_scores["Testability"] = 90
        else:
            sub_scores["Testability"] = 50
            violations.append({
                "subcharacteristic": "Testability",
                "issue": "No test code detected",
                "severity": "LOW"
            })
            score -= 10
        
        # Modifiability - magic numbers
        magic_numbers = len(re.findall(r'\b\d{2,}\b', content))
        if magic_numbers > 10:
            violations.append({
                "subcharacteristic": "Modifiability",
                "issue": f"{magic_numbers} magic numbers - use named constants",
                "severity": "LOW"
            })
            score -= 5
        sub_scores["Modifiability"] = max(0, 100 - magic_numbers)
        
        return max(0, score), violations, sub_scores
    
    def _eval_portability(self, content: str, language: str, file_path: str) -> tuple:
        """Adaptability, installability, replaceability"""
        score = 100
        violations = []
        sub_scores = {}
        
        # Adaptability
        if "os." in content or "platform" in content:
            sub_scores["Adaptability"] = 90
        else:
            sub_scores["Adaptability"] = 70
        
        # Installability - dependencies
        if "requirements.txt" in str(file_path) or "package.json" in str(file_path):
            sub_scores["Installability"] = 100
        else:
            sub_scores["Installability"] = 60
            violations.append({
                "subcharacteristic": "Installability",
                "issue": "No dependency manifest found",
                "severity": "LOW"
            })
            score -= 5
        
        # Replaceability
        if "interface" in content.lower() or "abstract" in content.lower():
            sub_scores["Replaceability"] = 85
        else:
            sub_scores["Replaceability"] = 60
        
        return max(0, score), violations, sub_scores
    
    def _score_to_grade(self, score: int) -> str:
        if score >= 95: return "A+"
        if score >= 90: return "A"
        if score >= 85: return "A-"
        if score >= 80: return "B+"
        if score >= 75: return "B"
        if score >= 70: return "B-"
        if score >= 65: return "C+"
        if score >= 60: return "C"
        if score >= 55: return "C-"
        if score >= 50: return "D+"
        if score >= 40: return "D"
        return "F"
    
    def print_report(self, report: ISO25010Report):
        """Print ISO/IEC 25010 compliant report"""
        print("\n" + "█"*70)
        print("█  ISO/IEC 25010 COMPLIANT AUDIT REPORT")
        print("█  Systems and Software Quality Requirements and Evaluation")
        print("█"*70)
        print(f"\n   Report ID: {report.report_id}")
        print(f"   File: {report.file_name}")
        print(f"   Language: {report.language}")
        print(f"   Timestamp: {report.timestamp}")
        print(f"\n   📊 OVERALL QUALITY SCORE: {report.overall_quality_score}/100")
        print(f"   📈 GRADE: {report.overall_grade}")
        print(f"   ✅ Standards Compliance: {sum(report.standards_compliance.values())}/8 characteristics")
        
        print("\n" + "-"*70)
        print("📋 QUALITY CHARACTERISTICS (ISO/IEC 25010)")
        print("-"*70)
        
        for qs in report.quality_scores:
            icon = "✅" if qs.score >= 70 else "⚠️" if qs.score >= 50 else "❌"
            print(f"\n   {icon} {qs.characteristic}: {qs.score}/100 ({qs.grade})")
            print(f"      Sub-characteristics:")
            for sub, sub_score in qs.subcharacteristic_scores.items():
                print(f"        - {sub}: {sub_score}/100")
            if qs.violations:
                for v in qs.violations[:2]:
                    print(f"        ⚠️ {v.get('issue', '')[:70]}")
        
        print("\n" + "-"*70)
        print("🔧 RECOMMENDATIONS")
        print("-"*70)
        for i, rec in enumerate(report.recommendations[:10], 1):
            print(f"   {i}. {rec}")
        
        print("\n" + "-"*70)
        print("📜 STANDARDS COMPLIANCE")
        print("-"*70)
        for std, compliant in report.standards_compliance.items():
            status = "✅ COMPLIANT" if compliant else "⚠️ NON-COMPLIANT"
            print(f"   {std}: {status}")
        
        print("\n" + "█"*70)
        print("█  END OF ISO/IEC 25010 REPORT")
        print("█"*70)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python iso25010_evaluator.py <file_path> [language]")
        sys.exit(1)
    
    file_path = sys.argv[1]
    language = sys.argv[2] if len(sys.argv) > 2 else None
    
    evaluator = ISO25010Evaluator()
    report = evaluator.evaluate(file_path, language)
    evaluator.print_report(report)
