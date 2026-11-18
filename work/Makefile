.DEFAULT_GOAL := help
PY ?= python3
PORT ?= 8090
DB ?= .openbot/state/openbot.db

.PHONY: help install test reuse-test workforce-demo lint smoke verify demo run seed stop clean release-check tidy tidy-check check-mirrors hq-install hq-test hq-run isolation-install isolation-check isolation-test isolation-demo

help: ## show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS=":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

install: ## install the Python control plane (no Docker, no keys needed)
	$(PY) -m pip install -r requirements.txt

test: ## run the Python control-plane tests
	$(PY) -m pytest

reuse-test: ## test the adopted findrepo CLI and Bot HQ queue (Node 18+, no npm install)
	node --test tools/findrepo/test/*.test.mjs packages/bot-hq-queue/*.test.mjs

workforce-demo: ## offline work intake, QA packet and synthetic reviewed/revoked feedback; no external actions
	$(PY) scripts/workforce-demo.py

lint: ## ruff the control plane (findings and missing dependencies fail)
	$(PY) -m ruff check services packages scripts

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

clean: tidy ## remove allowlisted caches only; retain business state and run evidence

hq-install: ## restore pinned Bot HQ local dependencies and build; no provider startup
	bash scripts/bot-hq.sh install

hq-test: ## build/typecheck and test the local-only HQ + independent report boundary
	bash scripts/bot-hq.sh test

hq-run: ## foreground authenticated local-only HQ on :8787; providers disabled
	bash scripts/bot-hq.sh start

isolation-install: ## explicitly download/extract pinned rootless tool to cache; no system install or services
	$(PY) scripts/bootstrap-isolation.py --install

isolation-check: ## read/check pinned fixed-tool setup; no implicit download
	$(PY) scripts/bootstrap-isolation.py

isolation-test: isolation-check ## opt-in fixed-namespace + legacy-transport integrity regressions; no providers
	OPENBOT_TEST_NAMESPACE=1 $(PY) -m pytest services/gateway/tests/test_namespace_executor.py scripts/tests/test_isolation_bootstrap.py services/worker/tests/test_transport_truth.py services/worker/tests/test_dispatch_agui.py

isolation-demo: isolation-check ## actual fixed namespace denials, parent-death and no-retry evidence in disposable state
	$(PY) scripts/isolation-demo.py

release-check: verify test reuse-test hq-test smoke ## local checks only; not public-release approval
	@echo "\nrelease-check: local gates green. Not a public-release approval; see STRATEGY_ADDENDUM.md."

tidy-check: ## preview cache cleanup (read-only; exit 1 if caches exist)
	bash scripts/clean.sh --check

tidy: ## remove untracked caches only; preserve databases, logs, runs and donors
	bash scripts/clean.sh --apply

check-mirrors: ## read-only donor provenance report; never clone or push
	bash scripts/mirror-upstreams.sh --check
