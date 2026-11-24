# 15. Beyond one machine: orchestration

Docker runs containers on one host. An **orchestrator** runs them across many
hosts and keeps them in the state you asked for: N copies, healthy, updated
gradually, restarted or moved when a machine dies.

## Options

| Option | Good for | Cost |
|---|---|---|
| Docker Compose on one VM | Small apps, internal tools, demos | No self-healing across machines; deploys are manual or scripted. |
| Docker Swarm | Simple multi-host with Compose-like files | Smaller ecosystem; fewer teams choose it today. |
| Kubernetes (self-managed or EKS/GKE/AKS) | Many services, autoscaling, strong ecosystem | Steep learning curve, real operating effort. |
| Serverless containers (Cloud Run, AWS Fargate/ECS, Azure Container Apps) | Stateless HTTP services and jobs without managing nodes | Less control; platform limits; cost per request at high volume. |

Pick the simplest one that meets your availability and scaling needs.

## Docker concepts in Kubernetes words

| Docker / Compose | Kubernetes |
|---|---|
| Container | Container, always inside a **Pod** (one or more containers sharing network and volumes) |
| `docker run` with N copies | **Deployment** (keeps N replicas, rolling updates) |
| Published port / Compose service name | **Service** (stable name and IP, load-balances to Pods) |
| Reverse proxy in front | **Ingress** / Gateway |
| `-e` / `env_file` | **ConfigMap** |
| Compose `secrets:` | **Secret** (base64 by default, not encrypted: enable encryption at rest or use an external secret store) |
| Named volume | **PersistentVolumeClaim** |
| `HEALTHCHECK` | `livenessProbe`, `readinessProbe`, `startupProbe` |
| `--memory`, `--cpus` | `resources.requests` and `resources.limits` |
| `--restart` | Built in: the controller replaces failed Pods |

## Does Kubernetes still use Docker?

Kubernetes runs containers through a container runtime that speaks the CRI
interface, usually **containerd** or CRI-O. Kubernetes removed its built-in Docker
Engine adapter ("dockershim") in version 1.24. Images built with Docker are OCI
images, so they run unchanged. You still use Docker (or another builder) to build
them.

## Check yourself

1. What does an orchestrator do that Docker on one machine does not?
2. What is a Pod, and why is it not the same as a container?
3. Do images built with Docker still run on Kubernetes after dockershim was removed? Why?
