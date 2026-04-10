# Design Methodology Specification

Version: 1.0.0

## Core Philosophies (Five)
1. Deterministic First   — Same input must always produce the same output
2. Trust by Evidence     — Every risk score is traceable to source data
3. Human in the Loop     — Operators can correct AI decisions before they propagate
4. Graceful Resilience   — Partial data failures produce warnings, not crashes
5. Open Extensibility    — New domains, axioms, scouts, and stages require no core code changes

---

## Architecture Pattern: Event-Driven Pipeline

Upload → RAG → [L1 → L2 → L3 → L4 → L5] → Report
                   ↑         ↑          ↑
             HITL Modal  GNN Module  HITL Re-trigger
                        World Model
                        Causal Matrix

All communication flows through SovereignBUS.
No module knows about any other module directly.
Scouts compete in parallel and are ranked by Axiom Democracy formula.

---

## Axiom Democracy (Competitive Axiom Evaluation)

### Core Metaphor: The Election Campaign
| Phase                  | Metaphor                        | Technical Implementation                              |
|------------------------|---------------------------------|-------------------------------------------------------|
| 1. Candidate Registration | Axioms declare their expertise | Axioms have metadata: domains, data types, success history |
| 2. Issue Analysis      | RAG extracts data features      | Data fingerprinting: stationarity, continuity, SNR, domain cues |
| 3. Campaigning         | Axioms "argue" for selection    | Each axiom evaluates data, produces confidence + explanation |
| 4. Primary Election    | Top candidates advance          | Filter relevance > 0.60, top 5 proceed               |
| 5. General Election    | Parallel evaluation             | Run competing evaluations simultaneously              |
| 6. Coalition Building  | Axioms combine forces           | Ensemble: weighted voting, stacking                   |
| 7. Winner Declaration  | Best axiom selected             | User can review and override                          |
| 8. Audit Trail         | Full history logged             | Complete trace of competition and winner selection    |

### Axiom Democracy Scoring Formula
Winning_Score = (Relevance × 0.4) + (Confidence × 0.3) + (Historical_Success × 0.2) + ((1 - Cost) × 0.1)

Where:
- Relevance:          How well data matches axiom's declared domains (0–1)
- Confidence:         Axiom's internal confidence in its prediction (0–1)
- Historical_Success: Past accuracy on similar domain data (0–1)
- Cost:               Relative computational cost (0–1, lower is better)

### Axiom Metadata (Campaign Platform)
Each axiom declares its platform:
{
  "axiom_id":           "thermal_equation_v1",
  "domains":            ["aerospace", "automotive", "electronics"],
  "data_types":         ["time_series", "temperature_cycles", "thermal_shock"],
  "confidence_history": [{"domain": "aerospace", "success_rate": 0.94, "sample_size": 156}],
  "computational_cost": 0.3,
  "preferred_allies":   ["fourier_transform", "arrhenius_model"],
  "rivalries":          ["simple_linear_regression"]
}

### Axiom Competition Strategies
| Strategy              | Behavior                         | Example                                   |
|-----------------------|----------------------------------|-------------------------------------------|
| Specialization        | Narrow domain, high relevance     | "I only do aerospace thermal"             |
| Generalization        | Wide domain, moderate relevance   | "I do all signal processing"              |
| Low-cost campaigning  | Emphasize efficiency              | "I'm fast and cheap"                      |
| Coalition building    | Ally with complementary axioms    | "Team up with Arrhenius for thermal"      |
| Negative campaigning  | Point out rival weaknesses        | "Fourier cannot handle non-stationary data" |

---

## Sovereign Multi-Agent Scouting Ecosystem

### Core Metaphor: Baseball Talent Scouting
| Role                        | System Component     | Responsibility                                        |
|-----------------------------|----------------------|-------------------------------------------------------|
| Talent (Data)               | Extracted data (RAG) | The raw potential to be evaluated                     |
| Scouts (Agents)             | L1–L5, GNN, WM, CAUSAL | Each evaluates talent from their specialty           |
| Scouting Director (Orchestrator) | System coordinator | Manages competition, collects reports, decides roster |
| General Manager (User)      | Human user           | Makes final decisions, signs off on recommendations   |
| Front Office (HITL)         | HITL modal           | Presents scouting reports, allows user override       |

### Scout Ranking Board (Draft Board)
| Rank | Scout         | Relevance | Confidence | Past Perf | Speed | Total |
|------|---------------|-----------|------------|-----------|-------|-------|
| 1    | GNN Scout     | 0.92      | 0.87       | 0.89      | 0.85  | 0.88  |
| 2    | L4 Scout      | 0.89      | 0.91       | 0.82      | 0.70  | 0.85  |
| 3    | WM Scout      | 0.85      | 0.88       | 0.85      | 0.75  | 0.84  |
| 4    | L2 Scout      | 0.82      | 0.84       | 0.88      | 0.80  | 0.83  |
| 5    | L1 Scout      | 0.88      | 0.79       | 0.83      | 0.90  | 0.82  |
| 6    | CAUSAL Scout  | 0.80      | 0.86       | 0.80      | 0.65  | 0.79  |
| 7    | L3 Scout      | 0.75      | 0.82       | 0.85      | 0.85  | 0.78  |
| 8    | L5 Scout      | 0.70      | 0.80       | 0.90      | 0.60  | 0.75  |

