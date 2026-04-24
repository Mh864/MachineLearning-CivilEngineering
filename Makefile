.PHONY: docker-frontend-dev docker-frontend-prod docker-frontend-down

# Hot reload: http://localhost:3001 (see DOCKER_WEB_DEV_PORT in docker-compose.yml)
docker-frontend-dev:
	docker compose --profile dev up --build

# Production build behind Nginx: http://localhost:8080 (proxies to Next)
docker-frontend-prod:
	docker compose --profile prod up --build

docker-frontend-down:
	docker compose --profile dev --profile prod down
