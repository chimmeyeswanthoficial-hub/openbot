.DEFAULT_GOAL := help
PY ?= python3
PORT ?= 8090
DB ?= .openbot/state/openbot.db

.PHONY: help install test lint smoke verify demo run seed stop clean release-check

help: ## show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS=":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

install: ## install the Python control plane (no Docker, no keys needed)
	$(PY) -m pip install -r requirements.txt

test: ## run every test in the repo
	$(PY) -m pytest

lint: ## ruff the control plane
	$(PY) -m ruff check services packages scripts 2>/dev/null || echo "ruff not installed: pip install ruff"

smoke: ## end-to-end smoke on a throwaway database
	bash scripts/smoke.sh

verify: ## the go/no-go gate (docs, governance, routines, budget, substrate)
	bash scripts/verify.sh

demo: seed run ## seed a demo dataset, then serve the console on :$(PORT)

seed: ## write demo decisions + ledger rows through the validated paths
	$(PY) scripts/seed-demo.py --base http://127.0.0.1:$(PORT)

run: ## serve the control room (console + API) on :$(PORT)
	@mkdir -p .openbot/state
	SENTINEL_DB=$(DB) $(PY) -m uvicorn app:app --app-dir services/sentinel --host 0.0.0.0 --port $(PORT)

stop: ## stop a background control plane started by scripts/pause-all.sh or this file
	-pkill -f "uvicorn app:app" 2>/dev/null || true

clean: ## remove generated state and caches
	rm -f $(DB) $(DB)-journal .openbot/state/pnl.json
	find . -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .ruff_cache

release-check: verify test smoke ## everything that must be green before a release
	@echo "\nrelease-check: green. Tag it, and put the verify output in the release note."
