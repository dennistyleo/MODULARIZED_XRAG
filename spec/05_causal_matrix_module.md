# Causal Matrix Module Specification

Version: 1.0.0
Stage: Parallel (runs alongside GNN + World Model)
BUS Event In:  SHAPE_COMPARED
BUS Event Out: CAUSAL_MATRIX_READY

## Purpose
Calculate causal relationships between every node and edge using Bayesian inference.
Trace the root cause chain from the drift origin to the predicted failure node.
Provide probability of failure and estimated cycles to failure.

## Input
- nodes:          array (min 2, pattern: N[0-9]+)
- edges:          array
- drift_location: string or null (pattern: N[0-9]+)
- difference_map: 2D matrix from World Model (positional differences at each node)

## Causal Matrix Construction
generate_causal_matrix():
  1. Initialize N×N matrix with zeros (N = number of nodes)
  2. For each edge (source, target):
     matrix[source][target] = causal_weight (derived from edge.causal_strength)
  3. If drift_location provided:
     amplify weights along paths passing through drift_location
  4. Normalize each row so sum <= 1.0

## Example Causal Matrix (10-node system, drift at N7)
     N1   N2   N3   N4   N5   N6   N7   N8   N9   N10
N1 [ 0.0, 0.8, 0.2, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0 ]
N2 [ 0.0, 0.0, 0.9, 0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0 ]
N3 [ 0.0, 0.0, 0.0, 0.7, 0.3, 0.0, 0.0, 0.0, 0.0, 0.0 ]
N4 [ 0.0, 0.0, 0.0, 0.0, 0.6, 0.4, 0.0, 0.0, 0.0, 0.0 ]
N5 [ 0.0, 0.0, 0.0, 0.0, 0.0, 0.5, 0.5, 0.0, 0.0, 0.0 ]
N6 [ 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.4, 0.6, 0.0, 0.0 ]
N7 [ 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.3, 0.7, 0.0 ]
N8 [ 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.2, 0.8 ]
N9 [ 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0 ]
N10[ 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0 ]

Interpretation:
  Causal chain: N1 → N2 → N3 → N4 → N5 → N6 → N7 (drift) → N8 → N9 → N10 (failure)
  N7 has 70% causal weight toward N8 and 30% toward N9.
  Failure at N10 is inevitable if drift at N7 continues.

## Root Cause Tracing
trace_root_cause(start_node):
  Walk backward through the causal matrix from drift_location.
  Follow the highest-weight predecessor at each step.
  Return the full chain array: ["N1", "N2", "N3", "N7"] (root → drift).

## Failure Probability
probability_of_failure = product of causal weights along root_cause_chain
  e.g., 0.8 × 0.9 × 0.7 × 0.3 × 0.7 ≈ 0.106 (before normalization)
  Normalized to [0, 1] relative to the chain length.

## Output (CAUSAL_MATRIX_READY payload)
- causal_matrix:          2D array of numbers (0–1), N×N
- root_cause_chain:       array of strings (e.g., ["N1","N2","N3","N7"])
- probability_of_failure: number (0–1)
- cycles_to_failure:      integer or null
- recommendation:         string (human-readable action)

## Error Codes
- E005: Causal matrix computation timeout (retry 3 times)
- E007: Causal chain broken (< 1 path connects drift to terminal node)
- T001: Test assertion failed (test harness only)

## Test Points
- CAUSAL_001: 10-node matrix generated with correct N1→N10 chain
- CAUSAL_002: trace_root_cause(N7) returns chain starting at N1
- CAUSAL_003: probability_of_failure > 0 when drift is present
- CAUSAL_004: drift_location=null → all weights equal, no dominant chain
- CAUSAL_005: E007 logged when no path exists between drift node and any terminal node

## Root Cause Analysis (RCA) User Confirmation

When report_type = ROOT_CAUSE, the following conditions require user confirmation:

| Condition | HITL Required | Action |
|-----------|---------------|--------|
| causal_chain length >= 5 | OPTIONAL | User may review long chain |
| causal_chain broken (no path to terminal) | YES | User must provide missing link |
| probability_of_failure > 0.70 | YES | User must confirm before action |
| root_cause_chain contains drift_location | OPTIONAL | User may verify |
| Multiple possible root causes found | YES | User selects the most likely |

### RCA Report HITL Interaction

When HITL is triggered for ROOT_CAUSE report:
1. Display causal chain visualization
2. Highlight the broken link (if any)
3. Present possible root cause candidates
4. User selects or confirms the root cause
5. User's selection becomes the official root_cause in final report
