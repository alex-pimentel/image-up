# Deploying to EasyPanel

This project has three services. Create each as a separate service in your EasyPanel project.

---

## 1. Redis

| Field | Value |
|---|---|
| **Type** | Image |
| **Image** | `redis:7-alpine` |
| **Port** | `6379` (internal only) |
| **Command** | `redis-server --maxmemory-policy allkeys-lru` |
| **Volumes** | none needed |

---

## 2. Backend API

| Field | Value |
|---|---|
| **Type** | Git |
| **Git URL** | `https://github.com/alex-pimentel/image-up` |
| **Build Dir** | `backend/` |
| **Dockerfile** | `backend/Dockerfile` |
| **Port** | `8000` |
| **Volumes** | `/app/results`, `/app/uploads` (persistent storage) |

### Environment variables

| Variable | Value | Description |
|---|---|---|
| `REDIS_URL` | `redis://<redis-service-name>:6379/0` | Redis connection |
| `CELERY_BROKER_URL` | `redis://<redis-service-name>:6379/0` | Celery broker |
| `CELERY_RESULT_BACKEND` | `redis://<redis-service-name>:6379/0` | Celery result backend |
| `REDIS_KEY_PREFIX` | `imageup:` | Redis key namespace |
| `ALLOWED_ORIGINS` | `https://imageup.agenteresolve.com.br` | CORS origins (comma-separated) |
| `ENABLE_ML` | `1` | Enable ML (`0` to force fallback) |
| `FALLBACK_IF_UNAVAILABLE` | `1` | Fallback to PIL if ML fails |
| `USE_GPU` | `0` | `1` for CUDA GPU |
| `MODEL_NAME` | `RealESRGAN_x4plus` | ML model variant |
| `MODELS_DIR` | `/app/models` | Model weights directory |
| `MAX_UPLOAD_MB` | `8` | Max upload size in MB |
| `MAX_INPUT_PX` | `1000` | Max input side length in px |
| `OUTPUT_QUALITY` | `95` | Output JPEG/WebP quality |
| `OUTPUT_FORMAT` | `webp` | Output format (`webp`, `jpg`, `png`) |
| `DEFAULT_SCALE` | `2` | Default upscale factor |
| `RESULT_TTL_SEC` | `3600` | Result cache TTL in seconds |

> **Replace `<redis-service-name>`** with the actual service name EasyPanel assigns to your Redis service (e.g. `redis` or `imageup-redis-1`).

---

## 3. Worker

| Field | Value |
|---|---|
| **Type** | Git |
| **Git URL** | `https://github.com/alex-pimentel/image-up` |
| **Build Dir** | `backend/` |
| **Dockerfile** | `backend/Dockerfile.worker` |
| **Port** | none (internal) |
| **Volumes** | `/app/models` (shared with Backend API) |

### Environment variables

| Variable | Value | Description |
|---|---|---|
| `REDIS_URL` | `redis://<redis-service-name>:6379/0` | Redis connection |
| `CELERY_BROKER_URL` | `redis://<redis-service-name>:6379/0` | Celery broker |
| `CELERY_RESULT_BACKEND` | `redis://<redis-service-name>:6379/0` | Celery result backend |
| `REDIS_KEY_PREFIX` | `imageup:` | Redis key namespace |
| `ENABLE_ML` | `1` | Enable ML (`0` to force fallback) |
| `FALLBACK_IF_UNAVAILABLE` | `1` | Fallback to PIL if ML fails |
| `USE_GPU` | `0` | `1` for CUDA GPU |
| `MODEL_NAME` | `RealESRGAN_x4plus` | ML model variant |
| `MODELS_DIR` | `/app/models` | Model weights directory |
| `MAX_UPLOAD_MB` | `8` | Must match Backend API |
| `MAX_INPUT_PX` | `1000` | Must match Backend API |
| `OUTPUT_QUALITY` | `95` | Must match Backend API |
| `OUTPUT_FORMAT` | `webp` | Must match Backend API |
| `DEFAULT_SCALE` | `2` | Must match Backend API |
| `RESULT_TTL_SEC` | `3600` | Must match Backend API |

> Worker and Backend API should share identical values for `MAX_*`, `OUTPUT_*`, `DEFAULT_SCALE`, and `RESULT_TTL_SEC`.

---

## volumes

Mount a persistent volume at `/app/models` on **both** Backend API and Worker so model weights are downloaded once and shared. Optionally mount `/app/results` and `/app/uploads` on the Backend API if you need results to survive container restarts.
