# SentinelAI — common developer tasks.
# Usage: make <target>

COMPOSE = docker compose -f infra/docker/docker-compose.yml

.PHONY: help
help:
	@echo "SentinelAI targets:"
	@echo "  install-backend   Create venv and install backend deps"
	@echo "  install-frontend  Install frontend deps"
	@echo "  backend           Run the FastAPI backend (reload)"
	@echo "  frontend          Run the Vite dev server"
	@echo "  demo              Run the local pipeline on the webcam"
	@echo "  test              Run backend tests"
	@echo "  lint              Ruff lint backend"
	@echo "  up / down         Start / stop the full Docker stack"
	@echo "  logs              Tail Docker logs"

.PHONY: install-backend
install-backend:
	cd backend && python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt

.PHONY: install-frontend
install-frontend:
	cd frontend && npm install

.PHONY: backend
backend:
	cd backend && uvicorn app.main:app --reload --port 8000

.PHONY: frontend
frontend:
	cd frontend && npm run dev

.PHONY: demo
demo:
	cd backend && python run_local.py --source 0 --demo-zone

.PHONY: test
test:
	cd backend && pytest -q

.PHONY: lint
lint:
	cd backend && ruff check app

.PHONY: up
up:
	$(COMPOSE) up --build -d

.PHONY: down
down:
	$(COMPOSE) down

.PHONY: logs
logs:
	$(COMPOSE) logs -f --tail=100
