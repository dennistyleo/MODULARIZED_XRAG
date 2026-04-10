# HITL Modal Specification

Version: 1.0.0
BUS Event In:  HITL_REQUEST
BUS Event Out: HITL_RESPONSE

## Purpose
Present a non-blocking review modal to the human operator whenever the pipeline
cannot make a deterministic decision or detects high-risk conditions.
The operator reviews extracted data, edits suspicious fields, and confirms or cancels.
Every HITL interaction is logged as part of the audit trail.

## Value of HITL (Beyond Error Correction)
Even without mistakes, HITL provides:
- Trust:         Users see what data was extracted and can verify
- Education:     Users learn how the ontology applies to their data
- Traceability:  User corrections become part of the audit trail
- Transparency:  The system is not a black box — the ontology is confirmed, not assumed

## Stage-Specific HITL Trigger Conditions
HITL can appear at any stage where the system cannot make a deterministic decision:

| Stage  | Trigger Condition                                        | reason Code             |
|--------|----------------------------------------------------------|-------------------------|
| UPLOAD | RAG overall confidence < 0.85                           | LOW_CONFIDENCE          |
| L1     | Multiple domain classifications possible                 | DOMAIN_AMBIGUITY        |
| L1     | assessment.tier == 3                                     | TIER_3                  |
| L1     | Any node.confidence < 0.60                              | NODE_LOW_CONFIDENCE     |
| L2     | Multiple pathways have equal Winning_Score               | PATHWAY_TIE             |
| L3     | Multiple valid pathways survive (score diff < 0.05)      | MULTI_PATHWAY_CHOICE    |
| L3     | No pathway passes constraints                            | NO_ADMISSIBLE_PATHWAY   |
| L4     | composite_score >= 0.70 (escalation from lower tier)    | SCORE_ESCALATION        |
| L4     | Confidence intervals of top pathways overlap             | CI_OVERLAP              |
| L5     | User wants to customize report format                    | REPORT_CUSTOMIZATION    |
| ANY    | GNN drift_detected == true                              | DRIFT_DETECTED          |
| ANY    | User manually requests review                            | MANUAL                  |

## HITL_REQUEST Payload
{
  "request_id":        "HITL_A3F2",
  "trace_id":          "string",
  "stage":             "UPLOAD | L1 | L2 | L3 | L4 | L5",
  "reason":            "(reason code from table above)",
  "domain":            "string",
  "file_name":         "string",
  "nodes":             [...],
  "assessment":        {...},
  "suspicious_node_ids": ["N3", "N7"]
}

## Modal Layout and Content

### Section 1: File Analysis Summary
- File name, type, domain, upload timestamp
- Overall confidence badge (color: HIGH=green, MEDIUM=yellow, LOW=red)
- Reason banner: explains which trigger fired and from which stage

### Section 2: Extracted Data Table (Editable)
Columns: Field | Extracted Value | Confidence | Status
- Rows: one per node
- Confidence indicator: bar colored by threshold (>= 0.85 green, >= 0.60 yellow, < 0.60 red)
- Suspicious nodes (confidence < 0.60) highlighted in red

### Section 3: Edit Panel (active on row click)
- Field:     selected node name
- Current:   current extracted value
- Suggested: alternative value (from source section reference, if available)
- Why low confidence?: explanation string from RAG
- Buttons:   [✓ Accept Suggestion]  [✏ Edit Manually]  [ℹ View Source]

### Section 4: Impact Preview (real-time)
Shows how current edits would affect each pipeline stage score:
- L1: Classification  → "Will use [domain] ontology"
- L2: Hypothesis      → "Will apply: [pathway names]"
- L3: Constraints     → "Will check: [axiom names]"
- L4: Risk            → "Will calculate confidence intervals"
- L5: Report          → "Will include your corrections in audit trail"

### Section 5: Multi-Pathway Choice (L3 only, reason=MULTI_PATHWAY_CHOICE)
"Multiple evaluation pathways detected. Choose one or more:"
  ☐ [Pathway 1 name]  — [description]
  ☐ [Pathway 2 name]  — [description]
  [Generate All]  [Generate Selected]  [Cancel]

### Section 6: Action Buttons
- [Cancel]             → dismiss modal, pipeline continues without correction
- [✓ Confirm & Continue] → save edits, re-trigger L1→L5 pipeline with corrected nodes

## Timeout
- HITL modal auto-submits using original (uncorrected) data after 300 seconds
- Error code E010 is logged on auto-submit
- BUS event emitted: HITL_RESPONSE with action=TIMEOUT

