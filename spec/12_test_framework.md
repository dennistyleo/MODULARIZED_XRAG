# Test Framework Specification

Version: 1.0.0

## Framework
- Runner:    pytest >= 7.0
- Async:     pytest-asyncio
- Coverage:  pytest-cov
- Mocking:   unittest.mock

## Coverage Requirements
- Line coverage:     >= 90%
- Branch coverage:   >= 85%
- Function coverage: 100%

## Directory Structure
tests/
  conftest.py              # shared fixtures and mock BUS
  fixtures/
    contract.pdf
    financial.csv
    aerospace.json
  test_bus.py
  test_rag_module.py
  test_gnn_module.py
  test_world_model.py
  test_causal_matrix.py
  test_stage_1.py
  test_stage_2.py
  test_stage_3.py
  test_stage_4.py
  test_stage_5.py
  test_hitl_modal.py
  test_module_registry.py
  test_api_endpoints.py
  test_database.py

## Test Naming Convention
Format: test_{module}_{number}_{description}
Examples:
  test_rag_001_pdf_extraction
  test_stage1_002_low_confidence_hitl
  test_gnn_003_time_rotation_backward

## Required Tests per Module
- test_001_valid_input
- test_002_invalid_input
- test_003_error_handling
- test_004_timeout
- test_005_schema_validation

## Mock BUS (conftest.py)
class MockBUS:
  Tracks all emitted events and payloads.
  Provides .last_event(name) → payload helper.
  Supports .simulate(event_name, payload) to inject upstream events.

## Running Tests
pytest tests/ --cov=modules --cov-report=term-missing -v

## CI Gate
Tests must pass before any deployment to Cloud Run.
Coverage below threshold blocks the pipeline.

## Test Points (framework-level)
- TEST_FW_001: conftest.py MockBUS captures all emitted events
- TEST_FW_002: Fixture files exist at expected paths
- TEST_FW_003: pytest --cov reports >= 90% line coverage
- TEST_FW_004: No test imports from modules using direct calls (BUS only)
- TEST_FW_005: All test IDs are unique across the test suite

## End-to-End User Journey Tests

### Test E2E_001: Complete Upload to Report Flow
Simulates a real user:
1. Opens browser, sees landing page
2. Clicks "INITIALIZE ENGINE"
3. Uploads a file (PDF/CSV/JSON)
4. Reviews HITL modal, edits suspicious field
5. Confirms, waits for L1-L5 processing
6. Views report in CORE tab
7. Switches to GNN tab, views 3D visualization
8. Switches to WORLD MODEL tab, views comparison
9. Switches to CAUSAL MATRIX tab, views matrix
10. Generates audit report, downloads PDF
11. Verifies report contains all expected sections

**Pass Criteria:** All steps complete without JavaScript errors, all visualizations render, report contains data.

### Test E2E_002: HITL Intervention Flow
1. Upload file with low confidence data (confidence < 60%)
2. HITL modal opens automatically
3. User edits suspicious field
4. Impact preview updates in real-time
5. User confirms
6. Verify corrected data flows through pipeline
7. Final report includes user corrections in audit trail

**Pass Criteria:** HITL modal opens, edits save, audit trail contains corrections.

### Test E2E_003: Multi-Pathway Selection (L3)
1. Upload file that triggers multiple valid pathways
2. HITL modal shows pathway selection UI
3. User selects 2 pathways
4. User clicks "Generate Selected"
5. Verify 2 separate reports are generated
6. Each report has unique report_id

**Pass Criteria:** Multi-pathway UI renders, 2 reports generated, both contain correct data.

## Tab-Specific Tests

### Tab: CORE
- Test TAB_CORE_001: Axiom tree renders with nodes
- Test TAB_CORE_002: Clicking node expands/collapses
- Test TAB_CORE_003: Confidence scores display correctly
- Test TAB_CORE_004: Tab remains responsive after data update

### Tab: GNN
- Test TAB_GNN_001: 3D canvas renders (Three.js)
- Test TAB_GNN_002: Nodes appear as spheres at correct coordinates
- Test TAB_GNN_003: Edges appear as lines between nodes
- Test TAB_GNN_004: Drift nodes are red, normal nodes are green
- Test TAB_GNN_005: Camera controls (rotate, pan, zoom) work
- Test TAB_GNN_006: Time rotation buttons trigger RCA/prediction
- Test TAB_GNN_007: Canvas resizes when window resizes

### Tab: WORLD MODEL
- Test TAB_WM_001: Ideal shape renders
- Test TAB_WM_002: Comparison view shows actual vs ideal
- Test TAB_WM_003: Deviation heatmap renders with correct colors
- Test TAB_WM_004: Recommendation panel displays text

