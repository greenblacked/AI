.DEFAULT_GOAL := help
PYTHON ?= python3
SHELL := bash

.PHONY: help validate test lint package install clean

help: ## Show this help
	@grep -hE '^[a-z-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

validate: ## Validate every skill, subagent and the marketplace manifest
	PYTHONPATH=src $(PYTHON) -m skillcheck . --strict

test: ## Run the validator's own test suite
	PYTHONPATH=src pytest

lint: ## Lint python, markdown, YAML and workflows (skips a tool when it is not installed)
	@command -v ruff >/dev/null 2>&1 && ruff check . && ruff format --check . || \
		echo "ruff not installed - run: pipx install ruff"
	@command -v markdownlint-cli2 >/dev/null 2>&1 && markdownlint-cli2 "**/*.md" || \
		echo "markdownlint-cli2 not installed - run: npx markdownlint-cli2 '**/*.md'"
	@command -v yamllint >/dev/null 2>&1 && yamllint --strict . || \
		echo "yamllint not installed - run: pipx install yamllint"
	@command -v actionlint >/dev/null 2>&1 && actionlint || \
		echo "actionlint not installed - see https://github.com/rhysd/actionlint"

package: ## Build a .skill archive for every skill into dist/
	@PYTHONPATH=src $(PYTHON) scripts/package_skills.py

install: ## Symlink every skill into ~/.claude/skills
	@scripts/install.sh

clean: ## Remove build output and caches
	rm -rf dist .pytest_cache
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
