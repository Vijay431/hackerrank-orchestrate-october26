# Thin aliases over the raw commands in README.md; no logic lives here.
PY ?= .venv/bin/python

# .env is read by code/llm.py (plain KEY=value parser); never include it here, make would evaluate it as Makefile syntax.

.DEFAULT_GOAL := help
.PHONY: help install run eval validate usage package

help: ## List targets
	@grep -E '^[a-z]+:.*## ' Makefile | awk -F':.*## ' '{printf "%-10s %s\n", $$1, $$2}'

install: ## Create .venv and install dependencies
	python3 -m venv .venv
	$(PY) -m pip install -r code/requirements.txt

run: ## Submission run (intent gate on, needs OPENROUTER_API_KEY) then validate
	$(PY) code/main.py
	$(PY) code/validate_output.py

eval: ## Score the golden samples and custom cases only (needs OPENROUTER_API_KEY), write evaluation report
	$(PY) code/evaluation/main.py

validate: ## Check the output.csv contract
	$(PY) code/validate_output.py

usage: ## Write evaluation/usage_report.md from the usage ledger
	$(PY) code/usage_report.py

package: ## Build code.zip and list contents
	$(PY) code/package.py
