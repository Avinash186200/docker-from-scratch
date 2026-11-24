.PHONY: install test lint image smoke

install:
	pip install -e ".[dev]"

test:
	pytest -q

lint:
	dockerhygiene check examples/Dockerfile
	dockerhygiene check examples/multistage.Dockerfile
	docker run --rm -i hadolint/hadolint:v2.12.0 < examples/Dockerfile
	docker run --rm -i hadolint/hadolint:v2.12.0 < examples/multistage.Dockerfile

image:
	docker build -t hello-app:1.0 examples

smoke: image
	docker run --rm -d --name hello-smoke -p 127.0.0.1:8080:8080 hello-app:1.0
	sleep 2 && curl -fs http://127.0.0.1:8080/health
	docker stop hello-smoke
