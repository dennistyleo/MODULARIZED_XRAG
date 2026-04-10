#!/bin/bash

# Rule 1
cat > .agents/rules/00_global_design_rules.md << 'EOF'
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
EOF

# Rule 2
cat > .agents/rules/01_naming_conventions.md << 'EOF'
# Naming Conventions

## Files
- Python modules: snake_case.py
- JavaScript modules: PascalCase.js
- Test files: test_snake_case.py

## Error Codes
- E001: FILE_NOT_FOUND
- E002: GEMINI_API_TIMEOUT
- E003: INVALID_JSON_RESPONSE
- E004: SCHEMA_VALIDATION_FAILED
- E005: MODULE_TIMEOUT
- E006: DRIFT_DETECTION_FAILED
- E007: CAUSAL_CHAIN_BROKEN
- E008: DATABASE_CONNECTION_FAILED
- E009: BUS_ROUTING_FAILED
- E010: HITL_TIMEOUT

## Environment Variables
- SOVEREIGN_GEMINI_API_KEY
- SOVEREIGN_DB_HOST
- SOVEREIGN_DB_USER
- SOVEREIGN_DB_PASSWORD
- SOVEREIGN_LOG_LEVEL
- SOVEREIGN_PORT
EOF

# Rule 3
cat > .agents/rules/02_code_structure.md << 'EOF'
# Code Structure Requirements

## Python Module Template
- File: modules/{name}.py
- Max lines: 500
- Must include: imports, logger, class, bus handlers

## JavaScript Module Template
- File: static/js/{name}.js
- Max lines: 400
- Must include: self-registration pattern

## Test File Template
- File: tests/test_{name}.py
- Max lines: 300
EOF

# Rule 4
cat > .agents/rules/03_module_communication.md << 'EOF'
# Module Communication Rules

## Sovereign BUS Only
- NO direct function calls
- ALL communication via SovereignBUS

## Required Events
- DATA_EXTRACTED
- ONTOLOGY_CLASSIFIED
- HYPOTHESIS_GENERATED
- PATHWAY_FILTERED
- RISK_ASSESSED
- REPORT_READY
- DRIFT_DETECTED
- SHAPE_COMPARED
- CAUSAL_MATRIX_READY
- HITL_REQUEST
- HITL_RESPONSE
- ERROR
EOF

# Rule 5
cat > .agents/rules/04_error_handling.md << 'EOF'
# Error Handling Rules

## Retry Rules
- E001: NO retry
- E002: Retry 3 times
- E003: Retry 2 times
- E005: Retry 3 times
- E008: Retry 3 times

## Logging Requirements
- Every error must be logged
- Log must include error_code, trace_id, timestamp
EOF

# Rule 6
cat > .agents/rules/05_testing_standards.md << 'EOF'
# Testing Standards

## Coverage Requirements
- Line coverage: >= 90%
- Branch coverage: >= 85%
- Function coverage: 100%

## Required Tests per Module
- test_valid_input
- test_invalid_input
- test_error_handling
- test_timeout
- test_schema_validation
EOF

# Rule 7
cat > .agents/rules/06_frontend_components.md << 'EOF'
# Frontend Component Rules

## No Hardcoded IDs
- Components must self-register

## Self-Registration Pattern
- registry.registerTab({id, label, order, component})

## Tab Lifecycle
- bind(element)
- onActivate()
- onDeactivate()
- onData(data)
EOF

# Rule 8
cat > .agents/rules/07_hitl_modal_rules.md << 'EOF'
# HITL Modal Rules

## Trigger Conditions
- assessment.tier == 3
- drift_detected == true
- confidence < 0.60
- user_request == true

## Modal Content
- File summary
- Data table with editable fields
- Edit panel
- Confirm/Cancel buttons
EOF

echo "All rules created successfully"
