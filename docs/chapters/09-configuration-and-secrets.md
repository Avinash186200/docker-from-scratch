# 9. Configuration and secrets

## Build once, configure at run time

The same image should run in dev, staging and production. What changes between
them (database URL, log level, feature flags) comes in at **run time**, usually as
environment variables. This is the "config" rule of the twelve-factor app.

```bash
docker run -e LOG_LEVEL=debug -e DATABASE_URL=postgres://db/app my-app:1.4.2
docker run --env-file ./staging.env my-app:1.4.2
```

Do not build one image per environment. If staging and production run different
images, you did not test what you ship.

## Where secrets must never go

| Place | Why it leaks |
|---|---|
| `ENV API_KEY=...` in the Dockerfile | Stored in the image config. `docker inspect` shows it. |
| `ARG TOKEN=...` / `--build-arg TOKEN=...` | Visible in `docker history` for steps that use it. |
| `COPY .env .` or `COPY id_rsa .` | The file is in a layer. Deleting it later only hides it. |
| The git repo | Forever in history. |

Anyone who can pull the image can read all of these. Attackers run automated scans
of public images and repos looking for exactly these leaked keys.

```bash
docker history --no-trunc IMAGE   # shows the commands, including ARG values used
docker inspect IMAGE --format '{{json .Config.Env}}'
```

## Secrets needed at build time

Example: a private package index token for `pip` or `npm`. Use a BuildKit secret
mount. The file is available only during that one `RUN` and is never written to a
layer:

```dockerfile
# syntax=docker/dockerfile:1
RUN --mount=type=secret,id=pip_conf,target=/etc/pip.conf \
    pip install --no-cache-dir -r requirements.txt
```

```bash
docker build --secret id=pip_conf,src="$HOME/.config/pip/pip.conf" -t my-app .
```

For private git repos, `RUN --mount=type=ssh` with `docker build --ssh default`
forwards your SSH agent instead of copying a key.

## Secrets needed at run time

From simplest to best:

1. **Environment variables** from your deploy tool. Common and simple, but env vars
   show up in `docker inspect`, crash dumps and child processes.
2. **Secret files** mounted into the container (Compose `secrets:`, Kubernetes
   Secrets as files, Docker Swarm secrets). Many official images support a `_FILE`
   variant, for example `POSTGRES_PASSWORD_FILE=/run/secrets/db_password`.
3. **A secret manager** (Vault, AWS Secrets Manager, Google Secret Manager) that the
   app or a sidecar reads at start-up, with short-lived credentials.

The example Compose file uses option 2 for Postgres.

## Check yourself

1. Why is `ENV DB_PASSWORD=...` in a Dockerfile a leak even if the repo is private?
2. How do you give `pip` a private token during a build without leaving it in the image?
3. Why should staging and production use the same image?
