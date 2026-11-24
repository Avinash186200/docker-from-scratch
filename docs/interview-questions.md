# Docker interview questions, basic to advanced

Answers are short and spoken, the way you would say them in an interview. Each
section links to the chapter with the full story.

- [Level 1: basics](#level-1-basics)
- [Level 2: building images](#level-2-building-images)
- [Level 3: storage, networking, Compose](#level-3-storage-networking-compose)
- [Level 4: running in production](#level-4-running-in-production)
- [Level 5: security](#level-5-security)
- [Level 6: internals](#level-6-internals)
- [Level 7: scenarios and troubleshooting](#level-7-scenarios-and-troubleshooting)

---

## Level 1: basics

**1. What is Docker?**
Docker packs an app with everything it needs to run into an image, and runs that
image as a container. The same image runs the same way on my laptop, in CI and on
the server. ([ch 1](chapters/01-what-is-docker-and-why.md))

**2. Image vs container?**
The image is the read-only template. The container is a running copy of it with its
own writable layer. One image, many containers. Like a class and its objects.

**3. Container vs virtual machine?**
A VM runs a full OS with its own kernel on a hypervisor. A container is just
isolated processes sharing the host kernel. So containers start in under a second
and are much smaller, but isolation is weaker than a VM.

**4. Can I run a Linux container on Windows?**
Not on the Windows kernel directly. Docker Desktop runs a small Linux VM through
WSL 2, and the containers run inside that VM.

**5. What is a registry?**
A server that stores images, like Docker Hub, GitHub Container Registry or ECR. You
push to it from CI and pull from it on servers.

**6. What does `docker run` do?**
It pulls the image if it is not local, creates a container with a writable layer,
network and mounts, and starts the image's command as a process.

**7. `docker stop` vs `docker kill`?**
Stop sends SIGTERM, waits for a grace period, then SIGKILL. Kill sends SIGKILL right
away (or another signal you pick). Stop gives the app a chance to shut down cleanly.

**8. `docker stop` vs `docker rm`?**
Stop just stops the process; the container and its files are still there and can
start again. Rm deletes the container and its writable layer.

**9. What does `-p 8080:80` mean?**
Host port 8080 forwards to port 80 in the container. Left is the host, right is the
container.

**10. `docker exec` vs `docker attach`?**
Exec starts a new process inside a running container, like a shell. Attach connects
your terminal to the main process's input and output. For debugging I use exec.

---

## Level 2: building images

**11. What is a Dockerfile?**
A text file with the steps to build an image: base image, install packages, copy
code, set user, set the start command. ([ch 4](chapters/04-writing-a-dockerfile.md))

**12. What are layers?**
Each RUN, COPY and ADD makes a layer of file changes. The image is a stack of
read-only layers, and they are shared between images. ([ch 5](chapters/05-layers-cache-and-image-size.md))

**13. How does the build cache work?**
For each step, if the instruction and its inputs are the same as before, Docker
reuses the old layer. Once one step changes, every step after it rebuilds.

**14. How do you order a Dockerfile for good caching?**
Things that change rarely go first. So: copy only the requirements file, install
dependencies, and then copy the code. Then a code change does not re-install
everything.

**15. CMD vs ENTRYPOINT?**
CMD is the default command and is replaced if you pass arguments to `docker run`.
ENTRYPOINT is the fixed program, and CMD becomes its default arguments. For apps I
use CMD; for an image that is a CLI tool I use ENTRYPOINT.

**16. Exec form vs shell form?**
Exec form is a JSON array, and the app runs as PID 1 and gets signals. Shell form
runs through `/bin/sh -c`, so the shell is PID 1 and SIGTERM does not reach the app.
I measured it: exec form stopped in 0.3 seconds with exit 0, shell form got killed
with exit 137. ([ch 14](chapters/14-production-patterns.md))

**17. COPY vs ADD?**
Both copy files. ADD also downloads URLs and unpacks local tar files. I use COPY
unless I want exactly that extra behaviour.

**18. ARG vs ENV?**
ARG exists only during the build. ENV is baked into the image and is there at run
time. Neither is safe for secrets.

**19. What is `.dockerignore` for?**
It keeps files out of the build context, like `.git`, virtual envs, data and `.env`
files. It makes builds faster and stops secrets ending up in the image.

**20. What is a multi-stage build?**
One stage has the compilers and build tools, and the final stage copies only the
built result. The tools never ship. It helps a lot for Go, Java or front-end builds.
For a pure-Python app with no compiling, it may not help at all: in this course the
multi-stage version was bigger, 224 MB against 187 MB.

**21. How do you make an image smaller?**
Pick a smaller base (slim, distroless), use multi-stage when there are build tools,
clean package caches in the same RUN, use `--no-install-recommends` and
`--no-cache-dir`, and keep the context small with `.dockerignore`. Just moving from
`python:3.11` to `python:3.11-slim` took our image from 1.6 GB to 187 MB.

**22. Why does deleting a file in a later RUN not make the image smaller?**
The file is still in the earlier layer. The new layer only hides it. You have to
delete it in the same RUN that created it.

**23. Alpine vs slim?**
Alpine is smaller but uses musl instead of glibc. Some Python and native packages
need compiling or behave differently on it. For Python I usually start with slim and
test Alpine only if size really matters.

**24. What is a dangling image?**
An image with no tag, usually an old build whose tag moved to a new build. Safe to
remove with `docker image prune`.

**25. Why not use the `latest` tag?**
It moves. The same Dockerfile can build something different next month, and in
production you cannot tell what is running or roll back cleanly. When I ran
`FROM python` in November 2026 it gave Python 3.15.2. I pin versions, and deploy by
digest or git SHA.

**26. What is BuildKit?**
The modern builder. It runs steps in parallel, and adds cache mounts, secret mounts,
SSH forwarding and multi-platform builds.

---

## Level 3: storage, networking, Compose

**27. Where does data go when a container writes a file?**
Into its writable layer. It survives stop and start, but it is gone when the
container is removed. ([ch 6](chapters/06-storage-volumes-and-bind-mounts.md))

**28. Volume vs bind mount?**
A volume is managed by Docker and is the right place for database data. A bind mount
maps a host folder in, which is good for live code editing in development. Bind
mounts are slower on Docker Desktop because files cross the VM boundary.

**29. Named vs anonymous volume?**
A named volume has a name I chose and is easy to find and reuse. An anonymous volume
gets a random hash name, often from a VOLUME line in the image. They pile up: on my
laptop 260 of 270 volumes were anonymous leftovers.

**30. What changed in `docker volume prune` in Docker 23?**
It now removes only anonymous volumes. To remove unused named volumes too you need
`-a`. That is safer, because named volumes usually hold databases.

**31. How do two containers talk to each other?**
Put them on the same user-defined network and use the container or service name as
the host name. Docker's DNS resolves it. ([ch 7](chapters/07-networking.md))

**32. Why does `localhost` not work between containers?**
Each container has its own network namespace, so `localhost` is the container itself.
You use the other container's name instead.

**33. Default bridge vs user-defined bridge?**
The user-defined bridge gives DNS by name and better isolation. The default bridge
has no name lookup.

**34. How does a container reach a service on my laptop?**
On Docker Desktop, `host.docker.internal`. On Linux, add
`--add-host=host.docker.internal:host-gateway`.

**35. What is Docker Compose?**
A YAML file that describes several services, their networks, volumes and secrets,
so one command starts the whole app. ([ch 8](chapters/08-docker-compose.md))

**36. `docker compose down` vs `down -v`?**
Down removes containers and networks but keeps volumes. Down `-v` also deletes the
named volumes, so the data is gone.

**37. Does `depends_on` wait for the database to be ready?**
Plain `depends_on` only waits for the container to start. With
`condition: service_healthy` it waits for the healthcheck. The app should still retry
connections.

**38. What is the Compose project name and why does it matter?**
It prefixes every container, network and volume, and it defaults to the folder name.
Rename the folder and you silently get a new empty set of volumes. I set `name:` in
the file to keep it stable.

---

## Level 4: running in production

**39. What happens when a container hits its memory limit?**
The kernel OOM killer kills it. Exit code 137, and `docker inspect` shows
`OOMKilled: true`. ([ch 11](chapters/11-resource-limits.md))

**40. And the CPU limit?**
It gets throttled, not killed. The app just slows down.

**41. What does exit code 137 mean?**
128 plus 9, so SIGKILL. Either out of memory, or `docker stop` timed out because the
app ignored SIGTERM. I check `OOMKilled` in inspect to tell them apart.

**42. Why is PID 1 special?**
Linux ignores signals for PID 1 unless the process installed a handler. So an app
running as PID 1 with no SIGTERM handler will not stop on `docker stop` and gets
killed after the timeout. PID 1 also has to reap zombie processes.

**43. What does `docker run --init` do?**
It adds a tiny init, tini, as PID 1. It forwards signals to the app and reaps
zombies. Useful when the app cannot handle signals itself.

**44. HEALTHCHECK: what is it and does Kubernetes use it?**
A command Docker runs to mark the container healthy or unhealthy. Compose can wait
on it. Kubernetes ignores it and uses its own liveness, readiness and startup probes.

**45. Liveness vs readiness?**
Liveness asks "is it stuck, should I restart it?" Readiness asks "can it take traffic
now?" A liveness check should not depend on the database, or a database blip
restarts every pod.

**46. Restart policies?**
`no`, `on-failure`, `unless-stopped` and `always`. For a service on one host I use
`unless-stopped`.

**47. How do you handle config across environments?**
Same image everywhere, and config comes in at run time through environment
variables or mounted files. If staging and prod run different images, you did not
test what you ship.

**48. How do you tag images in CI?**
Every build gets the git SHA, which never changes. Releases get a version tag that I
never re-push. I deploy by SHA or digest, never by `latest`.
([ch 13](chapters/13-ci-cd-and-tagging.md))

**49. Why not rebuild the image for production after testing?**
A rebuild can pull a newer base or newer dependencies, so production would run
something you never tested. Build once and promote the same digest.

**50. How do you speed up Docker builds in CI?**
Order the Dockerfile for caching, and keep the cache between runs with
`cache-from` / `cache-to`, for example the GitHub Actions cache, or a registry cache.

**51. What is a multi-platform image?**
One tag that holds builds for several CPU types, like amd64 and arm64. Built with
`docker buildx build --platform`. Without it, an arm64 image on an amd64 server
gives `exec format error`.

**52. Where should container logs go?**
To stdout and stderr. Docker collects them and the platform ships them on. And set a
log size limit, because by default the json-file driver can grow without limit.

**53. Compose vs Kubernetes?**
Compose is great for one machine. Kubernetes runs across many machines with rolling
updates, autoscaling and self-healing, at the cost of much more complexity.
([ch 15](chapters/15-orchestration.md))

**54. Does Kubernetes still use Docker?**
Kubernetes removed its Docker Engine adapter, dockershim, in 1.24 and uses
containerd or CRI-O. But images built by Docker are OCI images, so they run
unchanged.

---

## Level 5: security

**55. Why run as non-root inside a container?**
If the app is hacked, the attacker is root inside the container. Root inside plus a
kernel bug or a bad mount can mean root on the host. A normal user limits the damage.
([ch 12](chapters/12-security.md))

**56. How do you handle secrets?**
Never in the Dockerfile, ENV, ARG or a copied file, because anyone with the image can
read them. At build time I use BuildKit secret mounts. At run time, secret files or a
secret manager. ([ch 9](chapters/09-configuration-and-secrets.md))

**57. How can you see a secret someone baked into an image?**
`docker history --no-trunc` shows the build commands, and `docker inspect` shows the
ENV values. In lab 3, the API key is right there in `docker inspect`.

**58. Why is mounting `docker.sock` dangerous?**
Whoever can talk to the socket can start a container that mounts the host root
filesystem, so it is the same as root on the host.

**59. What hardening flags do you use?**
Non-root user, `--read-only` with a tmpfs for `/tmp`, `--cap-drop ALL`,
`--security-opt no-new-privileges`, resource limits, and never `--privileged`.

**60. How do you scan images?**
`docker scout` or `trivy` in CI, and fail the build on high or critical CVEs that
have a fix. Small bases mean far fewer findings.

**61. Is a container a good sandbox for untrusted code?**
Not on its own, because the kernel is shared. For untrusted code I would add gVisor,
Kata or Firecracker, or use separate VMs.

---

## Level 6: internals

**62. How are containers built on Linux?**
Namespaces give each container its own view (PID, network, mounts, hostname, users).
Cgroups limit CPU, memory and PIDs. A union filesystem, overlayfs, stacks the image
layers with a writable layer. ([ch 17](chapters/17-how-docker-works-inside.md))

**63. What are containerd and runc?**
containerd manages images and the container lifecycle. runc is the low-level runtime
that actually creates the container with namespaces and cgroups. dockerd sits on top
and handles the API, networks, volumes and builds.

**64. What is OCI?**
The Open Container Initiative: open standards for the image format, the runtime and
the registry API. That is why Docker, Podman and Kubernetes can share images.

**65. What is copy-on-write?**
Image layers are read-only. When a container changes a file, the file is first copied
up into its writable layer and changed there. The image stays untouched.

**66. How does Docker Desktop work on Windows?**
It runs a Linux VM through WSL 2. The engine and the containers run in it, and all
the data lives in one virtual disk file on the host drive. That file grows as you use
Docker and does not shrink by itself.

---

## Level 7: scenarios and troubleshooting

**67. A container exits right after it starts. What do you do?**
`docker logs` first. Then check the exit code with `docker inspect`. Common causes:
the command finishes right away (it is not a server), a missing env var, or the
wrong command. To look inside, run the image with `--entrypoint sh`.
([ch 10](chapters/10-logs-debugging-and-troubleshooting.md))

**68. The app works locally but I can't reach it through `-p`. Why?**
Usually the app listens on `127.0.0.1` inside the container. It must listen on
`0.0.0.0`. Then I check the port is published, with `docker port`.

**69. Builds are slow every time. Why?**
The cache breaks early, usually `COPY . .` before the dependency install. In CI it is
often because the cache is not kept between runs.

**70. A container keeps restarting with exit code 137.**
Two suspects: the memory limit, so I check `OOMKilled`, and `docker stats` for memory
growth; or a stop timeout when something is stopping it. If it is OOM, I raise the
limit or fix the leak, and tell the runtime its memory size.

**71. "No space left on device". How do you clean up safely?**
`docker system df` first. Remove stopped containers first, because they keep images
and volumes marked as in use. Then build cache, then images, then volumes. Before
any named volume, I check it is not the only copy of real data. On Docker Desktop I
then compact the virtual disk, after `fstrim`, or the host never gets the space
back. ([ch 16](chapters/16-disk-space-and-cleanup.md))

**72. Tell me about a Docker problem you solved.**
"My laptop's C: drive got down to 0.2 GB free and even PowerShell could not start.
Docker was using 133 GB but was broken: every command gave an input/output error,
because its virtual disk could not grow and Linux had made it read-only. I freed
safe caches first, restarted Docker and WSL so the disk was healthy, and checked
what was inside: 55 stopped containers, 260 anonymous volumes, one stack under three
project names, and 63 GB of build cache. After checking no named volume was the only
copy of real data, I pruned everything. The disk file was still 130 GB, because it
does not shrink by itself. Compacting took it to 68 GB. With fstrim first, it went
to 3.8 GB. C: went from 0.2 GB to 159 GB free." ([ch 18](chapters/18-case-study-disk-full.md))

**73. Docker says "input/output error" on every command. What now?**
It is the Docker disk, not my containers. I check host disk space first, then
restart Docker and WSL, and check inside the VM that the disk is mounted read-write
and the kernel log has no new I/O errors. Only then do I prune. If the errors come
back, I use Docker Desktop's Clean / Purge data and rebuild, instead of working on a
damaged filesystem.

**74. `docker system prune -a` ran on Windows, but C: has the same free space. Why?**
Prune frees space inside the VM's virtual disk. The `.vhdx` file on the host keeps
its size until you trim and compact it.

**75. A teammate's image works on their Mac and fails on the server with "exec format error".**
Their Mac is arm64 and the server is amd64. Build a multi-platform image with buildx,
or build for `--platform linux/amd64`.

**76. How would you cut a 1.5 GB image down?**
Look at `docker history` to find the big layers. Usually: switch to a slim base,
move build tools into a build stage, clean caches in the same RUN, and add a
`.dockerignore`. Then measure again; do not assume.

**77. Your container takes exactly the full grace period to stop. Why?**
SIGTERM is not reaching the app or not being handled. Either shell-form CMD, or the
app is PID 1 with no SIGTERM handler. Fix with exec form and a handler, or
`--init`.

**78. How do you keep a dev machine from filling up again?**
Use `--rm` for one-off runs, name volumes and set fixed Compose project names, set
log limits and a build cache budget, move the Docker disk off the system drive, cap
its size, and check `docker system df` every week.
