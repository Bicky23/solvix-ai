.PHONY: install run dev test lint docker-build docker-run help

help:
	@echo "Solvix AI Engine Commands"
	@echo "========================="
	@echo ""
	@echo "Development:"
	@echo "  make install    - Install dependencies"
	@echo "  make run        - Run the API server"
	@echo "  make dev        - Run with auto-reload"
	@echo "  make test       - Run tests"
	@echo "  make lint       - Run linter"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build  - Build Docker image"
	@echo "  make docker-run    - Run Docker container"

install:
	pip install -e ".[dev]"

run:
	uvicorn src.main:app --host 0.0.0.0 --port 8001

dev:
	uvicorn src.main:app --host 0.0.0.0 --port 8001 --reload

test:
	pytest tests/ -v

test-cov:
	pytest tests/ --cov=src --cov-report=html

lint:
	ruff check src/ tests/

format:
	ruff format src/ tests/

docker-build:
	docker build -t solvix-ai-engine .

docker-run:
	docker run -p 8001:8001 --env-file .env solvix-ai-engine
