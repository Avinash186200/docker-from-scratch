# 8. Docker Compose

Compose describes a multi-container app in one YAML file: services, networks,
volumes, secrets. One command starts all of it.

## The example file

[`examples/compose.yaml`](../../examples/compose.yaml) runs the app, and Postgres
under a profile. Shortened here (the db's volume, secret and logging are in the
full file):

```yaml
name: hello
services:
  app:
    build: .
    image: hello-app:1.0
    ports: ["127.0.0.1:8080:8080"]
    volumes: ["app-data:/data"]
    read_only: true
    tmpfs: ["/tmp"]
    cap_drop: [ALL]
    deploy:
      resources:
        limits: { cpus: "0.50", memory: 128M }
    restart: unless-stopped
    logging:
      driver: json-file
      options: { max-size: "10m", max-file: "3" }
  db:
    profiles: [db]
    image: postgres:16-alpine
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
volumes:
  app-data:
  db-data:
```

## Commands

```bash
docker compose up -d --build      # build if needed, start in background
docker compose ps
docker compose logs -f app
docker compose exec app sh
docker compose --profile db up -d # also start services in the 'db' profile
docker compose config             # print the final merged file: great for debugging
docker compose down               # stop + remove containers and networks; KEEPS volumes
docker compose down -v            # ALSO removes the named volumes: data loss
```

## Things that bite people

### Project names prefix everything

Compose prefixes everything with the project name: volumes and networks are
`<project>_<name>`, containers are `<project>-<service>-<n>`. The project name
defaults to the **folder name**. Rename or copy the folder and you get a new set of containers,
networks and **volumes**; the old ones stay behind. In the
[case study](18-case-study-disk-full.md), one stack existed under three project
names (old folder, new folder, a review copy), so its databases were on disk three
times. Set `name:` at the top of the file to make the project name stable.

### `depends_on` does not wait for "ready"

```yaml
services:
  app:
    depends_on:
      db:
        condition: service_healthy   # wait for the db healthcheck to pass
```

Plain `depends_on: [db]` only waits for the container to *start*. The app should
still retry its connection: in production nothing guarantees start order.

### Environment and `.env`

- `environment:` sets variables in the container.
- A `.env` file next to `compose.yaml` fills `${VARS}` in the YAML itself.
- `env_file:` loads a file into the container's environment.
- Keep `.env` out of git; commit a `.env.example`.

### Override files

`compose.override.yaml` is merged automatically. Use it for dev-only settings (bind
mounts for live reload, debug ports) and keep the base file close to production.
`docker compose -f compose.yaml -f compose.prod.yaml up` merges explicit files.

## Compose in production?

Fine for a single server with a few services. For many servers, rolling deploys,
autoscaling or self-healing across machines, use an orchestrator
([chapter 15](15-orchestration.md)).

## Check yourself

1. What is the difference between `docker compose down` and `docker compose down -v`?
2. You renamed the project folder and your database looks empty. What happened, and
   is the data lost?
3. Why is `condition: service_healthy` better than a plain `depends_on`?

Next: [lab 6](../../labs/README.md#lab-6-compose-with-a-database).
