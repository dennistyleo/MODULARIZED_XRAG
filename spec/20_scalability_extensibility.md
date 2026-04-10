# Scalability and Extensibility Specification

Version: 1.0.0

## Scalability Strategy

### Horizontal Scaling (Cloud Run)
- Min instances: 1 (always-warm)
- Max instances: 10 (auto-scaled by request count)
- Concurrency per instance: 80 requests
- Stateless design: all session state stored in PostgreSQL

### Database Scaling
- PostgreSQL read replicas for audit_sessions queries
- Connection pool: pool_size=10, max_overflow=5 per instance
- Table indexes:
  - audit_sessions(trace_id)
  - audit_nodes(session_id)
  - axiom_registry(domain, active)
  - hitl_events(session_id)

### BUS Scaling
Current:  In-process SovereignBUS (single instance)
Future:   Google Cloud Pub/Sub for multi-instance fan-out
Migration path:
  1. Abstract BUS interface: publish(event, payload), subscribe(event, cb)
  2. Swap in-process impl for Pub/Sub impl via CONFIG flag
  3. No module code changes required

### Load Targets
| Scenario               | Target         |
|------------------------|----------------|
| Concurrent users       | 80             |
| Uploads per minute     | 40             |
| Pipeline throughput    | 40 / minute    |
| DB write IOPS          | < 100          |

## Extensibility Patterns

### Adding a New Domain
1. Add domain constant to global_standards.md enum
2. Add constraint rules to stage_2 pruning ruleset (JSON file)
3. Add ideal shape to world_model shapes library
4. Register domain-specific axioms via /api/axioms/register
5. No changes to pipeline stage code required

### Adding a New Pipeline Stage
1. Create module following 02_code_structure.md template
2. Subscribe to upstream BUS event
3. Emit new downstream BUS event
4. Register with ModuleRegistry at startup
5. Add tab to frontend via self-registration pattern (14_frontend_tabs.md)

### Adding a New Axiom
POST /api/axioms/register
{
  "axiom_id": "THERMAL_B_002",
  "domain": "AEROSPACE",
  "pattern": ["SENSOR", "THRESHOLD", "ALERT"],
  "risk_label": "THERMAL_OVERRUN",
  "severity": "CRITICAL",
  "confidence_floor": 0.75
}
Axiom is immediately active in stage_3 matching (hot-reload).

### Feature Flags
Stored in environment variable: SOVEREIGN_FEATURES
Format: comma-separated list
Example: SOVEREIGN_FEATURES=pubsub_bus,cloud_storage,oauth2

## Anti-Patterns to Avoid
- ❌ Hardcoded domain names in pipeline stage code
- ❌ Direct module-to-module function calls
- ❌ Shared mutable global state
- ❌ Blocking I/O in BUS event handlers

## Test Points
- SCALE_001: 80 concurrent pipeline requests complete without 5xx
- SCALE_002: New axiom registered via API is matched in next pipeline run
- SCALE_003: Adding a new domain constant does not break existing domains
- SCALE_004: SOVEREIGN_FEATURES flag enables pubsub_bus without code changes
- SCALE_005: Database index on trace_id returns audit_session in < 10 ms
