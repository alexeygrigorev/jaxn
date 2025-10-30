.PHONY: test test-verbose clean install dev help

help:
	@echo "Available targets:"
	@echo "  make test          - Run all tests"
	@echo "  make test-verbose  - Run tests with verbose output"
	@echo "  make install       - Install package in editable mode"
	@echo "  make dev           - Install package with dev dependencies"
	@echo "  make clean         - Remove Python cache files"

test:
	uv run pytest

test-verbose:
	uv run pytest -v -s

install:
	uv sync --dev

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>nul || true
	find . -type f -name "*.pyc" -delete 2>nul || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>nul || true
