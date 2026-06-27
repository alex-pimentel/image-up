# ImageUp Frontend

Vue 3 + Vite + PrimeVue + Tailwind.

## Develop

```bash
pnpm install
cp .env.example .env
pnpm dev          # -> http://localhost:5173 (proxies /api to backend)
```

Set `VITE_API_BASE` to the backend URL (defaults to `http://localhost:8000`).
During dev the Vite proxy forwards `/api/*` to the backend so CORS isn't an issue.

## Build

```bash
pnpm build        # outputs dist/
pnpm preview
```

## App flow

1. User drops / selects an image (`UploadZone.vue`).
2. The frontend validates extension, size (bytes + max input pixels) before
   sending.
3. `POST /api/enhance` returns a `task_id` immediately.
4. The frontend polls `GET /api/status/{task_id}` every 1.5s until
   `status == "done"`.
5. The before/after comparison slider (`ImageComparer.vue`) shows the result.

## Size restriction

The current preview build restricts the **largest input side to 1000px**
(fetched from `GET /api/config`, server-configurable via `MAX_INPUT_PX`).
A banner and inline rejection message inform the user. Larger limits are
intended for the upcoming premium membership layer.