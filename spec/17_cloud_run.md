# Cloud Run Deployment Specification

Version: 1.0.0

## Platform
Google Cloud Run (fully managed, serverless containers)

## Container Image
Base: python:3.11-slim
Registry: gcr.io/{PROJECT_ID}/sovereign-matrix:latest
Build tool: Cloud Build (cloudbuild.yaml)

## Port
Container listens on: 8080 (set via SOVEREIGN_PORT)
Cloud Run maps: HTTPS 443 → container 8080

## Environment Variables (set in Cloud Run service)
SOVEREIGN_GEMINI_API_KEY  (Secret Manager reference)
SOVEREIGN_DB_HOST
SOVEREIGN_DB_USER
SOVEREIGN_DB_PASSWORD
SOVEREIGN_DB_NAME
SOVEREIGN_DB_PORT
SOVEREIGN_LOG_LEVEL       (default: INFO)
SOVEREIGN_PORT            (default: 8080)

## Resource Limits
| Setting         | Value    |
|-----------------|----------|
| CPU             | 2 vCPU   |
| Memory          | 2 GiB    |
| Min instances   | 1        |
| Max instances   | 10       |
| Request timeout | 300 s    |
| Concurrency     | 80       |

## cloudbuild.yaml Steps
1. docker build -t gcr.io/$PROJECT_ID/sovereign-matrix:$COMMIT_SHA .
2. docker push gcr.io/$PROJECT_ID/sovereign-matrix:$COMMIT_SHA
3. gcloud run deploy sovereign-matrix --image ... --region us-central1

## Dockerfile Requirements
- Multi-stage build to minimize image size
- Non-root user (uid 1000)
- COPY requirements.txt first (layer caching)
- RUN pip install --no-cache-dir -r requirements.txt
- ENTRYPOINT: gunicorn with gevent worker for SocketIO compatibility
  gunicorn -w 1 -k geventwebsocket.gunicorn.workers.GeventWebSocketWorker \
           -b 0.0.0.0:8080 app:app

## Health Check
Endpoint: GET /api/health
Cloud Run liveness probe: every 30 seconds
Expected response: HTTP 200, JSON with status "OK" or "DEGRADED"

## CI/CD Gate
Tests must pass (pytest) before Cloud Build triggers docker build.

## Secrets Management
- SOVEREIGN_GEMINI_API_KEY stored in Google Secret Manager
- Cloud Run service account granted roles/secretmanager.secretAccessor

## Gemini API Key Location and Access

### Development (Local)
- Location: `.env` file in project root (not committed to version control)
- Format: `SOVEREIGN_GEMINI_API_KEY="your_api_key_here"`
- Load via: `python-dotenv`

```python
from dotenv import load_dotenv
load_dotenv()
GEMINI_API_KEY = os.getenv('SOVEREIGN_GEMINI_API_KEY')
```

### Production (Cloud Run)
- Location: Google Secret Manager
- Secret name: `SOVEREIGN_GEMINI_API_KEY`
- IAM requirement: Cloud Run service account must have `roles/secretmanager.secretAccessor`
- Mounting: Injected as environment variable via Cloud Run secret reference (preferred)
  - In `gcloud run deploy`: `--set-secrets=SOVEREIGN_GEMINI_API_KEY=SOVEREIGN_GEMINI_API_KEY:latest`
- Fallback code pattern in `app.py` (if env var not injected):

```python
import os
from google.cloud import secretmanager

def get_secret(secret_id: str) -> str:
    """Fetch secret from Google Secret Manager. E008 on failure."""
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{PROJECT_ID}/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")

GEMINI_API_KEY = os.getenv("SOVEREIGN_GEMINI_API_KEY") or get_secret("SOVEREIGN_GEMINI_API_KEY")
```

### Staging / CI-CD Pipelines
- Use Secret Manager secrets bound to the staging Cloud Run service
- For GitHub Actions / Cloud Build: inject via `--set-secrets` or `secretEnv` in `cloudbuild.yaml`
- Never pass API keys as plaintext build arguments (`ARG` / `--build-arg`)

### Security Rules
| Rule | Requirement |
|------|-------------|
| `.env` in `.gitignore` | MUST be ignored — never committed |
| Secret rotation | Rotate via Secret Manager; Cloud Run picks up `latest` on next deploy |
| Least privilege | Service account scoped to `secretmanager.secretAccessor` only |
| Logging | API key value MUST NOT appear in any log output |

## Test Points
- CR_001: /api/health returns HTTP 200 after container startup
- CR_002: Container starts in < 10 seconds (cold start)
- CR_003: SOVEREIGN_GEMINI_API_KEY injected from Secret Manager at runtime
- CR_004: Concurrent 80 requests handled without 5xx errors
- CR_005: Max instances scales to 10 under load test
