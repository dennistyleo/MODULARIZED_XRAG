# Global Design Rules for Modularized XRAG

## Core Principles
1. Deterministic First
2. No Hardcoded IDs
3. Event-Driven Communication
4. Graceful Degradation
5. Testability

## Prohibited Practices
- Hardcoded port numbers
- Direct function calls between modules
- Global variables
- except: pass
- Print statements

## Required Practices
- Type hints for all functions
- Docstrings for public functions
- Error codes (E001-E999)
- Trace IDs for all operations
- Timeouts for external calls
