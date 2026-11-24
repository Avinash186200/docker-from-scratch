# 14. Production patterns

## One main process per container

A container lives as long as its PID 1 lives. Put one service in each container
(web app, worker, database), and scale and restart them separately. If you truly
need several processes, use a small init or supervisor, and know why.

## PID 1 and signals

`docker stop` sends **SIGTERM**, waits for a grace period, then sends **SIGKILL**.
Your app should catch SIGTERM, finish in-flight requests, close connections and
exit.

Two traps:

1. **Shell form** (`CMD python server.py`) makes `/bin/sh -c` PID 1. The shell does
   not forward SIGTERM to your app.
2. **PID 1 is special in Linux.** Signals with no handler installed are ignored for
   PID 1. An app that never installs a SIGTERM handler will not stop on SIGTERM when
   it is PID 1, even in exec form.

What we measured with [`examples/app/server.py`](../../examples/app/server.py),
which installs a SIGTERM handler (Docker Desktop 4.90.0, engine 29.7.2):

| CMD form | `docker stop` took | Exit code | What happened |
|---|---|---|---|
| Exec form `["python", "server.py"]` | 0.3 s | 0 | App got SIGTERM, logged "got signal 15, shutting down", exited cleanly. |
| Shell form `python server.py` | 3.3 s (default timeout on this engine) | 137 | SIGTERM went to `/bin/sh`; app was SIGKILLed. |
| Shell form, `docker stop -t 10` | 10.3 s | 137 | Same, just a longer wait. |

Docker's documented default grace period is 10 seconds; on this engine the default
stop took about 3 seconds. Do not rely on the default: set it on purpose
(`docker run --stop-timeout 30`, Compose `stop_grace_period: 30s`, Kubernetes
`terminationGracePeriodSeconds`).

Fixes, best first: use exec form and handle SIGTERM in the app; if a shell script
must run first, end it with `exec "$@"`; if the app cannot handle signals, run with
`docker run --init` (adds a tiny init, `tini`, as PID 1 that forwards signals and
reaps zombie processes).

Reproduce it in [lab 7](../../labs/README.md#lab-7-signals-and-memory-limits).

## Health checks

- **Liveness**: is the process stuck? Restart it.
- **Readiness**: can it take traffic now? Do not send requests yet.

Docker's `HEALTHCHECK` gives one status (`healthy` / `unhealthy`). Compose can wait
on it (`service_healthy`). Kubernetes ignores the Dockerfile `HEALTHCHECK` and uses
its own `livenessProbe` / `readinessProbe` / `startupProbe`. Keep health endpoints
cheap, and do not make liveness depend on the database: a database blip would
restart every app container at once.

## Restart policies

| Policy | Behaviour |
|---|---|
| `no` (default) | Never restart. |
| `on-failure[:N]` | Restart on non-zero exit, optionally at most N times. |
| `unless-stopped` | Always restart, except after you stopped it by hand. |
| `always` | Always restart, even after a manual stop once the engine restarts. |

## Stateless containers

Treat containers as replaceable. Keep state in databases, object storage or volumes
with backups. Then a deploy is "start new, check health, stop old", and a crash is
"start another one".

## Twelve-factor habits that matter most in containers

- Config from the environment ([chapter 9](09-configuration-and-secrets.md)).
- Logs to stdout ([chapter 10](10-logs-debugging-and-troubleshooting.md)).
- Fast start-up and graceful shutdown (this chapter).
- Same image in every environment ([chapter 13](13-ci-cd-and-tagging.md)).

## Check yourself

1. Your container always takes the full grace period to stop. Give two causes.
2. What does `docker run --init` add, and when do you need it?
3. Why should a liveness check not call the database?
