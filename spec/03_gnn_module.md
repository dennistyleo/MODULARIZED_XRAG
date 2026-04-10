# GNN Module Specification

Version: 1.0.0
Stage: Parallel (runs alongside L1–L4)
BUS Event In:  DATA_EXTRACTED
BUS Event Out: DRIFT_DETECTED

## Purpose
Build a 3D shape from extracted nodes and edges, detect structural deformation (drift),
and use time-axis rotation to trace root causes (BACKWARD) or predict failures (FORWARD).
The 3D shape is axis-rotatable — the time dimension can be adjusted to look backward
(root cause analysis) or forward (failure prediction).

## Scout Agent Metadata
- scout_id:                 gnn_scout_v1
- specialty:                Graph Neural Networks
- expertise_areas:          [relationship_detection, anomaly_detection, clustering]
- scoring_formula:          {relevance: 0.35, confidence: 0.35, past_performance: 0.20, speed: 0.10}
- average_evaluation_time_ms: 120

## Input
- nodes:          array of {id (N1..Nn), x, y, z}
- edges:          array of {source, target}
- inject_drift:   boolean (default: false) — test mode only
- drift_location: string (pattern: N[0-9]+, required if inject_drift: true)
- rotate_time:    FORWARD | BACKWARD | NONE (default: NONE)
- rotate_cycles:  integer (1–1000, default: 10)
- ideal_shape:    {nodes, edges} (provided by World Model for comparison)

## 3D Shape Formation
GNN builds a 3D shape where:
  - Each node is a point in 3D space (x, y, z)
  - Edges define the topology
  - The ideal shape is sourced from the axiom library via World Model
  - Deformation = deviation of actual shape from ideal shape

Visual reference (ideal shape):
  ●─────●─────●
 / \ / \ / \
●───●─●───●─●───●
/ \ / \ / \ / \ / \
●───●───●───●───●───●

Deformed shape with drift at N7:
  ●─────●─────●
 / \ / \ / \
●───●─●───●─●───●
/ \ / \ / \ / \⤵ / \
●───●───●───●───●↘──●
                    \
                     ● ← drift detected

## Deformation Detection
detect_3d_shape_drift():
  1. Compare actual node positions to ideal shape
  2. Calculate per-node deviation_score
  3. If max deviation_score > drift_threshold (default: 0.15) → drift_detected = true
  4. Identify drift_location as the node with highest deviation
  5. Output drift_magnitude (0–1)

## Time Rotation
rotate_time_dimension(direction):
  direction = BACKWARD → trace_root_cause(drift_location):
    - Rotate time axis backward cycle by cycle
    - Identify the earliest node where deviation began
    - Return root_cause_chain (e.g., ["N3", "N5", "N7"])

  direction = FORWARD → predict_failure_timeline():
    - Extrapolate drift trajectory forward
    - Estimate which node will reach failure threshold and when
    - Return prediction string and cycles_to_failure integer

## Collaboration with World Model
GNN sends DRIFT_DETECTED to World Model.
World Model responds with ideal shape for the domain.
If GNN drift location exists in ideal shape at same position → noise (not real).
If ideal shape shows no drift at that location → confirmed real anomaly.

## Output (DRIFT_DETECTED payload)
- shape_formed:      boolean
- shape_nodes:       array of {id, x, y, z} (deformed positions)
- drift_detected:    boolean
- drift_location:    string or null (e.g., "N7")
- drift_magnitude:   number (0–1) or null
- root_cause:        string or null (entry point node)
- root_cause_chain:  array of strings or null (e.g., ["N1","N2","N3","N7"])
- prediction:        string or null (human-readable failure prediction)
- cycles_to_failure: integer or null
- confidence:        number (0–1)
- scout_score:       number (0–1, from Axiom Democracy formula)

## Error Codes
- E006: Drift detection computation failed (use drift_detected=false as fallback, log warning)
- E005: GNN processing timeout (retry 3 times)
- T001: Test assertion failed (test harness only)

## Test Points
- GNN_001: Perfect 10-node shape formation → shape_formed=true, drift_detected=false
- GNN_002: Drift injection at N7, magnitude 0.15 → drift_detected=true, drift_location="N7"
- GNN_003: Time rotation BACKWARD from N7 → root_cause_chain starts at N3 or earlier
- GNN_004: Time rotation FORWARD from N7 → cycles_to_failure is integer > 0
- GNN_005: Ideal shape matches actual shape → deviation_score < drift_threshold, no drift
- GNN_006: GNN sends drift location to World Model → is_real_anomaly returned