## HITL_RESPONSE Payload
{
  "request_id":       "HITL_A3F2",
  "trace_id":         "string",
  "stage":            "UPLOAD | L1 | L2 | L3 | L4 | L5",
  "reason":           "string",
  "action":           "CONFIRMED | CANCELLED | TIMEOUT",
  "corrected_nodes":  [...],
  "selected_pathways": ["axiom_id_1", "axiom_id_2"],
  "operator_id":      "string or null",
  "timestamp":        "ISO8601"
}

## Accessibility Requirements
- Modal element:       role="dialog", aria-modal="true", aria-label="Human Review"
- Focus trapped within modal while open
- Keyboard:            Tab navigates fields, Enter confirms, Esc cancels
- All interactive elements have unique IDs:
  - hitl-modal
  - hitl-confirm-btn
  - hitl-cancel-btn
  - hitl-reason-banner
  - hitl-data-table
  - hitl-edit-panel
  - hitl-impact-preview
  - hitl-pathway-choice (L3 only)

## Error Codes
- E010: HITL timeout (auto-confirm with original data, log warning)
- T001: Test assertion failed

## Test Points
- HITL_001: tier==3 from L1 → modal displays with reason=TIER_3 and stage=L1
- HITL_002: Edit of node value updates impact preview in real-time without page reload
- HITL_003: [✓ Confirm & Continue] → HITL_RESPONSE action=CONFIRMED, corrected_nodes populated
- HITL_004: [Cancel] → HITL_RESPONSE action=CANCELLED, pipeline continues unchanged
- HITL_005: 300s timeout → HITL_RESPONSE action=TIMEOUT, E010 logged
- HITL_006: Esc key → modal closes with action=CANCELLED
- HITL_007: MULTI_PATHWAY_CHOICE → pathway checkbox list rendered, selected_pathways in response
- HITL_008: DRIFT_DETECTED from GNN → modal opens with stage=ANY, reason=DRIFT_DETECTED
- HITL_009: All HITL interactions for trace_id appear in L5 report hitl_audit_trail

## Report Type & Evaluation Approach

HITL confirmation requirements vary by report type. The following table defines when user confirmation is required:

| Report Type | Purpose | Evaluation Method | User Confirmation | Trigger Condition |
|-------------|---------|-------------------|-------------------|-------------------|
| DOC_ACCURACY | Verify extracted data matches source | Human review via HITL table | REQUIRED | Always (for transparency) |
| AXIOM_QA_FAILURE | Identify axioms failing quality checks | Automated constraint checking + diagnostic | OPTIONAL | When any axiom.confidence_floor not met |
| CAUSAL_PREDICTION | Predict future failures/events | Bayesian inference + causal matrix | REQUIRED | When risk_score > 0.70 |
| ROOT_CAUSE | Trace failure origin | Causal chain backtracking | REQUIRED | When causal_chain broken or drift detected |
| COMPLIANCE_AUDIT | Verify against regulatory standards | Rule matching (IFRS, SOX, ISO) | OPTIONAL | Auto-pass if all rules satisfied |
| COMBINED | Multi-purpose audit | All of the above | As needed per section | Per constituent report type |

### User Confirmation Matrix by Scenario

| Scenario | Confirmation Required | Reason |
|----------|----------------------|--------|
| Overall confidence < 85% | YES | Data may be inaccurate |
| Individual node confidence < 60% | YES | Field requires manual review |
| Axiom pattern match failed | OPTIONAL | Auto-degrade or HITL based on severity |
| Causal prediction risk > 0.70 | YES | High-risk decision needs approval |
| Root cause chain broken | YES | Missing information requires user input |
| Compliance violation detected | OPTIONAL | Depends on violation severity (HIGH severity = REQUIRED) |
| User manually requests review | YES | Respect user intent |

### HITL Response Enrichment for Report Type

The HITL_RESPONSE payload SHALL include report_type:

```json
{
  "request_id":        "HITL_A3F2",
  "trace_id":          "string",
  "stage":             "...",
  "reason":            "...",
  "action":            "CONFIRMED | CANCELLED | TIMEOUT",
  "report_type":       "DOC_ACCURACY | AXIOM_QA_FAILURE | CAUSAL_PREDICTION | ROOT_CAUSE | COMPLIANCE_AUDIT | COMBINED",
  "corrected_nodes":   [...],
  "selected_pathways": [...],
  "operator_id":       "string or null",
  "timestamp":         "ISO8601"
}
```
