# Legacy Vite + React scaffold

This folder is an older **Vite + React** client for manual API checks.

The **current** dashboard for this repository lives in **`frontend1/`** (Next.js App Router, flood UI, `@/lib/api` client). Prefer that app for development unless you are maintaining this scaffold.

## Quick start

```bash
cd frontend/vite-project
npm install
npm run dev
```

Point the UI at the FastAPI backend (default `http://127.0.0.1:8000`). If the project exposes `VITE_API_URL`, set it to your API base URL.

## Templates

This template ships with Vite’s default React setup (see upstream Vite docs for React Compiler, ESLint expansion, etc.).
