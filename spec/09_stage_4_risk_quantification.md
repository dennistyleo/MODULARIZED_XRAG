# Stage 4: Causal / Risk Quantification Specification

Version: 1.0.0
Stage Name: L4 — BAYESIAN_RISK
BUS Event In:  PATHWAY_FILTERED
BUS Event Out: RISK_ASSESSED

## Purpose
Combine filtered pathways with causal matrix output, GNN drift data, and World Model
comparison to produce a final composite risk score using Bayesian inference.
Each surviving pathway receives its own risk score. The dominant pathway defines
the system-level tier classification.

## L4 Agent Role (Scout Perspective)
The L4 agent is the Risk Scout:
  "I calculate risk for each pathway using Bayesian inference."
  "I integrate causal matrix weights, drift magnitude, and shape deviation."
  "I report per-pathway risk scores and the system composite score."
  "If confidence intervals overlap significantly, I call HITL."

## Scout Agent Metadata
- scout_id:                  l4_scout_v1
- specialty:                 Bayesian Risk Assessment
- expertise_areas:           [risk_quantification, bayesian_inference, uncertainty_estimation]
- scoring_formula:           {relevance: 0.35, confidence: 0.35, past_performance: 0.20, speed: 0.10}

## Input
Receives payload from PATHWAY_FILTERED event:
- filtered_pathways: array of {hypothesis_id, axiom_id, risk_label, severity, final_risk_score}
- trace_id:          string

Also reads from BUS cache (via bus.get_cached()):
- CAUSAL_MATRIX_READY: {causal_matrix, root_cause_chain, probability_of_failure}
- DRIFT_DETECTED:      {drift_detected, drift_magnitude, cycles_to_failure}
- SHAPE_COMPARED:      {deviation_score, is_real_anomaly}

## Per-Pathway Bayesian Risk Scoring
For each pathway:
  bayesian_risk = prior_risk × likelihood(data | pathway) / evidence

  Simplified approximation:
  pathway_risk_score = (pathway.final_risk_score × 0.6) +
                       (probability_of_failure × 0.4)

  Risk levels:
  - 0.00–0.23: Very Low
  - 0.24–0.45: Medium
  - 0.46–0.70: High
  - 0.71–1.00: Critical

Example (from PDF):
  Fourier Transform:     Risk Score 0.23 (Low)
  Arrhenius Model:       Risk Score 0.45 (Medium)
  GNN 3D Shape Analysis: Risk Score 0.12 (Very Low)  ← recommended

## Composite Score Formula
composite_score = (
    0.40 × max(pathway.final_risk_score for pathway in filtered_pathways) +
    0.30 × probability_of_failure +
    0.20 × (deviation_score if is_real_anomaly else 0.0) +
    0.10 × (drift_magnitude if drift_detected else 0.0)
)

## Tier Classification
- TIER_1 (ACCEPT):  composite_score < 0.40
- TIER_2 (REVIEW):  0.40 <= composite_score < 0.70
- TIER_3 (REFUSE):  composite_score >= 0.70

## HITL Trigger Conditions (L4 stage)
1. composite_score >= 0.70 AND original assessment.tier != 3   → HITL_REQUEST (reason: SCORE_ESCALATION)
2. Confidence intervals of top-2 pathways overlap significantly → HITL_REQUEST (reason: CI_OVERLAP)
   (overlap = |pathway_1.risk_score - pathway_2.risk_score| < 0.05)

## Output (RISK_ASSESSED payload)
- composite_score:        number (0–1)
- tier:                   1 | 2 | 3
- tier_label:             TIER_1 | TIER_2 | TIER_3
- per_pathway_risks:      array of {hypothesis_id, axiom_id, pathway_risk_score, risk_level}
- recommended_pathway:    hypothesis_id of the lowest-risk pathway
- contributing_factors: {
    pathway_score:     number,
    causal_score:      number,
    shape_deviation:   number,
    drift_contribution: number
  }
- dominant_risk_label:  string
- root_cause_chain:     array of strings
- cycles_to_failure:    integer or null
- trace_id:             string

## Error Codes
- E006: Drift data missing from BUS cache (use 0.0 as fallback, log warning)
- E007: No filtered pathways to quantify
- T001: Test assertion failed

## Test Points
- STAGE4_001: composite_score >= 0.70 → tier=3, HITL_REQUEST reason=SCORE_ESCALATION
- STAGE4_002: Missing drift data falls back to 0.0 without crash, E006 logged
- STAGE4_003: All four contributing_factors present and sum approximately = composite_score
- STAGE4_004: composite_score < 0.40 → tier=1, TIER_1, ACCEPT
- STAGE4_005: CI_OVERLAP: top two pathways within 0.05 → HITL_REQUEST reason=CI_OVERLAP
- STAGE4_006: GNN pathway has lowest per_pathway_risk → recommended_pathway = GNN hypothesis_id

## Composite Score Breakdown Transparency
The composite_score calculation must be fully transparent in the audit trail:

composite_score = (A × 0.40) + (B × 0.30) + (C × 0.20) + (D × 0.10)

Where:
- A = max_pathway_risk (from surviving pathways)
- B = probability_of_failure (from causal matrix)
- C = deviation_score × is_real_anomaly (from world model, 0 if not real)
- D = drift_magnitude × drift_detected (from GNN, 0 if no drift)

The audit trail must record:
- max_pathway_risk value and which pathway contributed it
- probability_of_failure from causal matrix
- deviation_score and is_real_anomaly flag
- drift_magnitude and drift_detected flag
- Each term's product: (A×0.40), (B×0.30), (C×0.20), (D×0.10)
- Final composite_score
- Derived tier (TIER_1/2/3)
- HITL trigger reason if composite_score ≥ 0.70 and original tier != 3

## Risk Thresholds for CAUSAL_PREDICTION Report

When report_type = CAUSAL_PREDICTION, the following thresholds determine HITL requirements:

| Risk Score | Risk Level | HITL Required | Action |
|------------|------------|---------------|--------|
| < 0.40 | LOW | NO | Auto-approve prediction |
| 0.40 - 0.69 | MEDIUM | OPTIONAL | User may review |
| 0.70 - 0.89 | HIGH | YES | User must confirm before action |
| ≥ 0.90 | CRITICAL | YES (with escalation) | Manager override may be required |

### Prediction Confidence Requirements

For CAUSAL_PREDICTION reports:
- Minimum confidence for auto-accept: 85%
- Confidence interval must be reported: [lower, upper]
- If confidence interval width > 0.30 → HITL_REQUEST (reason: WIDE_CONFIDENCE_INTERVAL)
