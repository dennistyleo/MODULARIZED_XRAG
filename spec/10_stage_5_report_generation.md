# Stage 5: Explainability / Report Generation Specification

Version: 1.0.0
Stage Name: L5 — AUDIT_SYNTHESIS
BUS Event In:  RISK_ASSESSED
BUS Event Out: REPORT_READY

## Purpose
Synthesize all pipeline outputs into a structured, human-readable audit report.
Every HITL interaction and every agent decision must appear in the audit trail.
Support multi-report generation when multiple pathways were selected by the user.
The report is transparent and explainable — it must not be a black box.

## L5 Agent Role
The L5 agent is the Report Scout:
  "I generate the final audit report with full trace."
  "I include every HITL interaction as part of the audit trail."
  "If multiple axiom pathways were chosen, I generate a report for each."
  "I present the outcome in a way that a non-expert can verify."

## Input
Receives payload from RISK_ASSESSED event:
- composite_score:       number (0–1)
- tier:                  1 | 2 | 3
- tier_label:            TIER_1 | TIER_2 | TIER_3
- per_pathway_risks:     array
- contributing_factors:  object
- recommended_pathway:   string
- dominant_risk_label:   string
- root_cause_chain:      array of strings
- cycles_to_failure:     integer or null
- trace_id:              string

Also reads from BUS cache:
- DATA_EXTRACTED:        original nodes, edges, domain, fingerprint
- CAUSAL_MATRIX_READY:   causal_matrix, probability_of_failure
- DRIFT_DETECTED:        drift_detected, drift_location, prediction
- PATHWAY_FILTERED:      filtered_pathways with axiom details, election_id
- ONTOLOGY_CLASSIFIED:   ontology_path
- HITL events:           all HITL_REQUEST and HITL_RESPONSE events for this trace_id

## Report Structure
report:
  header:
    trace_id:           string
    session_id:         string (SESSION_{timestamp}_{user})
    timestamp:          ISO8601
    domain:             string
    ontology_path:      string
    file_name:          string
    tier:               integer
    tier_label:         string
    election_id:        string
  executive_summary:
    composite_score:    number
    dominant_risk:      string
    recommendation:     string
  data_table:
    columns: [Node ID, Name, Value, Confidence, Risk Label, Status]
    rows:    array (one row per classified node)
  causal_chain:
    root_cause:             string (entry node)
    chain:                  array of strings (full path)
    probability_of_failure: number
    cycles_to_failure:      integer or null
    narrative:              string (e.g., "N1 → N2 → N3 → N7 (drift) → N10 (failure)")
  pathway_summary:
    top_pathways:    array of {axiom_id, risk_label, severity, pathway_risk_score}
    recommended:     axiom_id
    election_id:     string
  contributing_factors: object
  gnn_summary:
    drift_detected:  boolean
    drift_location:  string or null
    prediction:      string or null
    is_real_anomaly: boolean
  hitl_audit_trail:
    interactions: array of {
      request_id:      string,
      reason:          string,
      stage:           L1 | L2 | L3 | L4 | L5 | UPLOAD,
      action:          CONFIRMED | CANCELLED | TIMEOUT,
      corrected_nodes: array or null,
      operator_id:     string,
      timestamp:       ISO8601
    }
  appendix:
    raw_nodes:      array
    raw_edges:      array
    causal_matrix:  2D array
    data_fingerprint: object

## Multi-Report Support
If user selected multiple pathways in L3:
  Generate one report per selected pathway.
  Each report has a unique report_id: REPORT_{election_id}_{axiom_id}
  All reports share the same trace_id.

## HITL Trigger Conditions (L5 stage)
1. User wants to customize report format → HITL_REQUEST (reason: REPORT_CUSTOMIZATION)

## Export Formats
- JSON: application/json (always generated)
- HTML: rendered via Jinja2 template for print / PDF export
- CSV:  data_table rows only

## Output (REPORT_READY payload)
- reports:      array of report objects (one per selected pathway, or one if single pathway)
- export_urls:  {json: string, html: string, csv: string}
- trace_id:     string

## Error Codes
- E007: Causal chain data missing from BUS cache (log warning, use empty array)
- T001: Test assertion failed

