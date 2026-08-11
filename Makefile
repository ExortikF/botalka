.PHONY: up down logs migrate makemigration test shell-db

up:            ## поднять всё локально
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f backend web

makemigration:  ## make makemigration m="что поменялось"
	docker compose exec backend alembic revision --autogenerate -m "$(m)"

migrate:
	docker compose exec backend alembic upgrade head

test:
	docker compose exec backend pytest -q

shell-db:
	docker compose exec db psql -U botalka -d botalka
