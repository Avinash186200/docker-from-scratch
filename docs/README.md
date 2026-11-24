# Course map

Read in order if you are new. Jump to a chapter if you know the basics. Each
chapter ends with "Check yourself" questions; the answers are in the
[interview questions](interview-questions.md).

## Part 1: basics (day 1)

| # | Chapter | You will be able to |
|---|---|---|
| 1 | [What Docker is, and why](chapters/01-what-is-docker-and-why.md) | Explain images, containers, registries, and containers vs VMs |
| 2 | [Install and first container](chapters/02-install-and-first-container.md) | Run, inspect, stop and remove containers |
| 3 | [Images, tags, digests, registries](chapters/03-images-and-registries.md) | Pull, tag, push; know why tags move |

## Part 2: building images (day 2)

| # | Chapter | You will be able to |
|---|---|---|
| 4 | [Writing a Dockerfile](chapters/04-writing-a-dockerfile.md) | Write a clean Dockerfile; CMD vs ENTRYPOINT; `.dockerignore` |
| 5 | [Layers, cache and image size](chapters/05-layers-cache-and-image-size.md) | Make builds fast and images small; multi-stage |

## Part 3: running real apps (day 3)

| # | Chapter | You will be able to |
|---|---|---|
| 6 | [Storage: volumes and bind mounts](chapters/06-storage-volumes-and-bind-mounts.md) | Keep data safe; avoid volume pile-up |
| 7 | [Networking](chapters/07-networking.md) | Connect containers by name; publish ports safely |
| 8 | [Docker Compose](chapters/08-docker-compose.md) | Run a multi-service app; avoid `down -v` and project-name traps |
| 9 | [Configuration and secrets](chapters/09-configuration-and-secrets.md) | Configure at run time; keep secrets out of images |
| 10 | [Logs, debugging, troubleshooting](chapters/10-logs-debugging-and-troubleshooting.md) | Find why a container died; read exit codes |

## Part 4: production (day 4)

| # | Chapter | You will be able to |
|---|---|---|
| 11 | [Resource limits](chapters/11-resource-limits.md) | Set memory/CPU limits; recognise OOM kills |
| 12 | [Security](chapters/12-security.md) | Harden images and containers |
| 13 | [CI/CD and tagging](chapters/13-ci-cd-and-tagging.md) | Build once, promote by digest; cache in CI |
| 14 | [Production patterns](chapters/14-production-patterns.md) | Handle signals, health checks, restarts |
| 15 | [Orchestration](chapters/15-orchestration.md) | Choose between Compose, Kubernetes and serverless |

## Part 5: operations and internals (day 5)

| # | Chapter | You will be able to |
|---|---|---|
| 16 | [Disk space and cleanup](chapters/16-disk-space-and-cleanup.md) | Measure, clean safely, shrink Docker Desktop's disk |
| 17 | [How Docker works inside](chapters/17-how-docker-works-inside.md) | Explain namespaces, cgroups, overlayfs, containerd, OCI |
| 18 | [Case study: Docker filled my C: drive](chapters/18-case-study-disk-full.md) | Walk through a real incident end to end |

## Also

- [Labs](../labs/README.md): 8 hands-on exercises.
- [Interview questions](interview-questions.md): 78 questions, basic to advanced.
- [Cheatsheet](cheatsheet.md): the commands on one page.
