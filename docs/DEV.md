# Локальная разработка

## Запуск

```bash
cp .env.example .env      # заполнить TELEGRAM_BOT_TOKEN и JWT_SECRET
make up
make migrate
```

- Сайт: http://localhost:3000
- API и Swagger: http://localhost:8000 / http://localhost:8000/docs
- Проверка сервисов: http://localhost:8000/health

Порты Postgres (5433) и Redis (6380) намеренно нестандартные — чтобы не конфликтовать
с уже запущенными на машине.

## Команды

| Команда | Что делает |
|---|---|
| `make up` | собрать и поднять всё |
| `make down` | остановить |
| `make logs` | логи backend и web |
| `make migrate` | применить миграции |
| `make makemigration m="описание"` | сгенерировать миграцию по изменениям моделей |
| `make test` | тесты бэкенда |
| `make shell-db` | psql внутри контейнера |

## Телеграм-бот для разработки

1. `@BotFather` → `/newbot` → получить токен
2. `/setdomain` → указать домен для Login Widget. Для локальной разработки виджет
   Telegram с `localhost` не работает — нужен туннель (`cloudflared`, `ngrok`) и его
   домен в `/setdomain`
3. Токен → `TELEGRAM_BOT_TOKEN`, имя бота → `TELEGRAM_BOT_USERNAME` и
   `NEXT_PUBLIC_TELEGRAM_BOT_USERNAME`
4. `NEXT_PUBLIC_*` читаются при старте контейнера — после правки `.env`
   `docker compose up -d --force-recreate web`

Проверить проверку подписи без реального бота можно тестами: `make test`.

## Что уже работает (Спринт 0)

- docker compose: Postgres, Redis, FastAPI, Next.js
- `/health` с реальной проверкой БД и Redis
- Вход через Telegram (виджет на сайте и `initData` в Mini App), сессия в JWT-куке
- Модель `users` + Alembic-миграция
- Тесты на проверку подписи Telegram, CI на GitHub Actions

## Дальше

Спринт 1 — банк задач: модели `subjects/task_types/tasks/attempts`, импортёр
`content/*.yaml → БД`, движок проверки ответов. См. `docs/ROADMAP.md`.
