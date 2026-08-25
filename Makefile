up:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f

backend-test:
	docker compose run --rm backend pytest

backend-lint:
	docker compose run --rm backend ruff check app tests

db-migrate:
	docker compose run --rm backend alembic upgrade head
