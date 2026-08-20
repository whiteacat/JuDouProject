.PHONY: up down logs build test lint install

up:
	docker compose -f deploy/docker-compose.yml up -d

down:
	docker compose -f deploy/docker-compose.yml down

logs:
	docker compose -f deploy/docker-compose.yml logs -f

build:
	docker compose -f deploy/docker-compose.yml build

install:
	cd backend && python -m pip install -e ".[dev]"

test:
	cd backend && python -m pytest

lint:
	cd backend && python -m ruff check .
