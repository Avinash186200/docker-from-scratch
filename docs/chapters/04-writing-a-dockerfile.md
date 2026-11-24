# 4. Writing a Dockerfile

## The instructions

| Instruction | What it does | Makes a layer with files? |
|---|---|---|
| `FROM image` | Start from a base image. Every Dockerfile starts here. | (base layers) |
| `RUN cmd` | Run a command at **build** time (install packages, compile). | Yes |
| `COPY src dst` | Copy files from the build context into the image. | Yes |
| `ADD src dst` | Like COPY, but also fetches URLs and auto-extracts local tar files. | Yes |
| `WORKDIR /app` | Set the working directory (creates it). | Tiny |
| `ENV KEY=value` | Environment variable at build **and** run time. | No (metadata) |
| `ARG NAME=default` | Variable at **build** time only (`--build-arg`). | No |
| `USER app` | Run the following steps and the container as this user. | No |
| `EXPOSE 8080` | Documents a port. Does **not** publish it. | No |
| `CMD [...]` | Default command when the container starts. Easy to override. | No |
| `ENTRYPOINT [...]` | The fixed program; `CMD` becomes its default arguments. | No |
| `HEALTHCHECK` | A command Docker runs to decide healthy / unhealthy. | No |
| `LABEL k=v` | Metadata (source repo, version, owner). | No |
| `VOLUME /data` | Marks a path as a volume. Creates an anonymous volume per container if you do not mount one. | No |

## Walkthrough of the example

The repo's [`examples/Dockerfile`](../../examples/Dockerfile), line by line.
Note: a Dockerfile comment must start its own line. There are no comments at the
end of an instruction; `FROM python:3.11-slim  # base` is a parse error.

```dockerfile
# syntax=docker/dockerfile:1
# (first line: use the current Dockerfile syntax, BuildKit)

# pinned, small base
FROM python:3.11-slim
LABEL org.opencontainers.image.source="https://github.com/..."

# unbuffered = logs show up live
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 DATA_DIR=/data

# one RUN = one layer
RUN groupadd --system --gid 10001 app \
 && useradd --system --uid 10001 --gid app --no-create-home app \
 && mkdir -p /data && chown app:app /data
WORKDIR /app

# only the app folder
COPY --chown=app:app app/ ./

# numeric user id: never root, and checkable by Kubernetes
USER 10001:10001
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD ["python", "-c", "...urlopen('http://127.0.0.1:8080/health')..."]

# exec form: the app runs as PID 1 (the container's main process, chapter 14)
CMD ["python", "server.py"]
```

Build and run it:

```bash
docker build -t hello-app:1.0 examples
docker run --rm -p 127.0.0.1:8080:8080 hello-app:1.0
curl http://127.0.0.1:8080/        # hello from a container (hit 1)
```

## The build context and `.dockerignore`

`docker build PATH` sends the folder at `PATH` (the **context**) to the builder.
`COPY` can only see files inside it. Without a `.dockerignore`, the builder gets
your `.git` folder, virtual envs, data files and any `.env` with secrets, and a
`COPY . .` puts them in the image.

```gitignore
# .dockerignore
.git
**/__pycache__
**/.venv
**/.env
*.pem
data/
```

## CMD vs ENTRYPOINT

| You write | `docker run img` runs | `docker run img --help` runs |
|---|---|---|
| `CMD ["python", "app.py"]` | `python app.py` | `--help` (replaces CMD; fails) |
| `ENTRYPOINT ["python", "app.py"]` | `python app.py` | `python app.py --help` |
| `ENTRYPOINT ["python", "app.py"]` + `CMD ["--port", "80"]` | `python app.py --port 80` | `python app.py --help` |

Rule of thumb: use `CMD` for apps. Use `ENTRYPOINT` when the image *is* a tool
(`docker run my-cli --flag`), or with a small entrypoint script that does setup
and then `exec "$@"`.

## Exec form vs shell form

```dockerfile
# exec form: python is PID 1, gets signals
CMD ["python", "server.py"]

# shell form: /bin/sh -c "python server.py" is PID 1
CMD python server.py
```

(A trailing comment here would be worse than a style issue: `CMD ["python",
"server.py"]  # note` is no longer valid JSON, so Docker silently treats the whole
line as shell form.)

With shell form, `docker stop` sends SIGTERM to the shell, which does not pass it
on. Docker waits for the grace period and then SIGKILLs your app (exit code 137).
We measured this with the example app in [chapter 14](14-production-patterns.md):
exec form stopped in 0.3 s with exit 0; shell form was killed with exit 137.

## COPY vs ADD

Use `COPY`. `ADD` has two hidden behaviours: it downloads URLs and it unpacks local
tar archives. Use `ADD` only when you want exactly that.

## ARG vs ENV

- `ARG` exists only during the build. Good for versions: `ARG PY_VERSION=3.11`.
- `ENV` is baked into the image and visible at run time.
- Neither is safe for secrets: both can be seen in `docker history` or
  `docker inspect`. See [chapter 9](09-configuration-and-secrets.md).

## Check your Dockerfile

```bash
python -m dockerhygiene.cli check examples/Dockerfile      # this repo's teaching linter
docker run --rm -i hadolint/hadolint < examples/Dockerfile  # the standard linter
```

## Check yourself

1. Why does `EXPOSE` alone not make the app reachable from your browser?
2. What does `.dockerignore` protect you from?
3. When would you use `ENTRYPOINT` instead of `CMD`?

Next: [lab 2 and lab 3](../../labs/README.md#lab-2-build-your-own-image).
