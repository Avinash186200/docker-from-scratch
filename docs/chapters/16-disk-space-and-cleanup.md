# 16. Disk space and cleanup

Docker never deletes anything on its own except build cache under a GC policy.
Images, stopped containers, volumes and logs stay until you remove them. On a busy
dev laptop this adds up to tens or hundreds of GB.
The [case study](18-case-study-disk-full.md) is a real example: 148.7 GB.

## Where the bytes live

| Setup | Location |
|---|---|
| Linux (Docker Engine) | `/var/lib/docker` (images, containers, volumes, logs under `containers/<id>/<id>-json.log`) |
| Windows (Docker Desktop, WSL 2) | A virtual disk file, `docker_data.vhdx`, under `%LOCALAPPDATA%\Docker\wsl\` (exact folder depends on the version) |
| macOS (Docker Desktop) | A disk image file inside Docker Desktop's data folder (`Docker.raw`) |

On Windows and macOS everything is inside **one big file** on your host drive.

## Step 1: measure

```bash
docker system df          # images, containers, volumes, build cache
docker system df -v       # per image / container / volume
docker ps -a --filter status=exited
docker volume ls -q -f dangling=true | wc -l
```

Or let the repo's helper read it and suggest an order:

```bash
docker system df | python -m dockerhygiene.cli df
```

Read the RECLAIMABLE column with care. **Stopped containers keep their images and
volumes "in use"**, so reclaimable looks small until the containers are gone. In
the case study, images showed 23 GB reclaimable out of 56.5 GB; after removing 55
stopped containers, `image prune -a` reclaimed 44.08 GB.

## Step 2: clean, safest first

| Command | Deletes | Risk |
|---|---|---|
| `docker container prune` | Stopped containers and their writable layers | Low, unless you kept files inside a stopped container. |
| `docker image prune` | Dangling images (no tag) | Low. |
| `docker builder prune` | Build cache | None for correctness; next builds are slower. Keep a budget: `--max-used-space 20GB` (older versions: `--keep-storage`). |
| `docker image prune -a` | Every image not used by a container | Medium: you must pull or rebuild them. |
| `docker volume prune` | Unused **anonymous** volumes (Docker 23+) | Low to medium. |
| `docker volume prune -a` | Unused volumes, **named ones too** | High: this is where databases live. Check first. |
| `docker system prune` | Stopped containers, unused networks, dangling images, build cache | Low. Add `-a` for all unused images, `--volumes` for anonymous volumes. |

Useful filters: `--filter until=168h` (older than 7 days) works for containers,
images, networks and build cache; `volume prune` only accepts `label` filters.

**Watch out for databases started without a named volume.** Images like `postgres`
declare a `VOLUME`, so `docker run postgres` without `-v` stores its data in an
anonymous volume. Once that container is removed, `docker volume prune` deletes the
data. Name the volumes you care about.

Before deleting named volumes, ask: is this data anywhere else? Local dev databases
usually are not backed up. If you need one, dump it first
([chapter 6](06-storage-volumes-and-bind-mounts.md)).

The repo has a script that shows the plan and only deletes with `--yes`:

```bash
scripts/docker-cleanup.sh              # dry run: shows what each level would remove
scripts/docker-cleanup.sh --level safe --yes
```

## Step 3 (Docker Desktop only): give the space back to the host

Pruning frees space **inside** the VM's disk. The `.vhdx` / `.raw` file on your host
does not shrink by itself. On Windows, what worked in the case study:

1. Keep Docker Desktop running, and tell the Linux filesystem which blocks are free:

   ```bash
   # Git Bash needs MSYS_NO_PATHCONV=1 so it does not rewrite the Linux path
   MSYS_NO_PATHCONV=1 wsl -d docker-desktop -- df -h /mnt/docker-desktop-disk   # check the path first
   MSYS_NO_PATHCONV=1 wsl -d docker-desktop -- fstrim -v /mnt/docker-desktop-disk
   ```

2. Quit Docker Desktop, then `wsl --shutdown`.
3. Compact the file from an **admin** PowerShell:
   [`scripts/shrink-docker-vhdx.ps1`](../../scripts/shrink-docker-vhdx.ps1). It uses
   `Optimize-VHD` when the Hyper-V module is installed (Windows Pro and up), and
   `diskpart` (`compact vdisk`) otherwise.

Measured in the case study: compacting **without** step 1 took the file from
129.8 GB to 68.1 GB. After `fstrim`, the same compaction took it to **3.8 GB**.

Docker Desktop also has **Troubleshoot → Clean / Purge data**, which deletes
everything and starts a fresh small disk. Use it when the disk is damaged.

## Step 4: stop it from growing back

| Habit | How |
|---|---|
| Throwaway runs leave nothing behind | `docker run --rm ...` |
| Log size limits | `daemon.json` `log-opts` (see [`examples/daemon.json`](../../examples/daemon.json)) or per service in Compose |
| Build cache budget | `builder.gc` in `daemon.json`, plus a periodic `docker builder prune --max-used-space 20GB` |
| Stable Compose project names | `name:` in `compose.yaml` ([chapter 8](08-docker-compose.md)) |
| Avoid anonymous volumes | Name every volume you mean to keep; use `--rm` (it also removes the container's anonymous volumes) |
| Put the disk where there is room | Docker Desktop: Settings → Resources → Advanced → disk image location, on a bigger drive |
| Cap the disk | Docker Desktop: set the virtual disk limit, so Docker fails before the host drive fills |
| Look regularly | `docker system df` once a week, or a scheduled `scripts/docker-disk-report.sh` |

## Check yourself

1. You ran `docker system prune -a` on Windows and C: has the same free space. Why?
2. Why might `docker volume prune` free almost nothing on Docker 23+?
3. What does `fstrim` do, and why did it change the compaction result from 68 GB to 3.8 GB?

Next: [lab 8](../../labs/README.md#lab-8-cleanup-drill).
