# Contributing

Thanks for taking a look. Changes are judged on whether they keep the course
clear, correct and honest about its numbers.

## Ground rules

1. **Every measured number has a command.** Sizes, timings and counts in the docs come
   from a lab or a command shown next to them. If you change the examples, rerun the
   lab and update the numbers, and say which Docker version you used.
2. **Simple words.** Short sentences, one idea each. Explain *why*, not only *what*.
3. **Commands must run.** Every command block should work when pasted, from the repo
   root unless the block says otherwise.
4. **Safe by default.** Anything that deletes data is a dry run unless the reader
   passes an explicit flag, and the docs say what is lost.
5. **No secrets, no real hosts.** Use `example.com`, placeholder values and the
   `db_password.txt.example` pattern.

## Set up

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Checks CI runs

```bash
pytest
dockerhygiene check examples/Dockerfile
docker run --rm -i hadolint/hadolint:v2.12.0 < examples/Dockerfile
shellcheck scripts/*.sh
(cd examples && cp db_password.txt.example db_password.txt && docker compose config --quiet)
docker build -t hello-app:ci examples
```

## Adding a linter rule

1. Add it to `src/dockerhygiene/dockerfile_check.py` with the next `DHxxx` id, a
   severity, and a message that explains why.
2. Add a positive and a negative test in `tests/test_dockerfile_check.py`.
3. Make sure `examples/Dockerfile` still has no findings, and add a line to
   `examples/bad.Dockerfile` if the rule is a common mistake.
4. Mention it in the chapter that teaches it.
