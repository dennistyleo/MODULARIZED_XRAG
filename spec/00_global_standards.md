# Global Standards

Version: 1.0.0

## Naming Conventions
- Modules:              snake_case.py          (rag_module, gnn_module)
- Classes:              PascalCase             (RAGModule, GNNAgent)
- Functions/Methods:    snake_case() [Python]  (extract_structured_data)
                        camelCase() [JS]       (extractData, detectDrift)
- Constants:            UPPER_SNAKE_CASE       (GEMINI_3_FLASH_PREVIEW)
- Environment vars:     SOVEREIGN_*            (SOVEREIGN_GEMINI_API_KEY)
- API endpoints:        lowercase_with_underscores (/api/agent/seal/characterize)
- JSON field names:     snake_case             (contract_id, confidence_score)
- Test IDs:             MODULE_NUMBER_DESCRIPTION (RAG_001_pdf_extraction)
- Error codes:          E-series or T-series   (E001, T001)
- Trace IDs:            {timestamp}_{random_8} (20260410_083000_a3f2)
- Session IDs:          SESSION_{timestamp}_{user} (SESSION_20260410_083000_leo)

## Ports
- Flask:   8080
- SocketIO: 8080

## Error Codes
### Execution Errors (E-series)
- E001: FILE_NOT_FOUND          (no retry)
- E002: GEMINI_API_TIMEOUT      (retry 3 times)
- E003: INVALID_JSON_RESPONSE   (retry 2 times)
- E004: SCHEMA_VALIDATION_FAILED (no retry)
- E005: MODULE_TIMEOUT          (retry 3 times)
- E006: DRIFT_DETECTION_FAILED  (log warning, use fallback)
- E007: CAUSAL_CHAIN_BROKEN     (no retry)
- E008: DATABASE_CONNECTION_FAILED (retry 3 times)
- E009: BUS_ROUTING_FAILED      (retry 3 times)
- E010: HITL_TIMEOUT            (log warning, use original data)

### Test Errors (T-series)
- T001: TEST_ASSERTION_FAILED

## Trace / Timestamp Formats
Trace ID Format: {timestamp}_{random_8}
Example:         20260410_083000_a3f2
Timestamp Format: YYYYMMDD_HHMMSS

## Confidence Thresholds (HITL Gates)
- Overall RAG extraction confidence < 0.85 → HITL required (auto-pass at >= 0.85)
- Individual node confidence < 0.60       → HITL required
- Assessment tier == 3 (REFUSE)           → HITL required
- composite_score >= 0.70                 → HITL required (risk escalation)

## RAG Command Levels
Commands tell RAG exactly what to do — no guessing allowed.

| Level             | Purpose                                    | Example                                           |
|-------------------|--------------------------------------------|---------------------------------------------------|
| Domain Command    | Tells RAG what kind of analysis to perform | "Analyze this as a financial contract"            |
| Extraction Command| Specifies what data fields to extract      | "Extract: party names, effective date, payment terms" |
| Evaluation Command| Specifies what rules/axioms to apply       | "Apply L2: IFRS 15 revenue recognition rules"    |
| Output Command    | Specifies format/level of detail to return | "Return JSON with confidence scores per field"   |

Strict mode: if confidence_threshold is set and any field is below it, reject the file.

## Tier Classification
| Value | Label  | composite_score | Action              |
|-------|--------|-----------------|---------------------|
| 1     | TIER_1 | < 0.40          | ACCEPT (auto)       |
| 2     | TIER_2 | 0.40 – 0.69     | REVIEW              |
| 3     | TIER_3 | >= 0.70         | REFUSE + HITL modal |

## Enum Values

### Domain
CONTRACT | FINANCIAL | TECHNICAL | AEROSPACE | GENERAL

### Tier
TIER_1 | TIER_2 | TIER_3  (or integer 1 | 2 | 3)

### Direction (GNN time rotation)
FORWARD | BACKWARD | NONE

### Status
PENDING | IN_PROGRESS | COMPLETED | FAILED

### Confidence Label
HIGH (>= 0.85) | MEDIUM (>= 0.60) | LOW (< 0.60)

### HITL Action
CONFIRMED | CANCELLED | TIMEOUT

## Deterministic Action Names
| Action              | Python Function                        | Description                      |
|---------------------|----------------------------------------|----------------------------------|
| Extract data        | extract_structured_data()              | Returns JSON schema              |
| Fingerprint data    | generate_data_fingerprint()            | Returns stationarity/SNR/domain  |
| Detect drift        | detect_3d_shape_drift()                | Returns drift location           |
| Rotate time         | rotate_time_dimension(direction)       | direction: FORWARD or BACKWARD   |
| Find root cause     | trace_root_cause(start_node)           | Returns node chain               |
| Predict failure     | predict_failure_timeline()             | Returns cycles to failure        |
| Confirm HITL        | confirm_human_in_loop(decision)        | decision: CONFIRMED|CANCELLED    |
| Register axiom      | register_axiom(axiom_record)           | Hot registers into axiom registry|
| Rank scouts         | rank_scout_evaluations(evaluations)    | Returns sorted scout report cards|

