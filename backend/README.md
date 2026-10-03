# ImageUp Backend

FastAPI + Celery + Redis, with Real-ESRGAN upscaling (PIL fallback when ML deps
are missing).

## Run (local)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

# Redis must be running (e.g. docker run --rm -p 6379:6379 redis:7-alpine)

# Terminal 1: API
uvicorn app.main:app --reload --port 8000

# Terminal 2: Celery worker
celery -A app.worker worker --loglevel=info --concurrency=1
```

API docs at http://localhost:8000/docs.

## Endpoints

| Method | Path                     | Description                                            |
|--------|--------------------------|--------------------------------------------------------|
| GET    | `/api/health`            | Liveness + ML availability                             |
| GET    | `/api/config`            | Upload limits (max upload MB, max input px, etc.)     |
| POST   | `/api/enhance`           | `multipart` upload → returns `{task_id, status}`      |
| GET    | `/api/status/{task_id}`  | Poll task status (result URL once `done`)              |
| GET    | `/api/uploads/{task_id}` | Original upload (302 → short-lived presigned R2 GET)   |
| GET    | `/api/results/{file}`    | Enhanced result (302 → short-lived presigned R2 GET)   |

## Architecture

```
FastAPI (web)  ──put upload──> R2 tmp/uploads/imageup/{task_id}/…
       │
       └──enqueue──> Celery broker (Redis, imageup:* keys)
                              │
                              v
                       Celery worker ──get upload──> Real-ESRGAN
                              │                        │
                              └──put result──> R2 tmp/results/imageup/{task_id}/result.webp

       Redis hash: imageup:task:{id}   (status, keys, urls, elapsed, …)
```

Results and uploads live in the private `agenteresolve-tmp` bucket (24h
lifecycle). Downloads are short-lived presigned GETs issued by the API.
Without `R2_*` credentials the service falls back to local disk under
`storage/` so local dev and CI still work end-to-end.

### Key isolation

All Redis keys are prefixed with `imageup:` (configurable via
`REDIS_KEY_PREFIX`) so this project can share a Redis instance with other
projects without key collisions. Celery's own result-backend keys are also
namespaced via a `global_keyprefix` transport option. Tasks are published to
and consumed only from `CELERY_QUEUE` (default `imageup`), which must be unique
for each project sharing the broker.

## Enabling real ML

The `torch` / `realesrgan` / `basicsr` packages are commented out in
`requirements.txt` because they are large. To run the actual model on a VPS:

```bash
# CPU build (smaller)
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install realesrgan basicsr
```

Then set `ENABLE_ML=1` (default). Set `USE_GPU=1` + install the CUDA torch
build for GPU acceleration.

Without the ML deps the worker falls back to **PIL Lanczos** upscaling so the
end-to-end flow still works for local dev / CI / a tiny VPS.

## Environment

See `.env.example`. Key variables:

- `MAX_INPUT_PX` — reject inputs whose largest side exceeds this (default 1000).
- `MAX_UPLOAD_MB` — reject uploads above this size in MB (default 8).
- `OUTPUT_QUALITY` — JPEG/WEBP quality for saved results (default 90).
- `REDIS_URL`, `REDIS_KEY_PREFIX` — broker + key namespace.
- `USE_GPU`, `MODEL_NAME`, `ENABLE_ML`, `FALLBACK_IF_UNAVAILABLE`.
- `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_ENDPOINT`, `R2_BUCKET_TMP`,
  `R2_PRESIGN_EXPIRY_SEC` — Cloudflare R2 storage (leave blank for local disk).
- `CLERK_JWKS_URL`, `CLERK_ISSUER`, `CLERK_AUDIENCE` — optional Clerk JWT
  verification on `POST /api/enhance`. Anonymous requests are allowed with a
  stricter `MAX_UPLOAD_MB`; verified users get `AUTH_MAX_UPLOAD_MB`.

## Tests

```bash
pip install pytest "PyJWT[crypto]" boto3
pytest tests/ -v
```

The suite mocks the S3 client (R2 helper) and verifies JWTs against a locally
generated RSA keypair (Clerk verifier) — no network or cloud credentials needed.