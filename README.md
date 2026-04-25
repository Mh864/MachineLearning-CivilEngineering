How to run (local, without Docker)
```bash
pip install -r requirements.txt
python run_api.py
# API: http://localhost:8000
```
In a second terminal:

```bash
cd frontend1
npm install
npm run dev
# Web: http://localhost:3000
```

#How to run (Docker from this repo)

From the repo root:
```bash
docker compose up -d --build
```
- Web: `http://localhost:3000`
- API: `http://localhost:8000/health`

How to run (pull images from Docker Hub)
This project is published as two images: one for the API and one for the web UI.

### Option A: run with Docker Compose (recommended)

1) Create a file named `docker-compose.pull.yml` with the following contents:

```yaml
services:
  api:
    image: YOUR_DOCKERHUB_USER/flood-api:latest
    ports:
      - "8000:8000"
  web:
    image: YOUR_DOCKERHUB_USER/flood-web:latest
    environment:
      - NEXT_PUBLIC_API_URL=http://api:8000
    ports:
      - "3000:3000"
    depends_on:
      - api
```

2) Pull + run:

```bash
docker compose -f docker-compose.pull.yml pull
docker compose -f docker-compose.pull.yml up -d
```

### Option B: run with `docker run`

```bash
docker pull YOUR_DOCKERHUB_USER/flood-api:latest
docker pull YOUR_DOCKERHUB_USER/flood-web:latest

docker network create floodnet

docker run -d --name flood-api --network floodnet -p 8000:8000 YOUR_DOCKERHUB_USER/flood-api:latest
docker run -d --name flood-web --network floodnet -p 3000:3000 -e NEXT_PUBLIC_API_URL=http://flood-api:8000 YOUR_DOCKERHUB_USER/flood-web:latest
```

Then open:
- Web: `http://localhost:3000`
- API health: `http://localhost:8000/health`

Notes:
- The final report and slides are in `Rapport&PowerPoint/`.
- The `docs/` folder contains more detailed documentation.
- Rivers do not flood very commonly, so here are some dates where they do:
