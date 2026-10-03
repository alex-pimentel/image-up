# ImageUp Frontend

Vue 3 + Vite + PrimeVue + Tailwind v4, using the shared Agenteresolve design
tokens and optional Clerk authentication.

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

## Design system

Tailwind v4 is the CSS engine. `src/assets/main.css` imports the framework and
then the shared token layer from `@agenteresolve/ui`:

```css
@import "tailwindcss";
@import "@agenteresolve/ui/styles.css";
```

This gives the app the Agenteresolve dark/glass palette, brand colors and the
Inter typeface. The React components in `@agenteresolve/ui` are **not** used —
only its token CSS. Header/footer mirror the shared Service Shell visually and
link to the sibling services. PrimeVue runs in dark mode via the `.app-dark`
selector so its widgets match the tokens.

## Authentication (Clerk, optional)

`src/services/clerk.ts` wraps `@clerk/clerk-js`:

- Set `VITE_CLERK_PUBLISHABLE_KEY` to enable login and send a Bearer token with
  `POST /api/enhance`.
- Without the key the app runs fully anonymous and the header shows a neutral
  fallback link (no crash).

## Size restriction

The current preview build restricts the **largest input side to 1000px**
(fetched from `GET /api/config`, server-configurable via `MAX_INPUT_PX`).
A banner and inline rejection message inform the user. Larger limits are
available to authenticated users server-side (`AUTH_MAX_UPLOAD_MB`).