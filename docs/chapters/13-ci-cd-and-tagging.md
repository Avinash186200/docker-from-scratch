# 13. Docker in CI/CD

## Build once, promote the same image

```mermaid
flowchart LR
  A[git push] --> B[build image<br/>tag = git SHA]
  B --> C[lint + unit tests<br/>inside the image]
  C --> D[scan for CVEs]
  D --> E[push to registry]
  E --> F[deploy to staging<br/>by digest]
  F --> G[smoke tests]
  G --> H[promote the SAME digest<br/>to production]
```

The image that passed the tests is the image that ships. Do not rebuild for
production: a rebuild can pull a different base or different dependencies.

## Tagging strategy

| Tag | Use |
|---|---|
| `my-app:3f9c2ab` (git SHA) | Every build. Immutable. Deploy by this or by digest. |
| `my-app:1.4.2` | Releases. Never re-push an existing version tag. |
| `my-app:main` / `my-app:latest` | Convenience pointers for humans. Never deploy by them: you cannot tell what is running or roll back cleanly. |

Turn on tag immutability in the registry if it supports it.

## A GitHub Actions example

```yaml
name: image
on: { push: { branches: [main] } }
permissions: { contents: read, packages: write }
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: docker/build-push-action@v6
        with:
          context: .
          push: true
          tags: ghcr.io/${{ github.repository }}:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

`cache-from` / `cache-to` keep the layer cache between CI runs, which are otherwise
fresh machines with an empty cache.

This repo's own [CI](../../.github/workflows/ci.yml) builds the example image,
runs it, checks `/health`, checks that it runs as a non-root user, and lints every
Dockerfile and script.

## Multi-platform images

Laptops are often arm64 (Apple silicon); servers are often amd64. One tag can hold
both:

```bash
docker buildx build --platform linux/amd64,linux/arm64 -t ghcr.io/team/app:1.4.2 --push .
```

If you see `exec format error`, the image does not match the machine's CPU.

## Testing images, not just code

- Run unit tests inside the built image, so the test environment is the run environment.
- Add a smoke test: start the container, wait for health, call one endpoint.
- Check properties: non-root user, no shell in distroless, expected size range.

## Keep CI machines clean

Self-hosted runners fill up just like laptops. Schedule `docker system prune` with
filters (for example `--filter until=72h`) and keep a build cache budget
([chapter 16](16-disk-space-and-cleanup.md)).

## Check yourself

1. Why should you not rebuild the image for production after testing it?
2. What is wrong with deploying `my-app:latest`?
3. What does `cache-from: type=gha` fix?
