.PHONY: test test-verbose clean install dev help


test:
	uv run pytest


install:
	uv sync --dev


build:
	uv run hatch build

publish-test:
	uv run hatch publish --repo test

publish:
	uv run hatch publish

publish-clean:
	rm -r dist/