### Tab: CAUSAL MATRIX
- Test TAB_CM_001: Causal matrix heatmap renders (N×N grid)
- Test TAB_CM_002: Root cause chain renders as horizontal flow
- Test TAB_CM_003: Prediction card shows cycles_to_failure
- Test TAB_CM_004: Recommendation panel displays actionable text

## Modal Tests

### HITL Modal
- Test MODAL_HITL_001: Opens when confidence < 85%
- Test MODAL_HITL_002: Closes with Cancel button
- Test MODAL_HITL_003: Edit panel opens on row click
- Test MODAL_HITL_004: Accept Suggestion updates value
- Test MODAL_HITL_005: Impact preview updates in real-time
- Test MODAL_HITL_006: Confirm button saves corrections
- Test MODAL_HITL_007: Keyboard navigation works (Tab, Enter, Esc)
- Test MODAL_HITL_008: Multi-pathway checkbox renders (L3 only)
- Test MODAL_HITL_009: 300-second timeout auto-submits

### Audit Report Modal
- Test MODAL_AUDIT_001: Opens when "GENERATE AUDIT REPORT" clicked
- Test MODAL_AUDIT_002: Report contains executive summary
- Test MODAL_AUDIT_003: Report contains data table
- Test MODAL_AUDIT_004: Report contains causal chain
- Test MODAL_AUDIT_005: PDF download works
- Test MODAL_AUDIT_006: Print preview shows A4 format

## User-Friendliness Tests (Beyond Pass/Fail)

### UX-001: First-Time User Completes Audit Without Instructions
- No tooltips or guidance shown to user
- User must complete full audit flow
- Measure: time to completion, number of clicks, error rate
- Pass: User completes within 5 minutes without external help

### UX-002: Error Message Clarity
- Trigger each error condition (file too large, wrong format, timeout)
- Verify error message is in plain English (no technical jargon)
- Verify message explains what went wrong and how to fix
- Pass: User understands the error without technical knowledge

### UX-003: Visual Feedback Responsiveness
- Measure time from click to visual response
- All interactions < 100ms
- Loading indicators appear for operations > 500ms
- Pass: No perceived lag, loading spinners appear

### UX-004: Mobile/Responsive Layout
- Test at viewport widths: 1920px, 1280px, 768px, 375px
- All tabs accessible, no horizontal overflow
- HITL modal scrolls on small screens
- Pass: No layout breaks at any breakpoint

### UX-005: Accessibility Compliance
- Keyboard navigation: all interactive elements reachable
- Screen reader: aria labels present, modal has role="dialog"
- Color contrast: text meets WCAG AA (4.5:1)
- Pass: Lighthouse accessibility score >= 90

## Performance Tests

### PERF-001: Upload to Report Latency
- Upload 1MB file → measure time to report ready
- Pass: < 10 seconds (including Gemini API call)

### PERF-002: GNN 3D Render Time
- 100 nodes, 200 edges → measure render time
- Pass: < 500ms

### PERF-003: Concurrent Users
- Simulate 10 concurrent uploads
- Pass: No request drops, average latency < 15 seconds

### PERF-004: Memory Leak Check
- Run 10 upload-report cycles
- Pass: Memory usage does not increase monotonically

## Test Execution Commands

```bash
# Run all tests (unit + e2e + ux + performance)
pytest tests/ -v --cov=modules --cov-report=term-missing

# Run only E2E user journey tests
pytest tests/e2e/ -v -m "e2e"

# Run only UX tests
pytest tests/ux/ -v -m "ux"

# Run performance tests
pytest tests/performance/ -v -m "performance"
```

## Test ID Registry

| Test ID | Category | Area | HITL Involved |
|---------|----------|------|---------------|
| E2E_001 | End-to-End | Full pipeline | YES |
| E2E_002 | End-to-End | HITL intervention | YES |
| E2E_003 | End-to-End | Multi-pathway L3 | YES |
| TAB_CORE_001–004 | Tab | CORE tab UI | NO |
| TAB_GNN_001–007 | Tab | GNN 3D tab | NO |
| TAB_WM_001–004 | Tab | World Model tab | NO |
| TAB_CM_001–004 | Tab | Causal Matrix tab | NO |
| MODAL_HITL_001–009 | Modal | HITL modal | YES |
| MODAL_AUDIT_001–006 | Modal | Audit report modal | NO |
| UX-001–005 | UX | User experience | PARTIAL |
| PERF-001–004 | Performance | Latency & stability | NO |
