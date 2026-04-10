# Module Registry Specification

Version: 1.0.0

## Purpose
Provide two distinct self-registration mechanisms:
1. **ModuleRegistry** — registers pipeline execution modules (RAG, L1–L5, GNN, WM, CAUSAL)
2. **ScoutRegistry** — registers scout evaluation agents that compete to analyze data

Both registries communicate exclusively through SovereignBUS.

---

## Part 1: Module Registry (Pipeline Modules)

### Interface (Python)
class ModuleRegistry:
  register(module_id, module_instance, subscriptions)
    - module_id:      unique string (e.g., "rag_module")
    - module_instance: object with async handle(message) method
    - subscriptions:   list of BUS event names

  get(module_id)     → module_instance or None
  list_all()         → list of {module_id, subscriptions, status}
  unregister(module_id) → bool
  health_check(module_id) → {status: OK | DEGRADED | OFFLINE, latency_ms}

### Self-Registration Pattern (Python)
Each module calls at __init__:
  self.registry.register(
      module_id     = "rag_module",
      module        = self,
      subscriptions = ["DATA_EXTRACTED"]
  )

### Module Status Lifecycle
STARTING → READY → DEGRADED → OFFLINE
- STARTING:  registered but not yet handling events
- READY:     handling events normally
- DEGRADED:  handling events but returning errors > 20% of requests
- OFFLINE:   not responding to health_check within 5 seconds

### Required Registered Modules (10)
- rag_module
- gnn_module
- world_model_module
- causal_matrix_module
- stage_1_data_validation    (L1: Ontological)
- stage_2_constraint_pruning (L2: Hypothesis)
- stage_3_rule_matching      (L3: Admissibility)
- stage_4_risk_quantification (L4: Causal/Risk)
- stage_5_report_generation  (L5: Explainability)
- hitl_modal_handler

### Health Check Endpoint
GET /api/health
Response:
{
  "status": "OK | DEGRADED | OFFLINE",
  "modules": [
    {"module_id": "rag_module", "status": "READY", "latency_ms": 12},
    ...
  ],
  "scouts": [
    {"scout_id": "gnn_scout_v1", "status": "READY", "last_score": 0.88},
    ...
  ],
  "timestamp": "ISO8601"
}

---

## Part 2: Scout Registry (Competitive Agent Registry)

### Purpose
Manages scout agents that evaluate data and compete for selection via Axiom Democracy.
Scouts are registered at startup and can be added dynamically.

### Interface (Python)
class ScoutRegistry:
  register(scout_id, scout_instance)
    - scout_id:       unique string (e.g., "gnn_scout_v1")
    - scout_instance: object implementing evaluate(talent_data) → report_card

  get(scout_id)      → scout_instance or None
  list_all()         → list of {scout_id, specialty, expertise_areas, past_record}
  evaluate_all(talent_data) → list of report_cards sorted by winning_score desc

### Scout Self-Registration Pattern (Python)
Each scout calls at __init__:
  self.registry.register(
      scout_id = "gnn_scout_v1",
      scout    = self
  )

### Scout evaluate() Contract
evaluate(talent_data) returns:
{
  "scout_id":          "gnn_scout_v1",
  "specialty":         "Graph Neural Networks",
  "relevance_score":   0.92,
  "confidence_score":  0.87,
  "past_performance":  0.89,
  "speed":             0.85,  # normalized, 1.0 = fastest
  "winning_score":     0.88,  # (Relevance×0.4)+(Confidence×0.3)+(Past×0.2)+((1-Cost)×0.1)
  "report":            {...},  # scout-specific report content
  "explanation":       "string"
}

### Required Registered Scouts (8)
- l1_scout_v1   (Ontological classification)
- l2_scout_v1   (Hypothesis generation)
- l3_scout_v1   (Admissibility checking)
- l4_scout_v1   (Risk assessment)
- l5_scout_v1   (Report generation)
- gnn_scout_v1  (Graph neural networks)
- wm_scout_v1   (World model / context)
- causal_scout_v1 (Causal inference)

### Orchestrator Ranking
After all scouts submit evaluations, the Orchestrator:
  1. Calls ScoutRegistry.evaluate_all(talent_data)
  2. Ranks by winning_score descending
  3. Identifies top scout and any coalitions
  4. Emits HITL_REQUEST if user review needed (HITL_COMBINE)
  5. Proceeds with winning scout's report

### Coalition Formation
Scouts can form coalitions:
  coalition = {
    "name":     "Thermal Analysis All-Stars",
    "members":  ["l4_scout_v1", "gnn_scout_v1", "wm_scout_v1"],
    "weights":  [0.40, 0.35, 0.25],
    "combined_report": {...},
    "consensus_score": 0.86
  }
  Coalition is adopted if consensus_score > winning individual scout score.

---

## Error Codes
- E009: Module or Scout not found in registry
- E005: Module or Scout health check timeout
- T001: Test assertion failed

## Test Points
- REG_001: All 10 pipeline modules auto-register at startup
- REG_002: All 8 scouts auto-register at startup
- REG_003: get() returns None for unknown module_id or scout_id
- REG_004: Duplicate registration raises ValueError
- REG_005: health_check timeout → status=OFFLINE in /api/health response
- REG_006: ScoutRegistry.evaluate_all() returns 8 report_cards sorted by winning_score
- REG_007: Coalition consensus_score > all individual scouts → coalition adopted
- REG_008: New scout added via ScoutRegistry.register() is included in next evaluate_all()
