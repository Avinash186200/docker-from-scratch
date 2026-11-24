# syntax=docker/dockerfile:1
# Multi-stage build: tools and caches stay in the "build" stage, only the result
# is copied into the small runtime stage. Build from the examples/ folder:
#   docker build -f multistage.Dockerfile -t hello-app:ms examples
# Explained in docs/chapters/05-layers-cache-and-image-size.md.

# ---------- stage 1: build ----------
FROM python:3.11-slim AS build
WORKDIR /src
# Dependencies first (they change rarely), so this layer stays cached.
COPY app/requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m venv /venv \
 && /venv/bin/pip install -r requirements.txt
# Then the code (changes often).
COPY app/ .
RUN /venv/bin/python -m compileall -q .

# ---------- stage 2: runtime ----------
FROM python:3.11-slim AS runtime
ENV PATH="/venv/bin:$PATH" PYTHONUNBUFFERED=1 DATA_DIR=/data
RUN groupadd --system --gid 10001 app \
 && useradd --system --uid 10001 --gid app --no-create-home app \
 && mkdir -p /data && chown app:app /data
COPY --from=build /venv /venv
COPY --from=build --chown=app:app /src /app
WORKDIR /app
USER 10001:10001
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=2).status == 200 else 1)"]
CMD ["python", "server.py"]
