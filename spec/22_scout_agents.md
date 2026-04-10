# Scout Agents Specification

Version: 1.0.0

## Purpose
Define the Scout Agent layer — a competitive evaluation ecosystem where agents
assess extracted data from their domain specialty and compete for selection.
Scouts are distinct from pipeline modules: they evaluate and recommend;
modules execute. The orchestrator coordinates their competition.

---

## Core Concepts

### Talent (Input Data)
The extracted RAG output (player profile):
{
  "talent_id":       "SAAB_CFRP_001",
  "position":        "Aerospace Material",
  "stats":           {extracted node values},
  "tools":           ["HASS", "HALT", "Thermal Shock"],
  "potential_score": 0.72,  // RAG overall confidence
  "fingerprint":     {data fingerprint from RAG}
}

### Scout Agent
Each scout has a specialty and evaluates talent from its perspective:

| Scout ID         | Specialty                    | What It Evaluates                        |
|------------------|------------------------------|------------------------------------------|
| l1_scout_v1      | Ontological classification   | What TYPE of data is this?               |
| l2_scout_v1      | Hypothesis generation        | What evaluation methods apply?           |
| l3_scout_v1      | Admissibility / Constraints  | Does the talent meet requirements?       |
| l4_scout_v1      | Risk assessment              | What is the uncertainty / risk level?    |
| l5_scout_v1      | Report generation            | How to present findings?                 |
| gnn_scout_v1     | Graph Neural Networks        | How do data points connect and drift?    |
| wm_scout_v1      | World Model integration      | How does this fit into broader context?  |
| causal_scout_v1  | Causal inference             | What causes what?                        |

---

## Scout Agent Base Class

### Python Definition
class ScoutAgent:
    """
    Base class for all Sovereign Matrix scout agents.
    Version: 1.0.0
    """
    def __init__(
        self,
        scout_id:          str,
        specialty:         str,
        expertise_areas:   list[str],
        scoring_formula:   dict[str, float],
        past_record:       dict[str, dict] = None
    ):
        self.scout_id       = scout_id
        self.specialty      = specialty
        self.expertise_areas = expertise_areas
        self.scoring_formula = scoring_formula  # {relevance, confidence, past_performance, speed}
        self.past_record    = past_record or {}
        self.evaluation_history: list[dict] = []

    def evaluate(self, talent_data: dict) -> dict:
        """Evaluate talent and return a scored report card."""
        relevance       = self.calculate_relevance(talent_data)
        confidence      = self.calculate_confidence(talent_data)
        speed           = self.measure_speed()
        past_perf       = self.get_past_performance(talent_data.get("domain"))
        winning_score = (
            relevance  * self.scoring_formula["relevance"] +
            confidence * self.scoring_formula["confidence"] +
            past_perf  * self.scoring_formula["past_performance"] +
            (1 - speed) * self.scoring_formula["speed"]
        )
        return {
            "scout_id":         self.scout_id,
            "specialty":        self.specialty,
            "relevance_score":  relevance,
            "confidence_score": confidence,
            "past_performance": past_perf,
            "speed":            speed,
            "winning_score":    winning_score,
            "report":           self.generate_report(talent_data),
            "explanation":      self.generate_explanation(relevance, confidence)
        }

    def calculate_relevance(self, talent_data: dict) -> float:
        raise NotImplementedError("Must implement calculate_relevance()")

    def calculate_confidence(self, talent_data: dict) -> float:
        raise NotImplementedError("Must implement calculate_confidence()")

    def generate_report(self, talent_data: dict) -> dict:
        raise NotImplementedError("Must implement generate_report()")

    def generate_explanation(self, relevance: float, confidence: float) -> str:
        raise NotImplementedError("Must implement generate_explanation()")

    def measure_speed(self) -> float:
        # Normalized speed from past evaluation_history. 1.0 = fastest benchmark.
        pass

    def get_past_performance(self, domain: str) -> float:
        return self.past_record.get(domain, {}).get("accuracy", 0.0)

