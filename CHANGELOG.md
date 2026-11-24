# Changelog

All notable changes are listed here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project
uses [Semantic Versioning](https://semver.org/).

## [1.0.0] - 2026-11-24

### Added

- 18 chapters from basics to internals, a course map, a cheatsheet and 78 interview
  questions grouped in 7 levels.
- 8 labs, each run end to end on Docker Desktop 4.90.0 (engine 29.7.2).
- Case study: a full C: drive, a read-only Docker disk, 148.7 GB shown by
  `docker system df` (prune reported 136.2 GB reclaimed), and the virtual disk
  shrunk from 129.8 GB to 3.8 GB.
- Example app with a production-style Dockerfile, a multi-stage Dockerfile, a broken
  Dockerfile for practice, a hardened `compose.yaml` and a `daemon.json`.
- `dockerhygiene`: a teaching Dockerfile linter (11 rules) and a `docker system df`
  cleanup planner. Standard library only; 69 tests on Python 3.10-3.12.
- Scripts: read-only disk report, dry-run-by-default cleanup, Windows vhdx compaction.
- CI: tests, hadolint, shellcheck, PSScriptAnalyzer, compose validation, image
  build with smoke test (non-root, health, clean SIGTERM stop), gitleaks.