### The Farm System (Axiom Repository)
Axioms are the "farm system" that feeds into scout agents:
  AXIOM REPOSITORY → [each scout uses axioms as analytical tools] → SCOUT EVALUATIONS

### Agent Collaboration: The Goldmine
Each agent is designed to be incomplete by itself. They must collaborate.
"The whole is greater than the sum of its parts." — The Jade Design Principle

| Agent        | Gives to Others                                 | Receives from Others            |
|--------------|-------------------------------------------------|---------------------------------|
| RAG          | Raw data, initial confidence, data fingerprint   | Nothing (source)                |
| GNN          | 3D shape, drift detection, time-rotated RCA      | Ideal shape from World Model    |
| World Model  | Ideal 3D shape, is_real_anomaly confirmation     | Drift location from GNN         |
| Causal Matrix| Causal weights, root cause chain                | Drift confirmation from WM      |
| L1           | Ontological classification, ontology_path        | None                            |
| L2           | Candidate pathways + Winning_Scores             | L1 classification               |
| L3           | Admissible pathways + election_id               | L2 candidates                   |
| L4           | Per-pathway risks + composite_score             | L3 pathways                     |
| L5           | Final report + HITL audit trail                 | All of the above                |

### The Jade Design Principle
"The whole is greater than the sum of its parts."
Each agent is designed to be incomplete by itself. They must collaborate. They must share.
They must enrich each other's data.
The measure of a good agent is not how well it competes, but how much it contributes
to the collective intelligence.

---

## Trace-Driven Auditability
Every operation carries a trace_id from upload to report.
The trace_id links: audit_sessions → audit_nodes → hitl_events → scout_elections → BUS messages → log lines.
This enables full post-hoc reconstruction of every audit decision.

---

## Risk Tier Model
| Tier | Label  | composite_score | Action              |
|------|--------|-----------------|---------------------|
| 1    | TIER_1 | < 0.40          | Auto-approve        |
| 2    | TIER_2 | 0.40 – 0.69     | Recommend review    |
| 3    | TIER_3 | >= 0.70         | Block + HITL modal  |

---

## Module Independence Principle
Each module must function correctly given ONLY its BUS input payload.
It must NOT read files, databases, or other modules directly.
Shared state is cached by the BUS router: bus.get_cached(event_name).

---

## Off-the-Shelf Methodology References
| Methodology            | Source                          | Application in Sovereign Matrix          |
|------------------------|---------------------------------|------------------------------------------|
| DDD (Domain-Driven Design) | Eric Evans                  | Module boundaries, bounded contexts       |
| Event Storming         | Alberto Brandolini              | BUS event naming, pipeline modeling       |
| C4 Model               | Simon Brown                     | Architecture diagrams (context/containers)|
| BDD / Gherkin          | Cucumber / Given-When-Then      | Feature specs (spec/features/*.feature)  |
| OpenAPI 3.0            | OpenAPI Initiative              | API contract: spec/schemas/openapi.yaml  |
| JSON Schema            | json-schema.org                 | Data validation: spec/schemas/*.json     |

---

## AI-Ready Spec Format
The spec directory follows a combined methodology:
  spec/
    ├── *.md               — Human-readable specifications (this format)
    ├── schemas/           — JSON Schema (machine-readable validation)
    ├── features/          — Gherkin BDD (executable behavior specs)
    └── test_points/       — Deterministic YAML test points

Principle: Every gray area is eliminated by design, not discovered by testing.

---

## Development Workflow
1. Write spec (this directory) → review → approve
2. Write test (test-generator skill) → run red
3. Write module (rag/gnn/stage skill) → run green
4. Update spec if implementation diverges
5. Merge only when coverage thresholds met

---

## Decision Log
| Decision                              | Rationale                                               |
|---------------------------------------|---------------------------------------------------------|
| In-process BUS (not Pub/Sub)          | Simplicity for single-instance MVP                      |
| gemini-3-flash-preview                | Best latency/accuracy tradeoff for extraction           |
| PostgreSQL over Firestore             | ACID compliance for audit trail integrity               |
| Self-registering frontend tabs        | Eliminates hardcoded wiring as tabs are added           |
| 100vh locked layout                   | Prevents scroll-occlusion of audit dashboard            |
| Composite risk scoring (4 terms)      | Integrates RAG, causal, drift, shape signals            |
| Axiom Democracy formula               | Balances relevance, confidence, history, efficiency     |
| Scout Registry separate from Module   | Scouts compete; modules execute — different lifecycle   |
| HITL at every stage (not just upload) | Decisions can be ambiguous at any pipeline stage        |
| Multi-report for multi-pathway        | User may want multiple valid analyses simultaneously    |

---

## Versioning Policy
- Spec version:   Semantic (MAJOR.MINOR.PATCH)
- Module version: Matches spec MAJOR.MINOR
- API version:    URI-prefixed /api/v1/...
- Breaking spec changes require new MAJOR version and migration plan

## Test Points
- DESIGN_001: New module added without modifying any existing module code
- DESIGN_002: trace_id present in every BUS message payload
- DESIGN_003: Re-running same input produces identical tier classification
- DESIGN_004: /api/v1/ prefix returns same results as /api/ (version aliasing)
- DESIGN_005: Spec file version matches module docstring version on every module
- DESIGN_006: Axiom Democracy formula produces correct Winning_Score for known inputs
- DESIGN_007: Coalitions produce combined output when consensus_score > best individual
