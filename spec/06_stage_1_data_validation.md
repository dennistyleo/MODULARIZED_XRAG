# Stage 1: Ontological Classification Specification

Version: 1.0.0
Stage Name: L1 — ONTOLOGICAL_SCOPING
BUS Event In:  DATA_EXTRACTED
BUS Event Out: ONTOLOGY_CLASSIFIED

## Purpose
Classify extracted RAG output into ontological categories using domain-specific taxonomy.
Produce a hierarchical classification (domain > sub_domain > category) and validate
all nodes and edges against ontology schemas before downstream processing.

## L1 Agent Role
The L1 agent is the Ontological Scout:
  "I classify this data and determine what TYPE of thing it is."
  "I pass this classification to L2 so it knows what hypotheses to generate."

## Input
Receives payload from DATA_EXTRACTED event:
- domain:       string (CONTRACT | FINANCIAL | TECHNICAL | AEROSPACE | GENERAL)
- nodes:        array of {id, name, value, confidence, editable, suspicious}
- edges:        array of {source, target, causal_strength}
- assessment:   {conf, tier, reason}
- fingerprint:  data fingerprint object
- trace_id:     string

## Ontology Hierarchy Output
Classified nodes receive hierarchical labels, for example:
  Aerospace Materials > Thermal Cycling > Reliability
  Financial > Revenue Recognition > IFRS 15
  Contract > Obligation > Penalty Clause

Format per node:
  ontology_label: "{domain} > {sub_domain} > {category}"

## Validation Rules
- nodes array must have at least 2 elements
- each node.id must match pattern: N[0-9]+
- each node.confidence must be in range [0.0, 1.0]
- each edge.source and edge.target must reference existing node IDs
- each edge.causal_strength must be in range [0.0, 1.0]
- assessment.conf must be in range [0.0, 1.0]
- assessment.tier must be 1, 2, or 3
- domain must be one of the allowed enum values

## HITL Trigger Conditions (L1 stage)
1. Multiple domain classifications possible → HITL_REQUEST (reason: DOMAIN_AMBIGUITY)
2. assessment.tier == 3 (REFUSE)         → HITL_REQUEST (reason: TIER_3)
3. assessment.conf < 0.85 (overall RAG)  → HITL_REQUEST (reason: LOW_CONFIDENCE)
4. any node.confidence < 0.60            → HITL_REQUEST (reason: NODE_LOW_CONFIDENCE)

## Output (ONTOLOGY_CLASSIFIED payload)
- validated:          boolean
- domain:             string
- ontology_path:      string (e.g., "Aerospace Materials > Thermal Cycling > Reliability")
- classified_nodes:   array of {id, name, value, confidence, category, ontology_label}
- fingerprint:        data fingerprint (passed through from RAG)
- violated_rules:     array of {rule_id, node_id, description}
- trace_id:           string

## Error Codes
- E004: Schema validation failed (no retry)
- E009: BUS routing failed (retry 3 times)
- T001: Test assertion failed (test harness only)

## Test Points
- STAGE1_001: Valid AEROSPACE domain with 5 nodes → classified_nodes all have ontology_label
- STAGE1_002: Node with confidence < 0.60 → HITL_REQUEST emitted before classification
- STAGE1_003: Unknown domain value → E004, validated=false
- STAGE1_004: Edge referencing non-existent node ID → violated_rules entry + validated=false
- STAGE1_005: assessment.tier == 3 → HITL_REQUEST emitted, reason=TIER_3
- STAGE1_006: Multiple domain hints in fingerprint → HITL_REQUEST reason=DOMAIN_AMBIGUITY
