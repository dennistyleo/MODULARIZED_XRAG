# Quality Attributes Specification

Version: 1.0.0

## 1. Performance
| Metric                          | Target        |
|---------------------------------|---------------|
| End-to-end pipeline latency     | < 10 seconds  |
| Gemini extraction latency       | < 5 seconds   |
| Stage 1–5 processing latency    | < 3 seconds   |
| Report generation latency       | < 2 seconds   |
| UI first paint (localhost)      | < 1 second    |
| D3 visualization redraw         | <= 60 fps     |
| API response time (/api/health) | < 200 ms      |

## 2. Reliability
- System uptime target:          99.5% (monthly)
- Pipeline success rate:         >= 98% of valid uploads
- No 5xx errors under normal load (< 10 concurrent users)
- Graceful degradation:          missing module data logs warning, does not crash

## 3. Accuracy
- RAG extraction confidence:     >= 0.80 for well-formed documents
- GNN drift detection precision: >= 0.90 on synthetic drift fixtures
- HITL correction propagation:   100% (corrected nodes must feed back into L1→L5)

## 4. Security
- All API endpoints require a valid session token (future: OAuth2)
- SOVEREIGN_GEMINI_API_KEY never logged or returned in any API response
- Uploaded files scanned for MIME type mismatch before processing
- PostgreSQL credentials only in environment variables (never in source)
- Cloud Run HTTPS enforced; HTTP traffic auto-redirected

## 5. Maintainability
- Max module size:    Python 500 lines, JavaScript 400 lines
- Test coverage:      >= 90% line, >= 85% branch, 100% function
- All public functions have docstrings and type hints
- Every error logged with error_code + trace_id
- Spec files kept in sync with implementation (updated on every PR)

## 6. Observability
- Structured JSON logs (Google Cloud Logging format)
- Every log line includes: timestamp, trace_id, module, level, error_code (if any)
- Cloud Run request logs: method, path, latency, status
- BUS event throughput metric emitted every 60 seconds

## 7. Usability
- HITL modal accessible via keyboard (Tab, Enter, Esc)
- Status badge updated in real-time via aria-live="polite"
- All error states display a human-readable message in the UI
- Upload supports drag-and-drop and file picker

## Test Points
- QA_001: End-to-end pipeline completes in < 10 seconds with test fixture
- QA_002: GEMINI_API_KEY does not appear in any log output
- QA_003: Uploading a non-PDF/CSV/JSON file returns HTTP 400
- QA_004: System returns 200 on /api/health with at least READY status
- QA_005: All module docstrings verified by pydoc-lint in CI