---

## Specific Scout Implementations

### GNN Scout
class GNNScout(ScoutAgent):
    """
    Graph-based scout that detects anomalies, extracts relationships, and clusters nodes.
    Scout ID: gnn_scout_v1
    """
    def __init__(self):
        super().__init__(
            scout_id         = "gnn_scout_v1",
            specialty        = "Graph Neural Networks",
            expertise_areas  = ["relationship_detection", "anomaly_detection", "clustering"],
            scoring_formula  = {"relevance": 0.35, "confidence": 0.35, "past_performance": 0.20, "speed": 0.10},
            past_record      = {
                "aerospace": {"evaluations": 45, "accuracy": 0.89},
                "automotive": {"evaluations": 32, "accuracy": 0.85}
            }
        )

    def generate_report(self, talent_data: dict) -> dict:
        return {
            "anomalies":      self.detect_anomalies(talent_data),
            "relationships":  self.extract_relationships(talent_data),
            "clusters":       self.perform_clustering(talent_data),
            "recommendation": self.make_recommendation()
        }

### L4 Risk Scout
class L4RiskScout(ScoutAgent):
    """
    Bayesian risk assessment scout.
    Scout ID: l4_scout_v1
    """
    def __init__(self):
        super().__init__(
            scout_id        = "l4_scout_v1",
            specialty       = "Bayesian Risk Assessment",
            expertise_areas = ["risk_quantification", "bayesian_inference", "uncertainty_estimation"],
            scoring_formula = {"relevance": 0.35, "confidence": 0.35, "past_performance": 0.20, "speed": 0.10}
        )

    def generate_report(self, talent_data: dict) -> dict:
        return {
            "risk_level":          self.calculate_risk(talent_data),
            "confidence_interval": self.compute_confidence(talent_data),
            "uncertainty":         self.measure_uncertainty(talent_data),
            "recommendation":      self.make_recommendation()
        }

---

## Scout Report Card Format
{
  "scout_id":         "gnn_scout_v1",
  "specialty":        "Graph Neural Networks",
  "relevance_score":  0.92,
  "confidence_score": 0.87,
  "past_performance": 0.89,
  "speed":            0.85,
  "winning_score":    0.88,
  "report": {
    "anomalies":     3,
    "relationships": 5,
    "clusters":      2
  },
  "explanation": "This data has clear relational structure. I am highly relevant."
}

---

## Scouting Process Flow
1. RAG extracts talent data (player profile created)
2. All scouts notified: talent:available emitted on BUS
3. Each scout evaluates talent in parallel:
   - L1 Scout evaluates Ontology
   - L2 Scout evaluates Pathways
   - L3 Scout evaluates Constraints
   - L4 Scout evaluates Risk
   - GNN Scout evaluates Graph structure
   - WM Scout evaluates World context
   - CAUSAL Scout evaluates Causality
4. Scouting reports collected (report cards)
5. Orchestrator ranks scouts by Winning_Score
6. Coalition check: if coalition > best individual → adopt coalition
7. HITL Scouting Combine: present top scouts to user (General Manager)
8. User selects winner or accepts orchestrator's top pick

---

## Orchestrator Ranking Algorithm
rank_scout_evaluations(evaluations: list[dict]) -> list[dict]:
  1. Sort evaluations by winning_score descending
  2. Check for tie (difference < 0.01 between top-2): if so, apply tie-breaking
  3. Attempt coalition formation: if consensus_score > best individual score → use coalition
  4. Return ranked list (sorted, with coalitions marked)

### Tie-Breaking (for scouts)
1. Prefer scout with higher past_performance
2. Prefer scout with lower computational cost
3. Prefer scout with more evaluations in domain
4. Add small noise (±0.001), log for reproducibility

---

