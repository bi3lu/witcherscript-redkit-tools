.PHONY: sync lint format test test-py test-dotnet

sync:
	uv sync --all-extras --dev
	dotnet restore src/dotnet/WitcherScript.RedkitTooling.sln

lint:
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy src/py

format:
	uv run ruff format .
	uv run ruff check . --fix

test: test-py test-dotnet

test-py:
	uv run pytest

test-dotnet:
	dotnet test src/dotnet/WitcherScript.RedkitTooling.sln
