# RAG Module Specification

Version: 1.0.0
Stage: Upload / Pre-pipeline
BUS Event Out: DATA_EXTRACTED

## Purpose
Extract structured data from uploaded files using Gemini 3 Flash.
RAG must not guess — it must be instructed by explicit command input.

## Model
- Name:    gemini-3-flash-preview  (exact string, no abbreviations)
- Timeout: 30 seconds per request
- Retry:   E002 → 3 times, E003 → 2 times

## RAG Command Input (optional, overrides defaults)
{
  "domain_command":     "Analyze this as a financial contract",
  "extract_command":    {"fields": ["party_names", "effective_date", "amount"], "strict": true, "fallback": "reject"},
  "evaluation_command": "Apply: IFRS 15 revenue recognition rules",
  "output_command":     "Return JSON with confidence scores per field",
  "confidence_threshold": 0.95,
  "on_low_confidence":  "reject"
}

If confidence_threshold is set and any field confidence falls below it:
  Strict mode: reject the file immediately (no HITL, no retry).

## Input
- file_path: string (pattern: .*\.(pdf|csv|json)$)
- text:      string (minLength: 1, maxLength: 10000)
- command:   RAG Command object (optional)

Exactly one of file_path or text must be provided.

## Data Fingerprint Output
RAG generates a data fingerprint alongside structured extraction:
{
  "file_type":       "test_report | contract | financial | general",
  "domain_hints":    ["aerospace", "thermal", "reliability"],
  "data_types":      ["time_series", "temperature", "cycles_to_failure"],
  "statistical_properties": {
    "stationarity": 0.95,
    "continuity":   0.88,
    "snr":          0.76,
    "seasonality":  0.12
  },
  "extracted_fields": {}
}

The fingerprint is forwarded to axiom scouts for self-evaluation.

## Structured Output (DATA_EXTRACTED payload)
- domain:     CONTRACT | FINANCIAL | TECHNICAL | AEROSPACE | GENERAL
- nodes:      array of {id (N1..Nn), name, value, confidence, editable, suspicious}
- edges:      array of {source, target, causal_strength}
- assessment: {conf (0–1), tier (1|2|3), reason}
- fingerprint: data fingerprint object
- trace_id:   string

## HITL Gate (on overall confidence)
- RAG overall confidence >= 0.85 → AUTO-PASS to L1
- RAG overall confidence < 0.85  → emit HITL_REQUEST (reason: LOW_CONFIDENCE)
- assessment.tier == 3           → emit HITL_REQUEST (reason: TIER_3)

## Error Codes
- E001: File not found           (no retry)
- E002: Gemini API timeout       (retry 3 times, 30s timeout per attempt)
- E003: Invalid JSON response    (retry 2 times)
- E004: Schema validation failed (no retry)
- T001: Test assertion failed    (test harness only)

## Test Points
- RAG_001: PDF contract extraction → domain=CONTRACT, nodes>=3, tier=1
- RAG_002: CSV financial extraction → domain=FINANCIAL, revenue node present
- RAG_003: Text contract extraction → domain=CONTRACT, nodes=3
- RAG_004: Corrupted PDF → E004 returned, no crash
- RAG_005: Gemini timeout (35s) → response received in < 30s via fallback, E002 logged
- RAG_006: Strict mode with confidence_threshold=0.95 → file rejected if any field < 0.95
- RAG_007: Data fingerprint stationarity >= 0.80 on time-series fixture
