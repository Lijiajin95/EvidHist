UV_BIN := $(if $(wildcard .venv/bin/uv),.venv/bin/uv,uv)
UV := env UV_CACHE_DIR=$(CURDIR)/.cache/uv UV_PYTHON_INSTALL_DIR=$(CURDIR)/.toolchain/python $(UV_BIN)
NPM := env npm_config_cache=$(CURDIR)/.cache/npm npm --prefix $(CURDIR)/frontend
TEST_DATABASE_URL ?= postgresql+psycopg://evidhist:evidhist@127.0.0.1:55432/evidhist_test
FAST_TESTS := tests/unit tests/property tests/component tests/scenario

DEMO_DATABASE_URL ?= postgresql+psycopg://evidhist:evidhist@127.0.0.1:55433/evidhist_demo

.PHONY: setup format lint typecheck test check db-up db-down test-integration test-system coverage mutation audit sast security eval-fixture hooks precommit import-ming research-run run commit-policy-config api-schema api-schema-check structure-metrics import-lint deptry pylint coverage-thresholds frontend-setup frontend-check frontend-e2e frontend-mutation frontend-audit frontend-run migrate demo-up demo-down demo-migrate demo-seed demo-run

setup:
	$(UV) sync --frozen --default-index https://pypi.org/simple --group mutation --group security

format:
	.venv/bin/ruff check --fix src tests scripts
	.venv/bin/ruff format src tests scripts

lint:
	.venv/bin/ruff check src tests scripts
	.venv/bin/ruff format --check src tests scripts

typecheck:
	.venv/bin/pyright

test:
	.venv/bin/pytest $(FAST_TESTS)

check: lint typecheck test api-schema-check commit-policy-config structure-metrics import-lint deptry pylint

api-schema:
	.venv/bin/python scripts/export_openapi.py

api-schema-check:
	.venv/bin/python scripts/export_openapi.py --check

structure-metrics:
	.venv/bin/python scripts/check_structure_metrics.py

import-lint:
	.venv/bin/lint-imports

deptry:
	.venv/bin/deptry .

pylint:
	env PYLINTHOME=$(CURDIR)/.cache/pylint .venv/bin/pylint src scripts

db-up:
	.venv/bin/python scripts/test_database.py up

db-down:
	.venv/bin/python scripts/test_database.py down

test-integration:
	EVIDHIST_TEST_DATABASE_URL='$(TEST_DATABASE_URL)' .venv/bin/pytest tests/integration

test-system:
	EVIDHIST_TEST_DATABASE_URL='$(TEST_DATABASE_URL)' .venv/bin/pytest tests/system

coverage:
	mkdir -p reports
	EVIDHIST_TEST_DATABASE_URL='$(TEST_DATABASE_URL)' .venv/bin/pytest $(FAST_TESTS) tests/integration --cov --cov-report=term-missing --cov-report=xml:reports/coverage.xml --cov-report=json:reports/coverage.json
	.venv/bin/python scripts/check_coverage_thresholds.py

coverage-thresholds:
	.venv/bin/python scripts/check_coverage_thresholds.py

mutation:
	.venv/bin/mutmut run --max-children 2
	.venv/bin/mutmut export-cicd-stats
	.venv/bin/python scripts/check_mutation_stats.py

audit:
	mkdir -p reports
	$(UV) export --frozen --all-groups --no-emit-project --format requirements-txt --output-file reports/requirements-audit.txt > /dev/null
	.venv/bin/pip-audit --strict --no-deps --disable-pip --cache-dir .cache/pip-audit -r reports/requirements-audit.txt -f json -o reports/dependency-audit.json

sast:
	.venv/bin/python scripts/run_semgrep.py

security: audit sast

eval-fixture:
	.venv/bin/evidhist-eval-quotes --cases evals/quotes.jsonl --predictions evals/fixtures/quotes.predictions.jsonl --output reports/quote-eval.fixture.json

hooks:
	PRE_COMMIT_HOME=$(CURDIR)/.cache/pre-commit .venv/bin/pre-commit install --hook-type pre-commit --hook-type pre-push --hook-type commit-msg

commit-policy-config:
	.venv/bin/python scripts/check_commit_policy.py --validate-config

precommit:
	PRE_COMMIT_HOME=$(CURDIR)/.cache/pre-commit .venv/bin/pre-commit run --all-files

import-ming:
	.venv/bin/python scripts/import_ming_pilot.py --database-url '$(if $(EVIDHIST_DATABASE_URL),$(EVIDHIST_DATABASE_URL),$(DEMO_DATABASE_URL))'

research-run:
	.venv/bin/python scripts/run_research.py --database-url '$(if $(EVIDHIST_DATABASE_URL),$(EVIDHIST_DATABASE_URL),$(DEMO_DATABASE_URL))' \
		--question '$(QUESTION)' --executor '$(EXECUTOR)' --reviewer '$(REVIEWER)'

run:
	.venv/bin/uvicorn evidhist.api:app --host 127.0.0.1 --port 8000

frontend-run:
	$(NPM) run dev

migrate:
	.venv/bin/python scripts/migrate.py --database-url '$(if $(EVIDHIST_DATABASE_URL),$(EVIDHIST_DATABASE_URL),$(TEST_DATABASE_URL))'

demo-up:
	.venv/bin/python scripts/demo_database.py up

demo-down:
	.venv/bin/python scripts/demo_database.py down

demo-migrate:
	.venv/bin/python scripts/migrate.py --database-url '$(DEMO_DATABASE_URL)'

demo-seed:
	.venv/bin/python scripts/seed_demo.py

demo-run:
	EVIDHIST_DATABASE_URL='$(DEMO_DATABASE_URL)' .venv/bin/uvicorn evidhist.api:app --host 127.0.0.1 --port 8000

frontend-setup:
	$(NPM) install

frontend-check:
	$(NPM) run format:check
	$(NPM) run lint
	$(NPM) run typecheck
	$(NPM) run check:api-types
	$(NPM) run depcruise
	$(NPM) run knip
	$(NPM) run coverage

frontend-e2e:
	env PLAYWRIGHT_BROWSERS_PATH=$(CURDIR)/.cache/ms-playwright $(NPM) run e2e

frontend-mutation:
	$(NPM) run mutation

frontend-audit:
	$(NPM) run audit