## Axiom Democracy Scoring Formula
Used to rank competing axioms and scout agents across all pipeline stages.

### Per-Axiom Scoring (L2 — HYPOTHESIS_CAMPAIGN)
Each axiom that campaigns is scored with the following metrics:

| Metric | Formula | Weight | Source |
|--------|---------|--------|--------|
| Relevance Score | cosine_similarity(fingerprint.domain_hints, axiom.domains) | 0.40 | L2 |
| Confidence Score | axiom.confidence_score (from self-evaluation) | 0.30 | L2 |
| Historical Success | axiom.past_record[domain].success_rate | 0.20 | Axiom Registry |
| Computational Cost | 1 - (axiom.cost / max_cost) | 0.10 | Axiom Registry |

**Winning_Score** = (Relevance × 0.40) + (Confidence × 0.30) + (Historical_Success × 0.20) + (Cost_Adjusted × 0.10)

Where:
- Relevance:          cosine_similarity(fingerprint.domain_hints, axiom.domains) — (0–1)
- Confidence:         axiom.confidence_score from self-evaluation — (0–1)
- Historical_Success: axiom.past_record[domain].success_rate — (0–1)
- Cost_Adjusted:      1 - (axiom.cost / max_cost) — lower cost = higher score (0–1)

### Constraint Satisfaction (L3 — CONSTRAINT_ELECTION)
Each axiom must satisfy all of the following to remain admissible:

| Constraint | Rule |
|------------|------|
| Pattern Match | axiom.pattern ⊆ ontology_path |
| Confidence Floor | axiom.confidence_floor ≤ assessment.conf |
| Severity Threshold | axiom.severity ∈ [LOW, MEDIUM, HIGH, CRITICAL] |

### Coalition Consensus (L3)
coalition_consensus = Σ(member.winning_score × member.weight) / Σ(weights)

### Per-Pathway Risk (L4 — BAYESIAN_RISK)
pathway_risk = (final_risk_score × 0.6) + (probability_of_failure × 0.4)

### Composite Score (L4)
composite_score = (0.40 × max_pathway_risk) +
                  (0.30 × probability_of_failure) +
                  (0.20 × deviation_score × is_real_anomaly) +
                  (0.10 × drift_magnitude × drift_detected)

Where:
- A = max_pathway_risk         (from surviving pathways)
- B = probability_of_failure   (from causal matrix)
- C = deviation_score × is_real_anomaly  (0 if not a real anomaly)
- D = drift_magnitude × drift_detected   (0 if no drift detected)

### Audit Trail Requirements
For every decision point, the audit trail MUST record:
- Input values used in each calculation
- Intermediate products: (Relevance×0.40), (Confidence×0.30), (Historical×0.20), (Cost_Adj×0.10)
- Final Winning_Score per axiom
- Tie-breaking method (if scores are equal)
- User override (if HITL intervened)

## ID Naming Patterns
| ID Type       | Pattern                          | Example                     |
|---------------|----------------------------------|-----------------------------|
| Node ID       | N{number}                        | N1, N2, N7                  |
| Edge ID       | E{number}                        | E1, E2                      |
| Axiom ID      | {DOMAIN}_{TYPE}_{NUMBER}         | CONTRACT_D_001, THERMAL_B_002 |
| Test Point ID | {MODULE}_{NUMBER}_{description}  | RAG_001_pdf_extraction      |
| Trace ID      | {timestamp}_{random_8}           | 20260410_083000_a3f2        |
| Session ID    | SESSION_{timestamp}_{user}       | SESSION_20260410_083000_leo |
| HITL Req ID   | HITL_{random_4}                  | HITL_A3F2                   |
| Scout ID      | {module}_scout_v{N}              | gnn_scout_v1, l4_scout_v1   |
| Election ID   | {date}_{sequence}                | 2026-04-10-001              |

## Dataset Naming
| Type             | Pattern                                | Example                   |
|------------------|----------------------------------------|---------------------------|
| Fixture file     | {domain}_{type}_{number}.{ext}         | contract_pdf_001.pdf      |
| Test input       | input_{module}_{test_id}.json          | input_rag_001.json        |
| Expected output  | expected_{module}_{test_id}.json       | expected_rag_001.json     |
| Log file         | log_{module}_{date}.log                | log_rag_20260410.log      |

## Gray Area Elimination Checklist
Before writing any spec, verify all 10 checks pass:

1. Every model name is exact (from official docs)         ✅/⬜
2. Every naming convention is defined                     ✅/⬜
3. No abbreviations allowed                               ✅/⬜
4. Every enum has defined values                          ✅/⬜
5. Every action has a deterministic name                  ✅/⬜
6. Every error has a code                                 ✅/⬜
7. Every ID follows a pattern                             ✅/⬜
8. No "etc.", "and so on", "similar to"                  ✅/⬜
9. No "approximately", "around", "about"                 ✅/⬜
10. No "may", "might", "could", "should"                 ✅/⬜


