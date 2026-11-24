# Labs

Hands-on exercises, in course order. Run them from the repo root. Each takes 5 to
15 minutes. Clean up at the end of each lab so you do not grow your own disk
problem ([chapter 16](../docs/chapters/16-disk-space-and-cleanup.md)).

| Lab | Goes with |
|---|---|
| [1. First containers](#lab-1-first-containers) | Chapter 2 |
| [2. Build your own image](#lab-2-build-your-own-image) | Chapters 4-5 |
| [3. Fix a bad Dockerfile](#lab-3-fix-a-bad-dockerfile) | Chapters 4, 5, 9, 12 |
| [4. Volumes keep data](#lab-4-volumes-keep-data) | Chapter 6 |
| [5. Two containers talk by name](#lab-5-two-containers-talk-by-name) | Chapter 7 |
| [6. Compose with a database](#lab-6-compose-with-a-database) | Chapter 8 |
| [7. Signals and memory limits](#lab-7-signals-and-memory-limits) | Chapters 11, 14 |
| [8. Cleanup drill](#lab-8-cleanup-drill) | Chapter 16 |

---

## Lab 1: first containers

```bash
docker run -d --name web -p 127.0.0.1:8080:80 nginx:1.27
curl -s http://127.0.0.1:8080 | head -5
docker ps
docker logs web
docker exec -it web sh -c 'cat /etc/os-release | head -2'
docker stop web && docker ps -a --filter name=web
docker start web && docker ps
docker rm -f web
```

**Try:** run `docker run alpine:3.20 echo hi` three times, then `docker ps -a`.
Count the stopped containers. Now do it with `--rm`. What changed?

## Lab 2: build your own image

```bash
docker build -t hello-app:1.0 examples
docker images hello-app
docker history hello-app:1.0
docker run -d --name hello -p 127.0.0.1:8080:8080 hello-app:1.0
curl -s http://127.0.0.1:8080/        # hello from a container (hit 1)
docker inspect -f '{{.State.Health.Status}}' hello   # starting -> healthy after ~30s
docker exec hello id                  # uid=10001(app): not root
docker rm -f hello
```

**Compare sizes** (the numbers in chapter 5 come from this):

```bash
printf 'FROM python:3.11\nWORKDIR /app\nCOPY app/ ./\nCMD ["python","server.py"]\n' > /tmp/full.Dockerfile
docker build -f /tmp/full.Dockerfile -t hello-app:full examples
docker build -f examples/multistage.Dockerfile -t hello-app:ms examples
docker images hello-app
docker image inspect hello-app:full hello-app:1.0 hello-app:ms --format '{{index .RepoTags 0}} {{.Size}}'
```

**Try the cache:** run `docker build -t hello-app:1.0 examples` again: every step
says `CACHED`. Edit the greeting in `examples/app/server.py` and build again.
Which steps re-ran?

## Lab 3: fix a bad Dockerfile

[`examples/bad.Dockerfile`](../examples/bad.Dockerfile) breaks a rule on every line.

```bash
pip install -e .
python -m dockerhygiene.cli check examples/bad.Dockerfile
docker run --rm -i hadolint/hadolint < examples/bad.Dockerfile
```

Rewrite it until both tools are quiet. Then compare with
[`examples/Dockerfile`](../examples/Dockerfile).

**See the leaked secret:** build the bad file (from the `examples/` folder, so the
`COPY` and `requirements.txt` exist) and read the key back out of the image:

```bash
docker build -f examples/bad.Dockerfile -t leaky examples
docker inspect leaky --format '{{json .Config.Env}}'   # API_KEY=replace-me is right there
docker rmi leaky
```

## Lab 4: volumes keep data

The app counts hits in `/data/hits.txt`.

```bash
docker volume create hello-data
docker run -d --name h -p 127.0.0.1:8080:8080 -v hello-data:/data hello-app:1.0
curl -s http://127.0.0.1:8080/; curl -s http://127.0.0.1:8080/   # hit 1, hit 2
docker rm -f h
docker run -d --name h -p 127.0.0.1:8080:8080 -v hello-data:/data hello-app:1.0
curl -s http://127.0.0.1:8080/                                     # hit 3: data survived
docker rm -f h
```

Now run the same without `-v`: the count restarts at 1 every time. Finally:

```bash
docker volume rm hello-data
```

## Lab 5: two containers talk by name

```bash
docker network create lab-net
docker run -d --name api --network lab-net hello-app:1.0
docker run --rm --network lab-net curlimages/curl:8.10.1 -s http://api:8080/health   # ok
docker run --rm curlimages/curl:8.10.1 -s --max-time 3 http://api:8080/health \
  || echo "default bridge: no name lookup"
docker rm -f api && docker network rm lab-net
```

## Lab 6: compose with a database

```bash
cd examples
cp db_password.txt.example db_password.txt     # local only, ignored by git
docker compose up -d --build
docker compose ps
curl -s http://127.0.0.1:8080/
docker compose --profile db up -d
docker compose exec db pg_isready -U postgres
docker compose config | head -30               # the merged, final config
docker volume ls | grep hello_                 # project name prefix
docker compose --profile db down               # volumes kept
docker volume ls | grep hello_                 # still there
docker compose --profile db down -v            # now they are gone
cd ..
```

## Lab 7: signals and memory limits

**Signals** (the table in chapter 14 comes from this):

```bash
printf 'FROM hello-app:1.0\nCMD python server.py\n' | docker build -t hello-app:shellform -
docker run -d --name ex hello-app:1.0
docker run -d --name sh hello-app:shellform
sleep 3
time docker stop ex; docker inspect -f 'exit={{.State.ExitCode}}' ex   # fast, exit=0
time docker stop sh; docker inspect -f 'exit={{.State.ExitCode}}' sh   # slow, exit=137
docker logs ex | tail -1                                               # got signal 15
docker rm ex sh
```

**Memory limit:**

```bash
docker run --rm --memory 64m --memory-swap 64m python:3.11-slim \
  python -c "x = bytearray(200 * 1024 * 1024)"; echo "exit=$?"   # exit=137
docker run --name oom --memory 64m --memory-swap 64m python:3.11-slim \
  python -c "x = bytearray(200 * 1024 * 1024)"
docker inspect -f 'OOMKilled={{.State.OOMKilled}}' oom; docker rm oom
```

## Lab 8: cleanup drill

```bash
scripts/docker-disk-report.sh                 # what is using space
docker system df | python -m dockerhygiene.cli df
scripts/docker-cleanup.sh                     # dry run: nothing is deleted
scripts/docker-cleanup.sh --level safe --yes  # stopped containers, dangling images, old build cache
docker rmi hello-app:full hello-app:ms hello-app:shellform 2>/dev/null
docker system df
```

**Think:** which command would you never run on a machine whose local database
you have not backed up? (Answer: anything with `volume prune -a` or `down -v`.)
