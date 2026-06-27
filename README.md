<div align="center">
  <h1>ImageUp — AI Image Enhancer</h1>
  <p><strong>AI-powered image upscaling & enhancement</strong></p>
  <p>Upload a low-resolution or blurry image and get back a high-resolution, enhanced version — async task queue with Real-ESRGAN.</p>

  <p>
    <img src="https://img.shields.io/badge/python-3.11%2B-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python">
    <img src="https://img.shields.io/badge/fastapi-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
    <img src="https://img.shields.io/badge/celery-5.6-37814A?style=for-the-badge&logo=celery&logoColor=white" alt="Celery">
    <img src="https://img.shields.io/badge/vue%203-4FC08D?style=for-the-badge&logo=vuedotjs&logoColor=white" alt="Vue 3">
    <img src="https://img.shields.io/badge/vite-646CFF?style=for-the-badge&logo=vite&logoColor=white" alt="Vite">
    <img src="https://img.shields.io/badge/primevue-41B883?style=for-the-badge&logo=primevue&logoColor=white" alt="PrimeVue">
    <img src="https://img.shields.io/badge/redis-7.4-DC382D?style=for-the-badge&logo=redis&logoColor=white" alt="Redis">
    <img src="https://img.shields.io/badge/docker-compose-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker">
    <img src="https://img.shields.io/badge/Real--ESRGAN-FF6F00?style=for-the-badge&logo=ai&logoColor=white" alt="Real-ESRGAN">
    <img src="https://img.shields.io/badge/license-MIT-green?style=for-the-badge" alt="License">
  </p>

  <p>
    <a href="https://github.com/alex-pimentel/image-up/actions/workflows/ci.yml"><img src="https://github.com/alex-pimentel/image-up/actions/workflows/ci.yml/badge.svg?branch=main" alt="CI"></a>
    <a href="https://github.com/alex-pimentel/image-up/actions/workflows/lint.yml"><img src="https://github.com/alex-pimentel/image-up/actions/workflows/lint.yml/badge.svg?branch=main" alt="Lint"></a>
    <a href="https://github.com/alex-pimentel/image-up/actions/workflows/test.yml"><img src="https://github.com/alex-pimentel/image-up/actions/workflows/test.yml/badge.svg?branch=main" alt="Test"></a>
    <a href="https://github.com/alex-pimentel/image-up/actions/workflows/security.yml"><img src="https://github.com/alex-pimentel/image-up/actions/workflows/security.yml/badge.svg?branch=main" alt="Security"></a>
    <a href="https://github.com/alex-pimentel/image-up/actions/workflows/build.yml"><img src="https://github.com/alex-pimentel/image-up/actions/workflows/build.yml/badge.svg?branch=main" alt="Build"></a>
    <a href="https://github.com/alex-pimentel/image-up/actions/workflows/deploy.yml"><img src="https://github.com/alex-pimentel/image-up/actions/workflows/deploy.yml/badge.svg?branch=main" alt="Deploy"></a>
  </p>
</div>

---

## Preview

<p align="center">
  <img src="docs/preview.gif" alt="ImageUp preview" width="800">
  <br />
  <a href="https://imageup.agenteresolve.com.br" target="_blank"><strong><code>try now →</code></strong></a>
</p>

---

## Features

- **AI upscaling** — Powered by Real-ESRGAN with GFPGAN face enhancement
- **Async task queue** — Celery + Redis for non-blocking, scalable processing
- **Real-time progress** — Frontend polls task status until completion
- **Before / after slider** — Drag comparison with one-click download
- **Graceful fallback** — High-quality Lanczos upscaling when ML deps unavailable
- **Dockerized** — Multi-container setup with hot-reload in development

---

## Architecture

```
[ Vue 3 + PrimeVue ]  ──> Cloudflare Pages / Nginx
        │  POST /api/enhance   (multipart upload) ──> task_id
        │  GET  /api/status/{id}  (poll 1.5s)    <── status + result url
        v
[ FastAPI (Python) ]  ──> VPS (Hetzner / DigitalOcean)
        │  enqueue task
        v
[ Celery Worker ]  ──> Redis (broker + result backend)
        │
        v
[ Real-ESRGAN / GFPGAN ]  (CPU or GPU)
        │
        v
[ results/ ]  ──> served as static files
```

---

## Stack

