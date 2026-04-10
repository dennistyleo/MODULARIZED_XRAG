# spec/features/gnn.feature
# Gherkin BDD Specification: GNN Module — 3D Shape Analysis
# Version: 1.0.0
# Methodology: Cucumber / Given-When-Then

Feature: GNN Module - 3D Shape Analysis and Drift Detection

  Background:
    Given the module "gnn_module" is registered on SovereignBUS
    And the module "world_model_module" is registered on SovereignBUS
    And the module "causal_matrix_module" is registered on SovereignBUS
    And a valid DATA_EXTRACTED event has been emitted with trace_id "test_trace_001"

  # ─────────────────────────────────────────────────────────────
  # Scenario Group 1: Shape Formation
  # ─────────────────────────────────────────────────────────────

  Scenario: GNN_001 - Perfect 3D shape formed from 10 nodes
    Given a DATA_EXTRACTED payload with 10 nodes and 15 edges and inject_drift = false
    When the GNN module processes the data
    Then the DRIFT_DETECTED event is emitted on BUS
    And shape_formed should be true
    And drift_detected should be false
    And drift_location should be null
    And confidence should be >= 0.80

  Scenario: GNN_005 - Actual shape matches ideal shape causes no drift
    Given a DATA_EXTRACTED payload with nodes matching the ideal AEROSPACE shape
    When the GNN module processes the data
    Then drift_detected should be false
    And drift_magnitude should be null

  # ─────────────────────────────────────────────────────────────
  # Scenario Group 2: Drift Detection
  # ─────────────────────────────────────────────────────────────

  Scenario: GNN_002 - Drift detected at injected node N7
    Given a DATA_EXTRACTED payload with 10 nodes and inject_drift = true at node "N7" with magnitude 0.15
    When the GNN module processes the data
    Then the DRIFT_DETECTED event is emitted on BUS
    And drift_detected should be true
    And drift_location should be "N7"
    And drift_magnitude should be >= 0.15

  Scenario: Drift at N7 confirmed real by World Model
    Given the GNN module has detected drift at "N7"
    When the World Model receives the DRIFT_DETECTED event
    Then the SHAPE_COMPARED event is emitted on BUS
    And is_real_anomaly should be true
    And deviation_map should contain an entry for node "N7"

  Scenario: Drift at N7 flagged as noise by World Model
    Given the GNN module has detected drift at "N7" with magnitude 0.02
    And the ideal AEROSPACE shape also has a natural deviation at "N7"
    When the World Model receives the DRIFT_DETECTED event
    Then is_real_anomaly should be false

  # ─────────────────────────────────────────────────────────────
  # Scenario Group 3: Time Rotation
  # ─────────────────────────────────────────────────────────────

  Scenario: GNN_003 - Time rotation BACKWARD finds root cause at N3
    Given drift has been detected at "N7"
    When the GNN module processes with rotate_time = "BACKWARD"
    Then the root_cause should not be null
    And root_cause_chain should start at a node before "N7"
    And root_cause_chain should contain "N7" as the drift node

  Scenario: GNN_004 - Time rotation FORWARD predicts failure timeline
    Given drift has been detected at "N7"
    When the GNN module processes with rotate_time = "FORWARD"
    Then prediction should not be null
    And cycles_to_failure should be a positive integer

  # ─────────────────────────────────────────────────────────────
  # Scenario Group 4: Causal Matrix Integration
  # ─────────────────────────────────────────────────────────────

  Scenario: CAUSAL_001 - Causal matrix generated for 10-node system
    Given the World Model has confirmed drift is real
    When the Causal Matrix agent receives the SHAPE_COMPARED event
    Then the CAUSAL_MATRIX_READY event is emitted
    And causal_matrix should be a 10x10 array
    And all values in causal_matrix should be >= 0.0 and <= 1.0
    And each row should sum to <= 1.0

  Scenario: CAUSAL_002 - Root cause chain traced from N7 back to N1
    Given the Causal Matrix has been computed for a 10-node system with drift at N7
    When trace_root_cause("N7") is called
    Then root_cause_chain should begin at "N1"
    And root_cause_chain should end at "N7"

  Scenario: CAUSAL_003 - Probability of failure > 0 when drift present
    Given the causal matrix has been computed with drift_location = "N7"
    Then probability_of_failure should be > 0.0
    And probability_of_failure should be <= 1.0

  # ─────────────────────────────────────────────────────────────
  # Scenario Group 5: Error Handling
  # ─────────────────────────────────────────────────────────────

  Scenario: GNN drift detection failure falls back gracefully
    Given the GNN drift computation raises an internal error
    When the GNN module processes the data
    Then error code "E006" should be logged with the trace_id
    And drift_detected should be false (fallback)
    And the system should NOT crash

  Scenario: GNN output validates against gnn_output.json schema
    Given a valid DATA_EXTRACTED payload
    When the GNN module processes the data
    Then the DRIFT_DETECTED payload should validate against "spec/schemas/gnn_output.json"
