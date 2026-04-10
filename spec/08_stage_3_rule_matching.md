# Stage 3: Admissibility Specification

Version: 1.0.0
Stage Name: L3 — CONSTRAINT_ELECTION
BUS Event In:  HYPOTHESIS_GENERATED
BUS Event Out: PATHWAY_FILTERED

## Purpose
Check all surviving hypotheses against domain-specific constraint rules and the axiom registry.
Run the General Election (parallel evaluation of top axioms).
Support axiom coalitions (ensemble methods).
Present multi-pathway selection UI if multiple valid pathways survive.

## L3 Agent Role
The L3 agent is the Admissibility Scout:
  "I check constraints: which pathways are actually allowed?"
  "I run the General Election — competing axioms evaluate the data in parallel."
  "I may form coalitions between axioms for better combined results."
  "If no pathway passes, I call HITL."

## Input
Receives payload from HYPOTHESIS_GENERATED event:
- hypotheses:  array of {hypothesis_id, axiom_id, pathway_nodes, winning_score, explanation}
- domain:      string
- trace_id:    string

## General Election (Parallel Evaluation)
Run top-5 candidates simultaneously:
  For each candidate axiom:
    - Evaluate data against axiom's constraint ruleset
    - Produce per-pathway evaluation: {risk_label, severity, confidence_floor_met, matched_pattern}
  Rank results by winning_score (Axiom Democracy formula).

## Axiom Matching Algorithm
For each surviving hypothesis:
  1. Extract ontology_labels of pathway_nodes
  2. Check if any axiom.pattern is a subsequence of extracted labels
  3. If matched: assign axiom_id, risk_label, severity
  4. If unmatched: assign risk_label = UNKNOWN, severity = LOW

## Tie-Breaking Rules (equal Winning_Score)
Resolution order (highest priority first):
  1. Specificity: prefer axioms with more specific domain patterns
  2. Recency:     prefer axioms registered more recently
  3. User preference: if user previously selected an axiom for this domain, prefer it
  4. Randomized:  add small noise (±0.001) to scores, log for reproducibility

## Axiom Coalition (Ensemble Methods)
Axioms with complementary expertise can form coalitions:
  coalition = {
    name:    "Thermal Analysis All-Stars",
    members: ["thermal_equation_v1", "arrhenius_model"],
    weight:  [0.6, 0.4],
    combined_output: weighted average of member outputs,
    consensus_score: weighted average of member winning_scores
  }

Coalition replaces individual axioms in the output if consensus_score > any individual.

## Multi-Axiom Pathway Selection UI
After L3, if multiple valid pathways survive, present the user with:
  "Multiple evaluation pathways detected. Choose one or more:"
  ☐ RSI (Relative Strength Index)   — Best for momentum analysis
  ☐ MACD (Moving Average)           — Best for trend following
  ☐ EMA Twins (VEGAS)               — Best for volatility detection
  [Generate All]  [Generate Selected]  [Cancel]

This triggers HITL_REQUEST (reason: MULTI_PATHWAY_CHOICE) if multiple pathways survive.

## HITL Trigger Conditions (L3 stage)
1. Multiple valid pathways survive AND score difference < 0.05 → HITL_REQUEST (reason: MULTI_PATHWAY_CHOICE)
2. No pathway passes constraints                               → HITL_REQUEST (reason: NO_ADMISSIBLE_PATHWAY)

## Axiom Registry Hot-Reload
POST /api/axioms/register immediately activates new axiom for all subsequent L3 evaluations.
Axiom record:
{
  "axiom_id":         "CONTRACT_D_001",
  "domain":           "CONTRACT",
  "pattern":          ["PARTY", "OBLIGATION", "PENALTY"],
  "risk_label":       "BREACH_RISK",
  "severity":         "HIGH",
  "confidence_floor": 0.70
}

## Output (PATHWAY_FILTERED payload)
- filtered_pathways: array of {
    hypothesis_id:    string,
    axiom_id:         string or null,
    coalition_id:     string or null,
    risk_label:       string,
    severity:         LOW | MEDIUM | HIGH | CRITICAL,
    matched_pattern:  array of strings or null,
    final_risk_score: number (0–1),
    winning_score:    number (0–1)
  }
- unmatched_count:  integer
- election_id:      string (e.g., 2026-04-10-001)
- trace_id:         string

## Error Codes
- E004: Axiom registry empty or unreachable (no retry, use UNKNOWN labels)
- E007: No pathways survive admissibility check
- T001: Test assertion failed

## Test Points
- STAGE3_001: CONTRACT_D_001 axiom matches BREACH_RISK pathway
- STAGE3_002: Unregistered pattern → risk_label=UNKNOWN, severity=LOW
- STAGE3_003: Pathway below confidence_floor is excluded from output
- STAGE3_004: Empty axiom registry → E004, all surviving pathways labeled UNKNOWN
- STAGE3_005: Hot-reload axiom via /api/axioms/register → matched in next pipeline run
- STAGE3_006: Thermal Coalition formed → consensus_score > individual member scores
- STAGE3_007: Tie-breaking: more specific axiom preferred over generic when scores equal

## Coalition Consensus Calculation Transparency
For each coalition formed:
  coalition_consensus = Σ(member.winning_score × member.weight) / Σ(weights)

The audit trail must record:
- coalition_name
- member_axiom_ids
- member_weights
- member_winning_scores
- weighted_sum (Σ member.winning_score × member.weight)
- total_weight (Σ weights)
- final_consensus_score
- comparison to individual member scores (was coalition better?)
