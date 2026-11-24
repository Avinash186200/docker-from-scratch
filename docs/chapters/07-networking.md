# 7. Networking

## The default picture

Every container gets its own network namespace: its own interfaces, IP address
and `localhost`. **`localhost` inside a container is the container itself**, not
your laptop. This one fact explains most beginner networking bugs.

| Network driver | What it does | When |
|---|---|---|
| `bridge` (default) | A private network on the host. Containers get private IPs. Outbound traffic goes through NAT. | Most cases. |
| User-defined bridge (`docker network create app-net`) | Same, plus **DNS by container name**. | Whenever containers talk to each other. |
| `host` | The container uses the host's network directly. No isolation, no `-p` needed. | Special performance or networking cases. Native on Linux; recent Docker Desktop versions offer it only as an opt-in setting. |
| `none` | No network. | Batch jobs that must not reach anything. |
| `overlay` | Spans several hosts. | Swarm. Kubernetes uses its own networking (CNI). |

## Publishing ports

```bash
docker run -d -p 8080:80 nginx:1.27            # host 0.0.0.0:8080 -> container 80
docker run -d -p 127.0.0.1:8080:80 nginx:1.27  # only reachable from this machine
docker port <container>                        # what is published
```

`EXPOSE` in a Dockerfile does not publish anything. On a server, `-p 8080:80`
listens on all interfaces. On Linux, Docker writes its own firewall rules, which
can bypass host firewalls such as `ufw`. Bind to `127.0.0.1` when the port is only
for a local reverse proxy.

## Container to container: use names, not IPs

```bash
docker network create app-net
docker run -d --name db  --network app-net -e POSTGRES_PASSWORD=dev postgres:16-alpine
sleep 5   # give Postgres a few seconds to start
docker run --rm --network app-net postgres:16-alpine pg_isready -h db
# db:5432 - accepting connections
```

The default bridge network does **not** give you name lookup. User-defined networks
and Compose networks do. Container IPs change on restart, so never hard-code them.

## Container to host

On Docker Desktop, `host.docker.internal` resolves to your laptop. On Linux, add
`--add-host=host.docker.internal:host-gateway`.

## Debugging network problems

```bash
docker network ls
docker network inspect app-net            # which containers, which IPs
docker run --rm --network app-net alpine:3.20 nslookup db   # does the name resolve?
docker run --rm -it --network container:db nicolaka/netshoot   # tools, in db's network namespace
```

Questions to ask, in order:

1. Is the app inside listening on `0.0.0.0`, not `127.0.0.1`? (An app bound to the
   container's localhost cannot be reached through `-p`.)
2. Is the port published (`docker port`)?
3. Are both containers on the same user-defined network?
4. Is the name right (the service or container name)?

## Check yourself

1. Your app in a container connects to `localhost:5432` and fails, though Postgres
   runs in another container. Why?
2. Why do two containers on the default bridge fail to find each other by name?
3. What is the risk of `-p 5432:5432` on a cloud VM?

Next: [lab 5](../../labs/README.md#lab-5-two-containers-talk-by-name).
