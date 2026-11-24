# Docker cheatsheet

## Containers

```bash
docker run -d --name web -p 127.0.0.1:8080:80 nginx:1.27   # run in background
docker run --rm -it python:3.11-slim bash                  # throwaway shell
docker ps / docker ps -a                                   # running / all
docker logs -f --tail 100 web
docker exec -it web sh
docker stop web / docker start web / docker restart web
docker rm web            # docker rm -f web: stop + remove
docker inspect web       # everything; -f '{{.State.ExitCode}}' for one field
docker stats             # live CPU / memory
docker top web
docker cp web:/etc/nginx/nginx.conf .
```

## Images

```bash
docker build -t app:1.0 .                 # -f other.Dockerfile, --no-cache, --target build
docker images
docker history app:1.0
docker tag app:1.0 ghcr.io/team/app:1.0
docker push ghcr.io/team/app:1.0
docker pull python:3.11-slim
docker image inspect python:3.11-slim --format '{{index .RepoDigests 0}}'
docker rmi app:1.0
docker save -o app.tar app:1.0 / docker load -i app.tar
docker buildx build --platform linux/amd64,linux/arm64 -t ghcr.io/team/app:1.0 --push .
```

## Volumes and networks

```bash
docker volume create data / docker volume ls / docker volume inspect data
docker run -v data:/var/lib/postgresql/data postgres:16-alpine
docker run -v "$(pwd)":/app -w /app python:3.11-slim python main.py   # bind mount
docker network create app-net
docker run --network app-net --name db ...
docker network inspect app-net
```

## Compose

```bash
docker compose up -d --build
docker compose ps / logs -f / exec app sh
docker compose config        # merged final config
docker compose down          # keeps volumes
docker compose down -v       # deletes named volumes
```

## Disk space

```bash
docker system df [-v]
docker container prune                     # stopped containers
docker image prune [-a]                    # dangling [all unused] images
docker builder prune --max-used-space 20GB # build cache budget (older: --keep-storage)
docker volume prune [-a]                   # anonymous [also named] unused volumes
docker system prune [-a] [--volumes]
docker system df | python -m dockerhygiene.cli df     # cleanup plan from this repo
```

## Dockerfile skeleton

```dockerfile
# syntax=docker/dockerfile:1
FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1
RUN useradd --system --uid 10001 app
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=app:app . .
USER 10001
EXPOSE 8080
HEALTHCHECK CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health')"]
CMD ["python", "server.py"]
```

## Exit codes

`0` ok · `1` app error · `125` docker run failed · `126` not executable ·
`127` not found · `137` SIGKILL (OOM or stop timeout) · `139` segfault · `143` SIGTERM
