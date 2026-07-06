# Contributing to SentinelAI

Thanks for your interest! This project follows a lightweight, quality-first flow.

## Getting started
1. Fork & clone; create a feature branch off `main`.
2. Backend: `cd backend && pip install -r requirements.txt ruff pytest`.
3. Frontend: `cd frontend && npm install`.

## Before you push
- `cd backend && ruff check app && pytest -q`
- `cd frontend && npm run build`
- Add tests for new threat rules, endpoints, or tracker changes.

## Commit style
Conventional commits: `feat|fix|docs|chore|refactor|test(scope): summary`.

## Code standards
See [docs/DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md) — PEP 8, type hints,
docstrings, structured logging, error handling, modular design.

## Pull requests
Keep them focused and describe the *why*. Link related issues. CI must pass.

## Responsible use
This is defensive security software. Contributions that add mass-surveillance,
covert tracking of individuals without consent, or detection-evasion features
will not be accepted.
