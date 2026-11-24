# syntax=docker/dockerfile:1
# A small, production-style image for examples/app. Build from the examples/ folder:
#   docker build -t hello-app:1.0 examples
# Each line is explained in docs/chapters/04-writing-a-dockerfile.md.

# 1. Pin the base image. For production also pin the digest:
#    FROM python:3.11-slim@sha256:<digest>
FROM python:3.11-slim

# 2. Metadata: where the source lives (shows up in registries and scanners).
LABEL org.opencontainers.image.title="hello-app" \
      org.opencontainers.image.source="https://github.com/Avinash186200/docker-from-scratch"

# 3. Python settings: no .pyc files, unbuffered logs so 'docker logs' is live.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    DATA_DIR=/data

# 4. A non-root user with a fixed id (fixed ids make volume permissions predictable).
RUN groupadd --system --gid 10001 app \
 && useradd --system --uid 10001 --gid app --no-create-home app \
 && mkdir -p /data && chown app:app /data

WORKDIR /app

# 5. Copy only what the app needs. .dockerignore keeps the rest out of the context.
COPY --chown=app:app app/ ./

USER 10001:10001

# 6. Document the port. It does not publish it: 'docker run -p' does that.
EXPOSE 8080

# 7. Let Docker know whether the app works, not just whether the process is alive.
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=2).status == 200 else 1)"]

# 8. Exec form, so the app is PID 1 and receives SIGTERM from 'docker stop'.
CMD ["python", "server.py"]