| Layer | Technology |
|---|---|
| **API** | [FastAPI](https://fastapi.tiangolo.com/) + [Uvicorn](https://www.uvicorn.org/) |
| **Frontend** | [Vue 3](https://vuejs.org/) + [Vite](https://vite.dev/) + [PrimeVue](https://primevue.org/) |
| **Queue** | [Celery](https://docs.celeryq.dev/) + [Redis](https://redis.io/) |
| **AI Model** | [Real-ESRGAN](https://github.com/xinntao/Real-ESRGAN) / [GFPGAN](https://github.com/TencentARC/GFPGAN) |
| **Container** | [Docker Compose](https://docs.docker.com/compose/) |

---

## Repository layout

```
image-up/
├── frontend/          # Vue 3 + PrimeVue SPA (Vite)
│   ├── src/
│   │   ├── components/   # UploadZone, ImageComparer, StatusCard
│   │   ├── pages/        # Home page
│   │   └── services/     # API client, polling
│   └── ...
├── backend/           # FastAPI + Celery worker
│   ├── app/
│   │   ├── api/          # REST routes
│   │   ├── core/         # Config, Redis, Celery app
│   │   ├── models/       # Pydantic schemas
│   │   └── services/     # Upscaling logic (ML + fallback)
│   └── tests/
├── docs/              # Architecture diagram
└── docker-compose.yml
```

See `backend/README.md` and `frontend/README.md` for per-service details.

---

## Quick start

```bash
# Prerequisites: Python 3.11+, pnpm, Redis (or Docker)

# 1. Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000

# 2. Frontend (new terminal)
cd frontend
pnpm install
cp .env.example .env          # set VITE_API_BASE=http://localhost:8000
pnpm dev
```

Or run the whole stack with Docker:

```bash
docker compose up --build
# frontend -> http://localhost:8081
# backend  -> http://localhost:8000  (docs at /docs)
```

### Services

| Service | URL | Description |
|---|---|---|
| **Frontend** | http://localhost:8081 | Vue 3 SPA with upload & comparison slider |
| **API** | http://localhost:8000 | FastAPI backend |
| **API Docs** | http://localhost:8000/docs | Swagger UI |

---

## How it works

1. **Upload** — Drag & drop or select an image in the web UI → `POST /api/enhance`
2. **Queue** — Backend enqueues a Celery task → returns `task_id` immediately
3. **Process** — Celery worker runs Real-ESRGAN (or Lanczos fallback if ML deps missing)
4. **Poll** — Frontend polls `GET /api/status/{task_id}` every 1.5s
5. **Compare** — Once complete, drag the before/after slider and download

```
POST /api/enhance         →  { task_id: "abc-123", status: "queued" }
GET  /api/status/abc-123  →  queued → processing → done
GET  /api/results/abc-123.webp  →  image/webp (binary)
```

---

## Environment variables

| Service | Var | Default | Description |
|---|---|---|---|
| backend | `MAX_UPLOAD_MB` | `8` | Max upload size in MB |
| backend | `MAX_INPUT_PX` | `1000` | Max input side length in px |
| backend | `ALLOWED_ORIGINS` | `http://localhost:5173` | CORS origins, comma-separated |
| backend | `USE_GPU` | `0` | `1` to use CUDA, `0` for CPU |
| backend | `MODEL_NAME` | `RealESRGAN_x4plus` | Real-ESRGAN model variant |
| backend | `OUTPUT_QUALITY` | `90` | JPEG/WEBP quality for results |
| backend | `RESULT_TTL_SEC` | `3600` | Seconds result files are kept |
| backend | `REDIS_URL` | `redis://localhost:6379/0` | Redis broker URL |
| frontend | `VITE_API_BASE` | `http://localhost:8000` | Backend base URL |

---

## Notes & trade-offs

- **Fallback mode**: If `torch` / `realesrgan` are not installed (e.g. on a tiny CI box), the service transparently degrades to PIL Lanczos upscaling so the API contract still works end-to-end. Set `ENABLE_ML=1` to require the real model.
- **Memory**: The default model needs ~1.5GB RAM. For 4GB VPSes use `MODEL_NAME=RealESRGAN_x4plus_anime_6B` or the compact `realesr-animevideov3`.
- **Caching**: Finished results are served from disk with a configurable TTL and could be fronted by Cloudflare's CDN cache.

---

## License

[MIT](LICENSE.md) © 2026

---

<div align="center">
  <sub>Built with ❤️ using FastAPI, Celery, Vue 3, and Real-ESRGAN</sub>
</div>
