# 11. Resource limits

By default a container can use all the CPU and memory of the host (or of the
Docker Desktop VM). One leaking container can starve everything else. Limits use
Linux **cgroups** ([chapter 17](17-how-docker-works-inside.md)).

## Memory

```bash
docker run -d --memory 256m --memory-swap 256m my-app:1.4.2
```

- Above the limit, the kernel's OOM killer kills a process in the container. The
  container exits with **137** and `docker inspect` shows `"OOMKilled": true`.
- `--memory-swap` equal to `--memory` means no swap: fail fast instead of crawling.
- Runtimes need to know their limit. Modern JVMs read the cgroup limit. Python does
  not size itself to it, and Node's behaviour depends on the version, so set worker
  counts and heap sizes (`--max-old-space-size` for Node) on purpose.

## CPU

```bash
docker run -d --cpus 1.5 my-app:1.4.2        # at most 1.5 CPUs of time
docker run -d --cpuset-cpus 0,1 my-app:1.4.2 # pin to specific cores
```

CPU over the limit is **throttled**, not killed: the app just gets slower. Watch
`docker stats` and throttling metrics if latency goes up for no clear reason.

## Other limits worth knowing

| Flag | Protects against |
|---|---|
| `--pids-limit 200` | Fork bombs, thread leaks. |
| `--ulimit nofile=65536:65536` | Too few file handles for busy servers. |
| `--storage-opt size=10G` | Writable layer growth (only some storage drivers support it). |
| Log `max-size` / `max-file` | Logs filling the disk ([chapter 10](10-logs-debugging-and-troubleshooting.md)). |

## In Compose and Kubernetes

```yaml
# compose
deploy:
  resources:
    limits: { cpus: "0.50", memory: 128M }
```

```yaml
# kubernetes
resources:
  requests: { cpu: "250m", memory: "128Mi" }   # what the scheduler reserves
  limits:   { cpu: "500m", memory: "256Mi" }   # the hard cap
```

## Docker Desktop has its own limits too

On Windows and macOS, all containers share the VM's CPU, memory and **disk**
budget, set in Docker Desktop settings (or `.wslconfig` for the WSL 2 VM). The
VM's disk is a single file on your host drive, and it grows as you pull and build
([chapter 16](16-disk-space-and-cleanup.md)).

## Check yourself

1. What happens when a container goes over its memory limit, and how do you prove it?
2. What happens when it goes over its CPU limit?
3. Why should you tell a Node or Python app how much memory it has?

Next: [lab 7](../../labs/README.md#lab-7-signals-and-memory-limits).
