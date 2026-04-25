Notes:
- The final report and slides are in `Rapport&PowerPoint/`.
- The `docs/` folder contains more detailed documentation.

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

How to run (Docker from this repo)

From the repo root:
```bash
docker compose up -d --build
```
- Web: `http://localhost:3000`
- API: `http://localhost:8000/health`


How to run by pulling images from Docker Hub (Second Option using DockerHub)
This project is published as two images: one for the API and one for the web UI.

```bash
docker pull hadysouaiby/flood-api:latest
docker pull hadysouaiby/flood-web:latest

docker network create floodnet

docker run -d --name flood-api --network floodnet -p 8000:8000 hadysouaiby/flood-api:latest
docker run -d --name flood-web --network floodnet -p 3000:3000 -e NEXT_PUBLIC_API_URL=http://flood-api:8000 hadysouaiby/flood-web:latest
```

Then open:
- Web: `http://localhost:3000`
- API health: `http://localhost:8000/health`

N.B: Rivers do not flood everyday, so here are some of the many dates when they do:
Potomac River on 04/04/2024
Willamette 01/19/2024
Neuse 04/13/2023
Trinity 04/30/2024
