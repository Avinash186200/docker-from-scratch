# 3. Images, tags, digests and registries

## How an image name is built

```
registry.example.com:5000 / team / my-app : 1.4.2 @sha256:3f1c...
└────────── registry ───┘   └ namespace/repo ┘  tag      digest
```

- **Registry**: left out means Docker Hub (`docker.io`).
- **Namespace/repository**: on Docker Hub, official images have no namespace
  (`python`, `nginx`, `postgres`).
- **Tag**: a human label. Left out means `latest`.
- **Digest**: the SHA-256 of the image manifest. It never changes.

## Tags move, digests do not

A tag is a pointer that the publisher can move. `python:3.11-slim` today is not
the same bytes as `python:3.11-slim` next month (security patches get rebuilt
under the same tag). `latest` is just a tag that usually points at the newest
release; it is not special and not guaranteed to be newest.

A real example: when lab 3 in this course ran in November 2026, `FROM python`
(no tag, so `latest`) gave **Python 3.15.2**. A Dockerfile written a year earlier
with the same line gets a different Python version without anyone changing a file.

| Use | Pin to |
|---|---|
| Learning, local tinkering | A version tag: `python:3.11-slim` |
| Dockerfiles you commit | At least a minor version tag; the digest if you need repeatable builds |
| Production deploys | The exact image you tested, by digest or an immutable tag (git SHA) |

```bash
docker pull python:3.11-slim
docker image inspect python:3.11-slim --format '{{index .RepoDigests 0}}'
# python@sha256:...   <- put this in FROM for a fully repeatable build
```

Tools like Dependabot or Renovate can bump pinned digests for you, so pinning does
not mean never patching.

## Working with images

```bash
docker images                     # list local images (docker image ls)
docker image inspect nginx:1.27   # full metadata: env, cmd, user, layers, ports
docker history nginx:1.27         # the layers and the instruction that made each
docker tag my-app:dev registry.example.com/team/my-app:1.4.2
docker login registry.example.com
docker push registry.example.com/team/my-app:1.4.2
docker rmi my-app:dev             # remove a tag (and the image if no tags are left)
docker save -o my-app.tar my-app:1.4.2   # export for an offline machine
docker load -i my-app.tar
```

## Dangling vs unused images

- **Dangling**: has no tag (`<none>:<none>`). Usually an old build whose tag moved
  to a newer build. Safe to delete: `docker image prune`.
- **Unused**: tagged, but no container (running or stopped) uses it.
  `docker image prune -a` deletes these too. You will have to pull or rebuild them.

## Choosing a registry

| Registry | Good for |
|---|---|
| Docker Hub | Public images, official base images. Note the pull rate limits for anonymous users. |
| GitHub Container Registry (ghcr.io) | Images built by GitHub Actions next to the code. |
| Cloud registries (ECR, Artifact Registry, ACR) | Images deployed to that cloud; IAM-based access, scanning built in. |
| Self-hosted (Harbor, `registry:2`) | Air-gapped or strict data-residency setups. |

## Official, verified and random images

Prefer Docker Official Images and Verified Publisher images for bases. A random
image from the internet is someone else's code running in your environment: read
its Dockerfile or build your own.

## Check yourself

1. Why can two pulls of `python:3.11-slim` a month apart give different images?
2. What is a dangling image, and how is it different from an unused image?
3. What would you deploy to production: a tag or a digest? Why?
