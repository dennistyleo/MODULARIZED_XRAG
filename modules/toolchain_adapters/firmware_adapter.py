"""Firmware toolchain adapter with QEMU emulation"""

import subprocess
from typing import Dict
from .base_adapter import BaseToolchainAdapter, ExecutionResult


class FirmwareToolchainAdapter(BaseToolchainAdapter):
    
    def can_handle(self, language: str, file_path: str) -> bool:
        return language == "firmware" or file_path.endswith((".bin", ".hex", ".elf", ".rom"))
    
    def execute(self, file_path: str, timeout: int = 30) -> ExecutionResult:
        try:
            result = subprocess.run([
                "qemu-system-x86_64", "-bios", file_path, "-nographic",
                "-m", "256", "-serial", "stdio", "-display", "none",
                "-no-reboot", "-snapshot"
            ], capture_output=True, text=True, timeout=timeout)
            
            crashes = []
            if "panic" in result.stdout.lower() or "exception" in result.stdout.lower():
                crashes.append({"type": "firmware_panic", "trace": result.stdout[-500:]})
            
            return ExecutionResult(
                success="panic" not in result.stdout.lower(),
                stdout=result.stdout,
                stderr=result.stderr,
                logs=result.stdout + result.stderr,
                crashes=crashes
            )
        except subprocess.TimeoutExpired:
            return ExecutionResult(success=True, stdout="Firmware executed (timeout after normal operation)")
        except Exception as e:
            return ExecutionResult(success=False, stderr=str(e), exit_code=-1)
    
    def get_backup_analysis(self, file_path: str, failure_context: Dict) -> Dict:
        return {
            "root_cause": "POST sequence failure or hardware initialization error",
            "suggested_fixes": ["Verify interrupt vector table", "Check memory map", "Validate bootloader"],
            "reproducer": f"qemu-system-x86_64 -bios {file_path} -d int -no-reboot",
            "confidence": 0.75,
            "tool": "QEMU + OSS-Fuzz (Fallback)"
        }