## Test Points
- STAGE5_001: Report header contains all required fields including session_id and election_id
- STAGE5_002: data_table rows count equals number of classified nodes
- STAGE5_003: HTML export renders without template error
- STAGE5_004: Missing GNN data → gnn_summary fields = null, no crash
- STAGE5_005: causal_chain.chain matches root_cause_chain from stage 4
- STAGE5_006: hitl_audit_trail contains all HITL interactions for the trace_id
- STAGE5_007: Multi-pathway: 2 pathways selected → 2 report objects in reports array

## Audit Trail Requirements (Enhanced)
The audit trail MUST include for each stage:

### L1: ONTOLOGICAL_SCOPING
- ontology_path determined
- confidence level
- alternative classifications considered
- HITL intervention (if multiple classifications possible)

### L2: HYPOTHESIS_CAMPAIGN
- All axioms that campaigned with their Winning_Score calculation breakdown
- Primary election results (top 5)
- Tie-breaking log (if any)
- Selected pathways passed to L3

### L3: CONSTRAINT_ELECTION
- Constraint satisfaction results per axiom
- Coalition formation details (if any)
- User multi-pathway selection (if HITL invoked)
- Final admissible pathways

### L4: BAYESIAN_RISK
- Per-pathway risk scores with calculation breakdown
- Composite score with factor decomposition (A, B, C, D)
- Tier determination
- HITL intervention (if CI overlap or score escalation)

### L5: AUDIT_SYNTHESIS
- Export formats generated
- Report ID and trace ID
- Digital seal and logo placement confirmation

## Report Branding Requirements
- Logo: static/aichip-logo-home.png (header, left-aligned)
- Seal: static/seal_xrag_core_logo.png (footer, right-aligned)
- Report title: "SOVEREIGN MATRIX AUDIT REPORT"
- Classification stamp: CONFIDENTIAL | INTERNAL | PUBLIC (configurable)
- Page format: A4 (210mm × 297mm)
- Margins: 2cm all sides
- Footer: "Generated by Sovereign Matrix v{version} | Confidential | Page {page} of {total}"

## Report Type Determination

The report_type is determined by the user's intent and pipeline context:

| report_type | Determination Rule |
|-------------|---------------------|
| DOC_ACCURACY | Default when user uploads file without specific command |
| AXIOM_QA_FAILURE | When user selects "Diagnose Axioms" or axiom confidence_floor violations detected |
| CAUSAL_PREDICTION | When user requests "Predict failure" or GNN drift_detected == true |
| ROOT_CAUSE | When user requests "Find root cause" or causal_chain broken |
| COMPLIANCE_AUDIT | When user specifies compliance standard (e.g., "IFRS 15 audit") |
| COMBINED | When multiple report types are requested or detected |

### Report Type-Specific Output Sections

| Section | DOC_ACCURACY | AXIOM_QA_FAILURE | CAUSAL_PREDICTION | ROOT_CAUSE | COMPLIANCE_AUDIT |
|---------|--------------|------------------|--------------------|------------|------------------|
| Data Table | ✅ Full | ✅ Partial | ✅ Summary | ✅ Full | ✅ Full |
| Causal Chain | ❌ | ❌ | ✅ Full | ✅ Full | ❌ |
| Prediction | ❌ | ❌ | ✅ Required | ❌ | ❌ |
| Root Cause | ❌ | ❌ | ❌ | ✅ Required | ❌ |
| Axiom QA Results | ❌ | ✅ Required | ❌ | ❌ | ❌ |
| Compliance Status | ❌ | ❌ | ❌ | ❌ | ✅ Required |
| Risk Assessment | ⚠️ Optional | ❌ | ✅ Required | ✅ Required | ⚠️ Optional |
| Recommendation | ✅ Required | ✅ Required | ✅ Required | ✅ Required | ✅ Required |

### Example: CAUSAL_PREDICTION Report Output

For report_type = CAUSAL_PREDICTION:
- Must include: prediction statement, confidence interval, cycles_to_failure, probability_of_failure
- Must include: risk assessment with tier classification
- Must include: recommended actions to mitigate predicted failure
- Optional: full data table (can be collapsed)
