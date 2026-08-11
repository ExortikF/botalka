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

## Внешний доступ через туннель

Вход через Telegram требует публичный домен — `localhost` виджет не принимает.

```bash
cloudflared tunnel --url http://localhost:3000
```

Команда печатает адрес вида `https://xxx.trycloudflare.com`. Его нужно указать боту
через `@BotFather` → `/setdomain`. **Адрес меняется при каждом перезапуске туннеля**,
и `/setdomain` придётся повторять — для постоянной работы нужен свой домен.

API проксируется самим Next (`/api/*` → backend), поэтому туннеля на порт 3000
достаточно: и фронт, и API, и куки живут на одном адресе.

## Что уже работает (Спринт 0)

- docker compose: Postgres, Redis, FastAPI, Next.js
- `/health` с реальной проверкой БД и Redis
- Вход через Telegram (виджет на сайте и `initData` в Mini App), сессия в JWT-куке
- Модель `users` + Alembic-миграция
- Тесты на проверку подписи Telegram, CI на GitHub Actions

## Что работает (Спринты 1–2)

- Банк задач в YAML → БД: `docker compose exec backend python -m app.cli.import_content`
  (идемпотентно, отказывается импортировать задачу, чей эталонный ответ не проходит
  собственную проверку, и live-задачу без разбора)
- Движок проверки ответов: 5 типов, нормализация запятой, юникодных минусов, «ё»
- Квиз **без регистрации**: гость заводится автоматически, прогресс копится,
  вход через Telegram потом привязывается к тому же пользователю
- Разбор ошибок, серия дней, статистика решаемости по номерам заданий

## Дальше

Спринт 3 — дуэли: WebSocket, подбор соперника через Redis, рейтинг Эло.
См. `docs/ROADMAP.md`.
