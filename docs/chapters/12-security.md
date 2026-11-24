# 12. Security

Containers share the host kernel. Good defaults keep a bug in your app from
turning into control of the host.

## The image

| Practice | Why |
|---|---|
| Small base (slim, distroless) | Fewer packages = fewer CVEs and fewer tools for an attacker. |
| Pin versions, rebuild often | Repeatable builds; patched bases picked up on purpose. |
| No secrets in layers, `ENV` or `ARG` | [Chapter 9](09-configuration-and-secrets.md). |
| `.dockerignore` | Keeps `.git`, `.env` and keys out of the context. |
| Scan images | `docker scout cves IMAGE`, `trivy image IMAGE`, or your registry's scanner. Fail CI on high or critical issues that have a fix. |
| SBOM and signatures | `docker buildx build --sbom=true --provenance=true`; sign with cosign. Lets you answer "are we affected by CVE-X?" quickly. |
| Trusted bases only | Official or verified images, or your own. |

## The container at run time

| Practice | How |
|---|---|
| Run as non-root | `USER 10001` in the Dockerfile; `runAsNonRoot: true` in Kubernetes. Use a numeric id: Kubernetes can only verify "non-root" from a number, not a user name. |
| Read-only root filesystem | `--read-only` plus `--tmpfs /tmp`; write only to volumes. |
| Drop Linux capabilities | `--cap-drop ALL`, add back only what is needed (`--cap-add NET_BIND_SERVICE`). |
| No privilege escalation | `--security-opt no-new-privileges`. |
| Never `--privileged` | It turns off most isolation. Almost no app needs it. |
| Limit resources | [Chapter 11](11-resource-limits.md). |
| Publish ports narrowly | `-p 127.0.0.1:8080:8080`; databases on internal networks only. |

All of these appear in [`examples/compose.yaml`](../../examples/compose.yaml).

## The Docker socket is root

`/var/run/docker.sock` controls the engine. Anyone who can talk to it can start a
container that mounts the host's `/` and become root on the host. So:

- Do not mount `docker.sock` into containers unless you fully trust them (and think
  twice for CI runners and "dashboard" tools).
- Membership in the `docker` group is root-equivalent on Linux.
- Rootless Docker or Podman removes this risk for many dev and CI cases.

## Isolation is not a sandbox for hostile code

Plain containers are good for separating your own services. For running untrusted
code from strangers, add stronger isolation: gVisor, Kata Containers, Firecracker
microVMs, or separate VMs.

## A checklist you can run

```bash
python -m dockerhygiene.cli check Dockerfile         # root user, secrets, :latest, ...
docker run --rm -i hadolint/hadolint < Dockerfile     # Dockerfile lint
docker scout cves my-app:1.4.2                        # or: trivy image my-app:1.4.2
docker inspect -f '{{.Config.User}}' my-app:1.4.2     # empty means root
```

## Check yourself

1. Why is running as root inside a container a risk, if the container is isolated?
2. Why is mounting `docker.sock` into a container dangerous?
3. Name three run-time flags that reduce what a compromised container can do.