## Coalition Formation
Coalition is formed when two or more scouts have complementary specialties:
{
  "coalition_name":   "Thermal Analysis All-Stars",
  "members":          ["l4_scout_v1", "gnn_scout_v1", "wm_scout_v1"],
  "weights":          [0.40, 0.35, 0.25],
  "combined_report": {
    "risk_assessment":  "Medium-High",
    "graph_anomalies":  3,
    "world_context":    "Aerospace qualification required",
    "recommendation":   "Proceed with HALT testing"
  },
  "consensus_score": 0.86
}

Coalition replaces top individual scout if consensus_score >= top individual winning_score.

---

## HITL Scouting Combine UI
Presents top scouts to the General Manager (user):
  SOVEREIGN SCOUTING COMBINE
  TALENT: [file_name] ([domain])
  Overall Potential: [confidence]%

  TOP SCOUTS:
  🥇 [Scout 1] (Score: [score]) — [explanation]  [Select]
  🥈 [Scout 2] (Score: [score]) — [explanation]  [Select]
  🥉 [Scout 3] (Score: [score]) — [explanation]  [Select]
  🤝 COALITION: [name] (Score: [score]) — Members: [list]  [Select Coalition]

  [Accept Top Scout]  [Accept Coalition]  [Manual Override]

---

## BUS Events for Scout Layer
- talent:available      → broadcast to all scouts (sent after DATA_EXTRACTED)
- scout:registered      → scout announces capability (sent by ScoutRegistry)
- scout:evaluation      → scout submits report card (sent by each scout)
- orchestrator:ranking  → orchestrator publishes ranked scouts
- user:scout_selected   → user confirms scout selection (from HITL response)

---

## Extensibility: Adding a New Scout
class QuantumScout(ScoutAgent):
    def __init__(self):
        super().__init__(
            scout_id        = "quantum_scout_v1",
            specialty       = "Quantum Computing",
            expertise_areas = ["quantum_simulation", "optimization"],
            scoring_formula = {"relevance": 0.4, "confidence": 0.3, "past_performance": 0.2, "speed": 0.1}
        )

    def generate_report(self, talent_data: dict) -> dict:
        return {
            "quantum_speedup":    self.estimate_speedup(talent_data),
            "qubit_requirements": self.calculate_qubits(talent_data),
            "recommendation":     self.make_recommendation()
        }

# Register the new scout
ScoutRegistry.register("quantum_scout_v1", QuantumScout())

---

## Implementation Roadmap
| Phase   | Deliverable                          | Time Estimate |
|---------|--------------------------------------|---------------|
| Phase 1 | ScoutAgent base class + registry     | 2 days        |
| Phase 2 | L1–L5 scouts implementation          | 3 days        |
| Phase 3 | GNN, WM, CAUSAL scouts               | 2 days        |
| Phase 4 | Orchestrator + ranking system        | 2 days        |
| Phase 5 | HITL Scouting Combine UI             | 2 days        |
| Phase 6 | Coalition / all-star team formation  | 2 days        |
| Phase 7 | Farm system (axiom → scout pipeline) | 2 days        |
| Phase 8 | BUS event integration                | 1 day         |
| Total   |                                      | 16 days       |

---

## Error Codes
- E005: Scout evaluation timeout (retry 3 times)
- E009: Scout not found in ScoutRegistry
- T001: Test assertion failed

## Test Points
- SCOUT_001: All 8 scouts auto-register at startup
- SCOUT_002: GNNScout.evaluate() returns report_card with all required fields
- SCOUT_003: Winning_Score = (0.92×0.4)+(0.87×0.3)+(0.89×0.2)+((1-0.3)×0.1) ≈ 0.882
- SCOUT_004: Coalition consensus_score > best individual → coalition adopted
- SCOUT_005: Tie in winning_score resolved by past_performance
- SCOUT_006: New QuantumScout added via ScoutRegistry → included in next evaluate_all()
- SCOUT_007: HITL Scouting Combine UI renders top 3 scouts + coalition option
- SCOUT_008: scout:evaluation BUS event received by Orchestrator within 500ms of talent:available
