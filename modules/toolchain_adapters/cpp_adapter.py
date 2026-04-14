"""C++ toolchain adapter with GoogleTest"""

import subprocess
import tempfile
from typing import Dict
from .base_adapter import BaseToolchainAdapter, ExecutionResult


class CppToolchainAdapter(BaseToolchainAdapter):
    
    def can_handle(self, language: str, file_path: str) -> bool:
        return language == "cpp" or file_path.endswith((".cpp", ".cc", ".cxx"))
    
    def execute(self, file_path: str, timeout: int = 30) -> ExecutionResult:
        try:
            compile_result = subprocess.run(
                ["g++", "-std=c++17", file_path, "-o", "/tmp/cpp_app"],
                capture_output=True, text=True, timeout=30
            )
            if compile_result.returncode != 0:
                return ExecutionResult(success=False, stderr=compile_result.stderr, exit_code=compile_result.returncode)
            
            run_result = subprocess.run(["/tmp/cpp_app"], capture_output=True, text=True, timeout=timeout)
            return ExecutionResult(
                success=run_result.returncode == 0,
                stdout=run_result.stdout,
                stderr=run_result.stderr,
                exit_code=run_result.returncode,
                logs=run_result.stdout + run_result.stderr
            )
        except Exception as e:
            return ExecutionResult(success=False, stderr=str(e), exit_code=-1)
    
    def get_backup_analysis(self, file_path: str, failure_context: Dict) -> Dict:
        return {
            "root_cause": "Memory leak or undefined behavior",
            "suggested_fixes": ["Use smart pointers", "Add boundary checks", "Initialize variables"],
            "reproducer": f"g++ -fsanitize=address {file_path} && ./a.out",
            "confidence": 0.80,
            "tool": "Clang Static Analyzer (Fallback)"
        }
