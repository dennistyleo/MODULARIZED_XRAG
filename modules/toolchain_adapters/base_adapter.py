"""Base adapter for all toolchain integrations"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import json

@dataclass
class ExecutionResult:
    success: bool
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    logs: str = ""
    crashes: List[Dict] = None
    coverage: Dict = None
    tests: List[Dict] = None
    error: Optional[str] = None
    
    def __post_init__(self):
        if self.crashes is None:
            self.crashes = []
        if self.coverage is None:
            self.coverage = {}
        if self.tests is None:
            self.tests = []
    
    def to_dict(self) -> Dict:
        return asdict(self)


class BaseToolchainAdapter(ABC):
    @abstractmethod
    def execute(self, file_path: str, timeout: int = 30) -> ExecutionResult:
        pass
    
    @abstractmethod
    def get_backup_analysis(self, file_path: str, failure_context: Dict) -> Dict:
        pass
    
    @abstractmethod
    def can_handle(self, language: str, file_path: str) -> bool:
        pass
