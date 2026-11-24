# 10. Logs, debugging and troubleshooting

## Logs

Apps in containers should log to **stdout and stderr**, not to files. Docker
collects those streams; your platform ships them on (CloudWatch, Loki, ELK...).

```bash
docker logs web
docker logs -f --since 10m --tail 100 web
```

On Docker Engine, the default `json-file` log driver keeps logs **without any size
limit** unless you set one. A chatty container can fill a disk with logs alone. Set limits per
container, in Compose, or for the whole engine in `daemon.json`:

```json
{ "log-driver": "json-file", "log-opts": { "max-size": "10m", "max-file": "3" } }
```

## The debugging toolkit

| Command | Answers |
|---|---|
| `docker ps -a` | Is it running? When did it exit? |
| `docker logs CONTAINER` | What did it print before it died? |
| `docker inspect CONTAINER` | Exit code, OOMKilled, mounts, env, network, health log. |
| `docker inspect -f '{{.State.ExitCode}} {{.State.OOMKilled}}' C` | Why it stopped. |
| `docker inspect -f '{{json .State.Health}}' C` | Healthcheck history. |
| `docker exec -it C sh` | Look around inside a running container. |
| `docker run --rm -it --entrypoint sh IMAGE` | Look inside an image whose app crashes on start. |
| `docker stats` | Live CPU, memory, network, I/O per container. |
| `docker top C` | Processes inside. |
| `docker events` | Live stream of what the engine is doing. |
| `docker cp C:/path ./local` | Copy a file out (works on stopped containers too). |
| `docker debug C` | (Docker Desktop) a shell with tools, even for distroless images. |

## Exit codes

| Code | Usual meaning |
|---|---|
| 0 | Finished normally. |
| 1 | The app failed (read the logs). |
| 125 | `docker run` itself failed (bad flag, name in use). |
| 126 | The command exists but cannot run (permissions, not executable). |
| 127 | Command not found (typo, missing binary, wrong `PATH`). |
| 137 | 128 + 9: killed with SIGKILL. Out of memory (`OOMKilled: true`), or `docker stop` timed out because the app ignored SIGTERM. |
| 139 | 128 + 11: segmentation fault. |
| 143 | 128 + 15: stopped by SIGTERM and exited without handling it. |

## Common problems and the first thing to check

| Symptom | Check |
|---|---|
| Container exits right away | `docker logs`. Is the main command a one-shot command or a server? A container lives only as long as its PID 1. |
| "port is already allocated" | Something else uses that host port: change the left side of `-p`. |
| Can't reach the app via `-p` | Is the app listening on `0.0.0.0` inside? ([chapter 7](07-networking.md)) |
| "permission denied" on a volume | User id inside vs owner of the folder ([chapter 6](06-storage-volumes-and-bind-mounts.md)). |
| `exec format error` | Image built for another CPU (arm64 vs amd64). Use `--platform` or a multi-arch image. |
| Build is slow every time | Cache busted early: `COPY . .` before dependency install ([chapter 5](05-layers-cache-and-image-size.md)). |
| `no space left on device` | `docker system df` ([chapter 16](16-disk-space-and-cleanup.md)). |
| Every command fails with "input/output error" | The Docker disk itself is unhealthy, often after the host disk filled up. See the [case study](18-case-study-disk-full.md). |

## Check yourself

1. A container restarts again and again with exit code 137. What two causes would
   you check, and how?
2. Why should a containerised app log to stdout rather than to a file?
3. How do you get a shell in an image whose entrypoint crashes on start?
