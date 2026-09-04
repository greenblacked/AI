.DEFAULT_GOAL := help
PYTHON ?= python3
SHELL := bash

# Read the pins out of the workflow so there is one source of truth. A local linter on a
# different version is worse than no local linter: ruff 0.16 formats Python inside
# Markdown fences and 0.15 does not, so an older one reports a tree clean that CI then
# rejects. That has happened here twice, once because an older binary earlier on PATH
# shadowed the pinned one.
RUFF_PIN := $(shell sed -n "s/^ *RUFF_VERSION: *'\(.*\)'/\1/p" .github/workflows/security.yml)
MARKDOWNLINT_PIN := 0.23.2

.PHONY: help validate test lint package install clean

help: ## Show this help
	@grep -hE '^[a-z-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

validate: ## Validate every skill, subagent and the marketplace manifest
	PYTHONPATH=src $(PYTHON) -m skillcheck . --strict

test: ## Run the validator's own test suite
	PYTHONPATH=src pytest

lint: ## Lint python, markdown, YAML and workflows (skips a tool when it is not installed)
	@if command -v ruff >/dev/null 2>&1; then \
		have=$$(ruff --version | awk '{print $$2}'); \
		if [ "$$have" != "$(RUFF_PIN)" ]; then \
			echo "warning: ruff $$have is first on PATH but CI pins $(RUFF_PIN)."; \
			echo "         0.16 formats Python inside Markdown fences and older versions do not,"; \
			echo "         so this run can pass where CI fails - run: pipx install ruff==$(RUFF_PIN)"; \
		fi; \
		ruff check .; rc=$$?; ruff format --check .; fc=$$?; \
		[ $$rc -eq 0 ] && [ $$fc -eq 0 ]; \
		else echo "ruff not installed - run: pipx install ruff==$(RUFF_PIN) (the version CI pins)"; fi
	@if command -v markdownlint-cli2 >/dev/null 2>&1; then markdownlint-cli2 "**/*.md"; \
		else echo "markdownlint-cli2 not installed - run: npx markdownlint-cli2@$(MARKDOWNLINT_PIN) '**/*.md'"; fi
	@if command -v yamllint >/dev/null 2>&1; then yamllint --strict .; \
		else echo "yamllint not installed - run: pipx install yamllint"; fi
	@if command -v actionlint >/dev/null 2>&1; then actionlint; \
		else echo "actionlint not installed - see https://github.com/rhysd/actionlint"; fi

package: ## Build a .skill archive for every skill into dist/
	@PYTHONPATH=src $(PYTHON) scripts/package_skills.py

install: ## Symlink every skill into ~/.claude/skills
	@scripts/install.sh

clean: ## Remove build output and caches
	rm -rf dist .pytest_cache
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
