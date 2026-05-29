.PHONY: sync lint format test test-py test-dotnet docker-build docker-shell docker-lint docker-test

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

docker-build:
	docker compose build dev

docker-shell:
	docker compose run --rm dev

docker-lint:
	docker compose run --rm dev make lint

docker-test:
	docker compose run --rm dev make test
