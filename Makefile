.PHONY: sync sync-all install test lint format type-check clean run

export PYTHONPATH := $(CURDIR)/src

sync:
	uv sync -v

sync-all:
	uv sync --all-extras

install:
	uv sync --all-extras

run:
	uv run uvicorn dacke.app:app --reload

test:
	uv run --extra dev pytest -vv -s --cache-clear

test-cov:
	uv run --extra dev pytest --cov=src --cov-report=html

lint:
	uv run --extra dev ruff check src tests

format:
	uv run --extra dev black src tests
	uv run --extra dev ruff check --fix src tests

type-check:
	uv run --extra dev mypy src

clean:
	rm -rf build dist *.egg-info .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

docker-clean:
	docker-compose down -v

dev-setup:
	cp .env.example .env
	$(MAKE) docker-up
	$(MAKE) install

dev-teardown:
	$(MAKE) docker-clean

test-all:
	$(MAKE) lint
	$(MAKE) type-check
	$(MAKE) test-cov


migrate:
	uv run --extra db alembic upgrade head

help:
	@echo "Available commands:"
	@echo "  make sync              - Sync dependencies"
	@echo "  make sync-all          - Sync all dependencies including extras"
	@echo "  make install           - Install all dependencies"
	@echo "  make run               - Run development server"
	@echo "  make test              - Run tests"
	@echo "  make test-cov          - Run tests with coverage report"
	@echo "  make test-all          - Run lint, type-check, and tests"
	@echo "  make lint              - Run linter"
	@echo "  make format            - Format code"
	@echo "  make type-check        - Run type checker"
	@echo "  make clean             - Clean build artifacts"
	@echo "  make docker-up         - Start Docker services"
	@echo "  make docker-down       - Stop Docker services"
	@echo "  make docker-logs       - View Docker logs"
	@echo "  make docker-clean      - Stop and remove Docker volumes"
	@echo "  make dev-setup         - Setup development environment"
	@echo "  make dev-teardown      - Teardown development environment"
	@echo "  make migrate           - Run database migrations"
	
