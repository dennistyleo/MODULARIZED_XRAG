# World Model Module Specification

Version: 1.0.0
Stage: Parallel (runs alongside GNN)
BUS Event In:  DRIFT_DETECTED
BUS Event Out: SHAPE_COMPARED

## Purpose
Maintain the "perfect world" — a library of ideal 3D shapes for each domain and axiom.
Compare GNN's detected actual shape against the ideal shape to confirm whether a drift
is a real anomaly or measurement noise.

## Multi-Domain Model Library
The World Model stores ideal shapes derived from the following physical models:

| Domain    | Model             | Equation / Principle                         |
|-----------|-------------------|----------------------------------------------|
| AEROSPACE | Arrhenius Model   | τ = A · exp(Ea / kT) — thermal aging         |
| AEROSPACE | Fourier Transform | Signal decomposition for frequency analysis  |
| FINANCIAL | Black-Scholes     | Option pricing, volatility surface           |
| TECHNICAL | Navier-Stokes     | Fluid dynamics for thermal/pressure systems  |
| CONTRACT  | Obligation Graph  | Party → Obligation → Clause → Penalty        |
| GENERAL   | Bayesian Inference| Probabilistic dependency graph               |

Each domain's model produces a canonical ideal shape (nodes + edges with ideal positions).

## Input
- domain:          CONTRACT | FINANCIAL | TECHNICAL | AEROSPACE | GENERAL
- extracted_shape: {nodes: [{id, x, y, z}], edges: [{source, target}]}
- drift_location:  string or null (received from GNN via DRIFT_DETECTED event)

## Comparison Process
compare_shape():
  1. Load ideal shape for domain from axiom library
  2. Align actual shape to ideal using node IDs
  3. Calculate per-node deviation:
     deviation[n] = sqrt((x_actual - x_ideal)² + (y_actual - y_ideal)² + (z_actual - z_ideal)²)
  4. Compute overall deviation_score = mean(deviation) normalized to [0, 1]
  5. At drift_location: if ideal shape position == actual → noise
                        if positions differ significantly → is_real_anomaly = true

## Collaboration Protocol
1. GNN emits DRIFT_DETECTED with drift_location
2. World Model receives location, loads ideal shape for domain
3. World Model compares ideal vs. actual at drift_location
4. World Model emits SHAPE_COMPARED with is_real_anomaly
5. If is_real_anomaly == true → World Model triggers Causal Matrix via SHAPE_COMPARED
6. Causal Matrix agent uses difference_map to compute causal weights

## Output (SHAPE_COMPARED payload)
- ideal_shape:       {nodes: [{id, x, y, z}], edges: [{source, target}]}
- is_real_anomaly:   boolean (true = drift is real, not noise)
- deviation_score:   number (0–1, 0 = perfect match)
- deviation_map:     array of {node_id, deviation}
- difference_map:    2D matrix of positional differences (used by Causal Matrix)
- recommendation:    string (human-readable action recommendation)

## Error Codes
- E004: Ideal shape not found for domain (no retry, emit warning)
- E005: World Model computation timeout (retry 3 times)

## Test Points
- WM_001: AEROSPACE domain → Arrhenius ideal shape loaded correctly
- WM_002: Actual shape matches ideal → deviation_score < 0.05, is_real_anomaly=false
- WM_003: Drift at N7 confirmed real → is_real_anomaly=true, deviation_map contains N7 entry
- WM_004: Unknown domain → E004 logged, deviation_score=null, recommendation = "Manual review"
- WM_005: difference_map is passed to Causal Matrix and contains non-zero values at drift_location
