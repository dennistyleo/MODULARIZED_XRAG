# spec/features/rag.feature
# Gherkin BDD Specification: RAG Module — Document Extraction
# Version: 1.0.0
# Methodology: Cucumber / Given-When-Then

Feature: RAG Module - Document Extraction

  Background:
    Given the Gemini API model "gemini-3-flash-preview" is available
    And the API key is configured as SOVEREIGN_GEMINI_API_KEY
    And the module "rag_module" is registered on SovereignBUS

  # ─────────────────────────────────────────────────────────────
  # Scenario Group 1: Successful Extraction
  # ─────────────────────────────────────────────────────────────

  Scenario: RAG_001 - Extract contract data from PDF
    When I upload a file "fixtures/contract_pdf_001.pdf"
    Then the DATA_EXTRACTED event is emitted on BUS
    And the response domain should be "CONTRACT"
    And the nodes should include node IDs matching pattern "N[0-9]+"
    And each node should have confidence >= 0.85
    And the assessment tier should be 1
    And the data fingerprint field "domain_hints" should contain "contract"

  Scenario: RAG_002 - Extract financial data from CSV
    When I upload a file "fixtures/financial_csv_001.csv"
    Then the DATA_EXTRACTED event is emitted on BUS
    And the response domain should be "FINANCIAL"
    And a node with name "revenue" should be present
    And the assessment conf should be > 0.80

  Scenario: RAG_003 - Extract contract data from plain text
    When I send text "Contract ID: 12345, Amount: $25000, Date: 2024-01-15"
    Then the DATA_EXTRACTED event is emitted on BUS
    And the response domain should be "CONTRACT"
    And the nodes array should contain exactly 3 items
    And the first node id should be "N1"

  Scenario: RAG_007 - Data fingerprint produced alongside extraction
    When I upload a file "fixtures/aerospace_pdf_001.pdf"
    Then the DATA_EXTRACTED event is emitted on BUS
    And the fingerprint field "stationarity" should be >= 0.80
    And the fingerprint field "domain_hints" should not be empty

  # ─────────────────────────────────────────────────────────────
  # Scenario Group 2: Confidence Gate and HITL
  # ─────────────────────────────────────────────────────────────

  Scenario: HITL triggered when overall RAG confidence is below 0.85
    Given a document where overall extraction confidence will be 0.72
    When I upload the document
    Then the HITL_REQUEST event is emitted on BUS
    And the HITL request reason should be "LOW_CONFIDENCE"
    And the DATA_EXTRACTED event should still be emitted with conf = 0.72

  Scenario: Auto-pass when overall confidence >= 0.85
    Given a document where overall extraction confidence will be 0.92
    When I upload the document
    Then the HITL_REQUEST event should NOT be emitted
    And the ONTOLOGY_CLASSIFIED event is emitted within 10 seconds

  # ─────────────────────────────────────────────────────────────
  # Scenario Group 3: Error Handling
  # ─────────────────────────────────────────────────────────────

  Scenario: RAG_004 - Corrupted PDF returns E004
    When I upload a file "fixtures/corrupted_pdf_001.pdf"
    Then the response should include error code "E004"
    And the system should NOT crash
    And error code "E004" should be logged with the trace_id

  Scenario: RAG_005 - Gemini API timeout returns E002 and uses fallback
    Given the Gemini API will respond after 35 seconds
    When I upload a file "fixtures/contract_pdf_001.pdf"
    Then the response should be received within 30 seconds
    And the error code "E002" should be logged
    And the system should retry up to 3 times before fallback

  Scenario: RAG_006 - Strict mode rejects file when confidence below threshold
    Given a RAG command with confidence_threshold = 0.95 and on_low_confidence = "reject"
    When I upload a file where any field confidence is 0.80
    Then the file should be rejected immediately
    And no DATA_EXTRACTED event should be emitted
    And the response should include error code "E004"

  # ─────────────────────────────────────────────────────────────
  # Scenario Group 4: Schema Validation
  # ─────────────────────────────────────────────────────────────

  Scenario: RAG output matches rag_output.json schema
    When I upload a file "fixtures/contract_pdf_001.pdf"
    Then the DATA_EXTRACTED payload should validate against "spec/schemas/rag_output.json"

  Scenario: RAG input with missing file_path and missing text returns error
    When I send a RAG request with neither file_path nor text
    Then the system should return error code "E004"
    And the response should include message "No input provided"
