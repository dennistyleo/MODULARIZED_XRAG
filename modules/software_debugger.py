#!/usr/bin/env python3
"""
Software Debugger Module for Axiom Generator - Fixed Version
"""

import ast
import re
import json
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

class SoftwareDebugger:
    def __init__(self):
        self.bug_patterns = self._load_bug_patterns()
    
    def _load_bug_patterns(self) -> Dict:
        return {
            "python": {
                "L3_RULE": {
                    "patterns": [
                        {"name": "bare_except", "pattern": r"except\s*:", 
                         "fix": "except Exception as e:", "severity": "HIGH"},
                        {"name": "multiple_assignments", "pattern": r"(\w+)\s*=\s*(\w+)\s*=\s*(\w+)",
                         "fix": "Split into separate statements", "severity": "MEDIUM"},
                        {"name": "print_statement", "pattern": r"print\(",
                         "fix": "Use logging instead", "severity": "LOW"},
                    ]
                }
            },
            "javascript": {
                "L3_RULE": {
                    "patterns": [
                        {"name": "loose_equality", "pattern": r"==",
                         "fix": "===", "severity": "MEDIUM"},
                        {"name": "var_declaration", "pattern": r"\bvar\s+",
                         "fix": "Use let or const", "severity": "LOW"},
                    ]
                }
            },
            "verilog": {
                "L3_RULE": {
                    "patterns": [
                        {"name": "blocking_in_generate", "pattern": r"generate.*?assign.*?<=",
                         "fix": "Use = instead of <=", "severity": "CRITICAL"},
                        {"name": "genvar_conflict", "pattern": r"genvar\s+g;.*?integer\s+g;",
                         "fix": "Use different names", "severity": "HIGH"},
                    ]
                }
            }
        }
    
    def debug_file(self, filepath: str, language: str = None) -> Dict:
        if not language:
            ext = Path(filepath).suffix
            lang_map = {'.py': 'python', '.js': 'javascript', '.v': 'verilog', '.sv': 'verilog'}
            language = lang_map.get(ext, 'unknown')
        
        if language == 'unknown':
            return {"error": f"Cannot detect language for {filepath}"}
        
        with open(filepath, 'r') as f:
            content = f.read()
        
        results = {
            "file": filepath,
            "language": language,
            "timestamp": datetime.now().isoformat(),
            "bugs": [],
            "fixes": [],
            "score": 100,
            "status": "CLEAN"
        }
        
        # L1: Syntax validation
        syntax_bugs = self._check_syntax(content, language, filepath)
        results["bugs"].extend(syntax_bugs)
        
        # L3: Pattern matching (skip L2 for now - too many false positives)
        pattern_bugs = self._match_patterns(content, language)
        results["bugs"].extend(pattern_bugs)
        
        # L4: Risk quantification
        results["score"], results["status"] = self._calculate_risk(results["bugs"])
        
        # L5: Generate fixes
        results["fixes"] = self._generate_fixes(results["bugs"])
        
        return results
    
    def _check_syntax(self, content: str, language: str, filepath: str) -> List[Dict]:
        bugs = []
        
        if language == 'python':
            try:
                ast.parse(content, filename=filepath)
            except SyntaxError as e:
                bugs.append({
                    "layer": "L1",
                    "type": "SYNTAX_ERROR",
                    "message": str(e),
                    "line": e.lineno,
                    "severity": "CRITICAL"
                })
            except IndentationError as e:
                bugs.append({
                    "layer": "L1",
                    "type": "INDENTATION_ERROR",
                    "message": str(e),
                    "line": e.lineno,
                    "severity": "CRITICAL"
                })
        elif language == 'verilog':
            try:
                result = subprocess.run(
                    ["iverilog", "-o", "/dev/null", filepath],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode != 0:
                    for line in result.stderr.split('\n'):
                        if 'error' in line.lower():
                            bugs.append({
                                "layer": "L1",
                                "type": "SYNTAX_ERROR",
                                "message": line.strip(),
                                "severity": "CRITICAL"
                            })
            except FileNotFoundError:
                bugs.append({
                    "layer": "L1",
                    "type": "TOOL_MISSING",
                    "message": "iverilog not installed",
                    "severity": "LOW"
                })
        return bugs
    
    def _match_patterns(self, content: str, language: str) -> List[Dict]:
        bugs = []
        patterns = self.bug_patterns.get(language, {}).get("L3_RULE", {}).get("patterns", [])
        
        for pattern in patterns:
            if "pattern" in pattern:
                matches = re.findall(pattern["pattern"], content, re.DOTALL)
                if matches:
                    bugs.append({
                        "layer": "L3",
                        "type": pattern["name"].upper(),
                        "message": f"Found: {pattern['name']}",
                        "suggestion": pattern.get("fix", "Review and fix"),
                        "severity": pattern["severity"]
                    })
        return bugs
    
    def _calculate_risk(self, bugs: List[Dict]) -> tuple:
        severity_weights = {"CRITICAL": 50, "HIGH": 20, "MEDIUM": 10, "LOW": 2}
        total_deduction = sum(severity_weights.get(b.get("severity", "LOW"), 0) for b in bugs)
        score = max(0, 100 - total_deduction)
        
        if score >= 90:
            status = "CLEAN"
        elif score >= 70:
            status = "GOOD"
        elif score >= 50:
            status = "NEEDS_IMPROVEMENT"
        elif score >= 25:
            status = "POOR"
        else:
            status = "CRITICAL"
        return score, status
    
    def _generate_fixes(self, bugs: List[Dict]) -> List[Dict]:
        fixes = []
        for bug in bugs:
            if "suggestion" in bug:
                fixes.append({
                    "for_bug": bug["type"],
                    "suggestion": bug["suggestion"],
                    "confidence": 0.85
                })
        return fixes
    
    def print_report(self, results: Dict):
        print("\n" + "=" * 60)
        print(f"🔍 AXIOM GENERATOR DEBUG REPORT")
        print("=" * 60)
        print(f"File: {results['file']}")
        print(f"Language: {results['language']}")
        print(f"Score: {results['score']}/100")
        print(f"Status: {results['status']}")
        print(f"Bugs Found: {len(results['bugs'])}")
        print("-" * 60)
        
        for bug in results['bugs']:
            print(f"\n[{bug['severity']}] {bug['type']}")
            print(f"  {bug['message']}")
            if bug.get('line'):
                print(f"  Line: {bug['line']}")
        
        if results['fixes']:
            print("\n" + "-" * 60)
            print("🔧 SUGGESTED FIXES:")
            for fix in results['fixes']:
                print(f"  • {fix['suggestion']}")
        print("\n" + "=" * 60)


if __name__ == "__main__":
    import sys
    debugger = SoftwareDebugger()
    
    if len(sys.argv) < 2:
        print("Usage: python software_debugger_fixed.py <filepath> [language]")
        sys.exit(1)
    
    filepath = sys.argv[1]
    language = sys.argv[2] if len(sys.argv) > 2 else None
    
    results = debugger.debug_file(filepath, language)
    
    if "error" in results:
        print(f"❌ Error: {results['error']}")
    else:
        debugger.print_report(results)
        
        report_path = Path(filepath).stem + "_debug_report.json"
        with open(report_path, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n📄 Detailed report saved to: {report_path}")
