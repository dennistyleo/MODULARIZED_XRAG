# External Resources Specification

Version: 1.0.0

## 1. Gemini API
Provider:  Google AI (generativelanguage.googleapis.com)
Model:     gemini-3-flash-preview
Auth:      API key via SOVEREIGN_GEMINI_API_KEY
Timeout:   30 seconds (per request)
Retry:     3 times for E002 (GEMINI_API_TIMEOUT)
           2 times for E003 (INVALID_JSON_RESPONSE)
Rate limit: 60 requests per minute (per key)

Endpoints used:
  POST /v1beta/models/gemini-3-flash-preview:generateContent

Request headers:
  Content-Type: application/json
  x-goog-api-key: {SOVEREIGN_GEMINI_API_KEY}

## 2. Google Cloud Storage (optional)
Purpose:   Store uploaded files and generated reports
Bucket:    gs://sovereign-matrix-{PROJECT_ID}
Auth:      Service account with roles/storage.objectAdmin
Max file size: 50 MB
Retention:    30 days (lifecycle policy)

## 3. Google Cloud Pub/Sub (optional future)
Purpose:   Async BUS backbone for multi-instance deployments
Topic:     sovereign-events
Subscription: sovereign-handler

## 4. Socket.IO
Library:   python-socketio + gevent-websocket (server)
           socket.io-client v4 (browser)
Transport: WebSocket (with long-polling fallback)
Namespace: /sovereign
Events emitted to client:
  - data:extracted
  - data:gnn:updated
  - data:worldmodel:updated
  - data:causal:updated
  - data:report:ready
  - hitl:request
  - error:pipeline

## 5. PostgreSQL (Cloud SQL)
See spec 16_database.md for full schema.
Connection: Cloud SQL Auth Proxy in Cloud Run
Instance:   {PROJECT_ID}:{REGION}:sovereign-db

## 6. D3.js (browser)
Version:   7.x (CDN: cdn.jsdelivr.net)
Used for:  Causal tree visualization, GNN graph rendering
Canvas:    SVG-based, 60 fps throttle

## Timeout Summary
| Resource      | Timeout   | Retry |
|---------------|-----------|-------|
| Gemini API    | 30 s      | 3x    |
| PostgreSQL    | 10 s      | 3x    |
| Cloud Storage | 60 s      | 2x    |
| SocketIO emit | 5 s       | 1x    |
| HITL modal    | 300 s     | 0x    |

## Test Points
- EXT_001: Gemini API call with valid key returns structured JSON
- EXT_002: Gemini timeout triggers E002 and retry up to 3 times
- EXT_003: PostgreSQL connection failure triggers E008 and retry
- EXT_004: SocketIO data:report:ready received by browser client
- EXT_005: Invalid Gemini JSON response triggers E003 and retry
