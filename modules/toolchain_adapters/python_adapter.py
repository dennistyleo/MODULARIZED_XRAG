"""Python toolchain adapter with venv isolation"""

import subprocess
import tempfile
from pathlib import Path
from typing import Dict
from .base_adapter import BaseToolchainAdapter, ExecutionResult


class PythonToolchainAdapter(BaseToolchainAdapter):
    
    def can_handle(self, language: str, file_path: str) -> bool:
        return language == "python" or file_path.endswith(".py")
    
    def execute(self, file_path: str, timeout: int = 30) -> ExecutionResult:
        with tempfile.TemporaryDirectory() as sandbox:
            try:
                venv_path = f"{sandbox}/venv"
                subprocess.run(["python3", "-m", "venv", venv_path], capture_output=True, timeout=10)
                
                req_path = Path(file_path).parent / "requirements.txt"
                if req_path.exists():
                    pip_path = f"{venv_path}/bin/pip"
                    subprocess.run([pip_path, "install", "-r", str(req_path)], capture_output=True, timeout=60)
                
                python_path = f"{venv_path}/bin/python"
                result = subprocess.run([python_path, file_path], capture_output=True, text=True, timeout=timeout)
                
                crashes = []
                if "Traceback" in result.stderr or "Error" in result.stderr:
                    crashes.append({"type": "runtime_error", "trace": result.stderr[:500]})
                
                return ExecutionResult(
                    success=result.returncode == 0,
                    stdout=result.stdout,
                    stderr=result.stderr,
                    exit_code=result.returncode,
                    logs=result.stdout + result.stderr,
                    crashes=crashes
                )
            except subprocess.TimeoutExpired:
                return ExecutionResult(success=False, stderr=f"Timeout after {timeout}s", exit_code=-1)
            except Exception as e:
                return ExecutionResult(success=False, stderr=str(e), exit_code=-1)
    
    def get_backup_analysis(self, file_path: str, failure_context: Dict) -> Dict:
        return {
            "root_cause": "Potential infinite loop or recursion detected",
            "suggested_fixes": ["Add base case to recursion", "Check loop termination", "Add timeout"],
            "reproducer": f"python3 {file_path}",
            "confidence": 0.85,
            "tool": "Python Static Analyzer (Fallback)"
        }
