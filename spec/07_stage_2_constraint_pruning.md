# Stage 2: Hypothesis Generation Specification

Version: 1.0.0
Stage Name: L2 — HYPOTHESIS_CAMPAIGN
BUS Event In:  ONTOLOGY_CLASSIFIED
BUS Event Out: HYPOTHESIS_GENERATED

## Purpose
Generate candidate mathematical pathways (hypotheses) based on the ontological
classification produced by L1. Run axiom self-evaluation (campaigning) to score
each pathway. Apply Primary Election to filter the top candidates.

## L2 Agent Role
The L2 agent is the Hypothesis Scout:
  "Based on L1's classification, I generate candidate evaluation pathways."
  "I ask each axiom scout to evaluate the data and declare its relevance."
  "I pass the top-ranked pathways to L3 for admissibility checking."

## Input
Receives payload from ONTOLOGY_CLASSIFIED event:
- domain:           string
- ontology_path:    string (e.g., "Aerospace Materials > Thermal Cycling > Reliability")
- classified_nodes: array of {id, name, value, confidence, category, ontology_label}
- fingerprint:      data fingerprint from RAG
- trace_id:         string

## Candidate Mathematical Pathways by Domain
AEROSPACE:
  - Fourier Transform (signal analysis)
  - Arrhenius Model (thermal aging)
  - GNN 3D Shape Analysis (drift detection)
  - Navier-Stokes (fluid/pressure systems)

FINANCIAL:
  - RSI (Relative Strength Index) — momentum analysis
  - MACD (Moving Average Convergence) — trend following
  - EMA Twins / VEGAS — volatility detection
  - Black-Scholes — option pricing

CONTRACT:
  - Obligation Graph traversal
  - Penalty chain analysis
  - Party obligation coverage check

TECHNICAL:
  - Dependency graph analysis
  - Version compatibility matrix
  - Resource contention model

GENERAL:
  - Bayesian Inference
  - Linear regression baseline

## Axiom Self-Evaluation (Campaigning)
Each axiom scout evaluates the data fingerprint and returns:
{
  "axiom_id":        "thermal_equation_v1",
  "relevance_score": 0.92,
  "confidence_score": 0.87,
  "explanation":     "Data contains temperature cycling and cycles_to_failure. My specialty.",
  "predicted_output": {...},
  "uncertainty":     0.13,
  "computational_cost": 0.3,
  "campaign_slogan": "Thermal problems need thermal solutions."
}

## Primary Election (Filtering)
primary_election(candidates, fingerprint):
  1. Filter by relevance_score > 0.60
  2. Sort descending by relevance_score
  3. Return top 5 candidates

## HITL Trigger Conditions (L2 stage)
1. Multiple pathways have equal Winning_Score → HITL_REQUEST (reason: PATHWAY_TIE)
2. Zero pathways pass Primary Election filter  → HITL_REQUEST (reason: NO_HYPOTHESIS)

## Output (HYPOTHESIS_GENERATED payload)
- hypotheses: array of {
    hypothesis_id:          string,
    axiom_id:               string,
    pathway_nodes:          array of node IDs,
    relevance_score:        number (0–1),
    confidence_score:       number (0–1),
    winning_score:          number (0–1, from Axiom Democracy formula),
    computational_cost:     number (0–1),
    explanation:            string,
    constraint_violations:  array of rule_ids,
    pruning_reason:         string or null
  }
- pruned_count:    integer (axioms that did not pass primary election)
- retained_count:  integer
- trace_id:        string

## Error Codes
- E004: No axiom schema found for domain (no retry)
- E007: No hypotheses survive primary election
- T001: Test assertion failed (test harness only)

## Test Points
- STAGE2_001: AEROSPACE domain produces >= 3 candidate pathways
- STAGE2_002: Axiom with relevance_score < 0.60 is pruned from primary election
- STAGE2_003: Equal Winning_Score on two axioms → HITL_REQUEST reason=PATHWAY_TIE
- STAGE2_004: winning_score calculated correctly: (0.92×0.4)+(0.87×0.3)+(0.89×0.2)+((1-0.3)×0.1) ≈ 0.89
- STAGE2_005: Zero axioms pass filter → E007 logged and HITL_REQUEST emitted

## Winning Score Calculation Transparency
For each axiom, the Winning_Score is calculated as documented in 00_global_standards.md.
The audit trail must record for each axiom:
- relevance_score (with input fingerprint.domain_hints)
- confidence_score (from axiom self-evaluation)
- historical_success (from axiom.past_record)
- computational_cost (from axiom.cost)
- intermediate products: (relevance×0.4), (confidence×0.3), (historical×0.2), (cost_adj×0.1)
- final winning_score
- tie_break_method (if scores are equal)
