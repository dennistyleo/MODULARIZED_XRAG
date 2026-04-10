# Database Specification

Version: 1.0.0

## Engine
PostgreSQL >= 14
Connection pooling via SQLAlchemy (pool_size=10, max_overflow=5)
Environment variables:
  SOVEREIGN_DB_HOST
  SOVEREIGN_DB_USER
  SOVEREIGN_DB_PASSWORD
  SOVEREIGN_DB_NAME    (default: sovereign_db)
  SOVEREIGN_DB_PORT    (default: 5432)

## Schema

### Table: audit_sessions
| Column          | Type        | Constraints                                                |
|-----------------|-------------|------------------------------------------------------------|
| session_id      | UUID        | PRIMARY KEY                                                |
| session_label   | VARCHAR(128)| Format: SESSION_{timestamp}_{user}, e.g. SESSION_20260410_083000_leo |
| trace_id        | VARCHAR(64) | UNIQUE NOT NULL                                            |
| timestamp       | TIMESTAMPTZ | DEFAULT NOW()                                              |
| domain          | VARCHAR(32) | NOT NULL                                                   |
| ontology_path   | VARCHAR(256)|                                                            |
| file_name       | VARCHAR(256)|                                                            |
| tier            | SMALLINT    | CHECK (tier IN (1,2,3))                                    |
| tier_label      | VARCHAR(8)  | CHECK (tier_label IN ('TIER_1','TIER_2','TIER_3'))         |
| composite_score | NUMERIC(5,4)|                                                            |
| election_id     | VARCHAR(64) |                                                            |
| status          | VARCHAR(16) | DEFAULT 'IN_PROGRESS'                                      |

### Table: audit_nodes
| Column     | Type        | Constraints                              |
|------------|-------------|------------------------------------------|
| node_pk    | BIGSERIAL   | PRIMARY KEY                              |
| session_id | UUID        | FOREIGN KEY → audit_sessions.session_id  |
| node_id    | VARCHAR(16) | e.g. N7                                  |
| name       | TEXT        |                                          |
| value      | NUMERIC     |                                          |
| confidence | NUMERIC(4,3)|                                          |
| suspicious | BOOLEAN     | DEFAULT FALSE                            |
| corrected  | BOOLEAN     | DEFAULT FALSE                            |
| ontology_label | TEXT    |                                          |

### Table: axiom_registry
| Column           | Type        | Constraints      |
|------------------|-------------|------------------|
| axiom_id         | VARCHAR(64) | PRIMARY KEY      |
| domain           | VARCHAR(32) | NOT NULL         |
| pattern          | JSONB       | NOT NULL         |
| risk_label       | VARCHAR(64) | NOT NULL         |
| severity         | VARCHAR(16) |                  |
| confidence_floor | NUMERIC(4,3)| DEFAULT 0.60     |
| historical_success | NUMERIC(4,3) | DEFAULT 0.0   |
| computational_cost | NUMERIC(4,3) | DEFAULT 0.5   |
| sample_size      | INTEGER     | DEFAULT 0        |
| created_at       | TIMESTAMPTZ | DEFAULT NOW()    |
| active           | BOOLEAN     | DEFAULT TRUE     |

### Table: hitl_events
| Column           | Type        | Constraints                              |
|------------------|-------------|------------------------------------------|
| event_pk         | BIGSERIAL   | PRIMARY KEY                              |
| request_id       | VARCHAR(64) | UNIQUE NOT NULL (format: HITL_{random_4})|
| session_id       | UUID        | FOREIGN KEY → audit_sessions.session_id  |
| trace_id         | VARCHAR(64) |                                          |
| stage            | VARCHAR(8)  | UPLOAD | L1 | L2 | L3 | L4 | L5        |
| reason           | VARCHAR(32) |                                          |
| action           | VARCHAR(16) | CONFIRMED | CANCELLED | TIMEOUT          |
| operator_id      | VARCHAR(128)|                                          |
| corrected_nodes  | JSONB       |                                          |
| selected_pathways| JSONB       |                                          |
| timestamp        | TIMESTAMPTZ | DEFAULT NOW()                            |

### Table: scout_elections
| Column          | Type        | Constraints                              |
|-----------------|-------------|------------------------------------------|
| election_pk     | BIGSERIAL   | PRIMARY KEY                              |
| election_id     | VARCHAR(64) | UNIQUE NOT NULL (format: {date}_{seq})   |
| session_id      | UUID        | FOREIGN KEY → audit_sessions.session_id  |
| trace_id        | VARCHAR(64) |                                          |
| candidates      | JSONB       | array of {scout_id, scores, explanation} |
| winner_scout_id | VARCHAR(64) |                                          |
| winning_score   | NUMERIC(5,4)|                                          |
| coalition_used  | BOOLEAN     | DEFAULT FALSE                            |
| user_override   | VARCHAR(64) | scout_id chosen by user, or null         |
| timestamp       | TIMESTAMPTZ | DEFAULT NOW()                            |

## Session ID Format
Format:  SESSION_{timestamp}_{user}
Example: SESSION_20260410_083000_leo
Where:   timestamp = YYYYMMDD_HHMMSS, user = operator username (lowercase, alphanumeric)

## Indexes
- audit_sessions(trace_id)      — for fast lookup by trace
- audit_sessions(session_label) — for user-based lookup
- audit_nodes(session_id)       — for joining nodes to sessions
- axiom_registry(domain, active) — for fast axiom lookup during L3
- hitl_events(session_id)       — for HITL audit trail construction
- scout_elections(session_id)   — for election history lookup

## Migrations
Tool:    Alembic
Location: db/migrations/
Command: alembic upgrade head

## Retry Policy
E008 (DATABASE_CONNECTION_FAILED): retry up to 3 times, exponential backoff (1s, 2s, 4s)

## Test Points
- DB_001: audit_sessions row inserted on pipeline start, session_label = SESSION_{ts}_{user}
- DB_002: audit_nodes rows match extracted node count, ontology_label populated after L1
- DB_003: axiom_registry query with (domain, active=true) returns only active axioms
- DB_004: hitl_events row created on HITL_REQUEST emission with correct stage and reason
- DB_005: E008 logged with trace_id on connection failure
- DB_006: scout_elections row created after L3 General Election with all candidates
- DB_007: Index on trace_id returns audit_session in < 10ms
