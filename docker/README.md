# Docker (Next.js frontend)

The dashboard lives in `frontend1/` (Next.js 16). Compose uses **profiles** so dev and prod stacks stay separate.

## One-command workflows

From the **repository root**:

| Goal | Command |
|------|---------|
| **Development** (hot reload on **http://localhost:3001** — avoids clashing with local Next on 3000) | `docker compose --profile dev up --build` |
| **Production** (optimized build, **Nginx** on **8080** → Next) | `docker compose --profile prod up --build` |
| Same via Make | `make docker-frontend-dev` or `make docker-frontend-prod` |

Stop containers: `docker compose --profile dev down` or `--profile prod down`, or `make docker-frontend-down`.

## API URL (browser → FastAPI)

`NEXT_PUBLIC_*` is inlined at **build** time. For production image builds, set before `up --build`:

```bash
# Linux / macOS
export NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
docker compose --profile prod up --build
```

```powershell
# Windows PowerShell
$env:NEXT_PUBLIC_API_URL = "http://127.0.0.1:8000"
docker compose --profile prod up --build
```

The browser must be able to reach that URL (not `http://web:3000`). Use your machine’s IP or `host.docker.internal` if the API also runs in Docker.

## Folder name `frontend` instead of `frontend1`

Edit `docker-compose.yml`: replace `./frontend1` with `./frontend` in `context` and `volumes`.

## Ports

- **Dev:** host **`3001`** → container `3000` (Next dev server). Set `DOCKER_WEB_DEV_PORT` to use another host port (e.g. `3005`).
- **Prod:** `8080` → Nginx → Next on internal port `3000`. Change `8080:80` in `docker-compose.yml` if needed.
