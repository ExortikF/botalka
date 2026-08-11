# Архитектура

## Стек (предложение, требует подтверждения)

| Слой | Выбор | Почему |
|---|---|---|
| Backend | Python 3.12 + FastAPI | нативные WebSocket для дуэлей; ИИ-проверка и OCR потом всё равно на Python |
| БД | PostgreSQL 16 | ничего экзотичного не нужно |
| Кеш/очереди | Redis | подбор соперника, состояние матчей, rate limit, pub/sub между процессами |
| Frontend | Next.js 15 (App Router) + TypeScript | одна кодовая база на сайт и Telegram Mini App |
| Формулы | KaTeX | быстрее MathJax, для школьной математики хватает |
| Стили | Tailwind | скорость; дизайн-система на CSS-переменных |
| Бот | aiogram 3 | стандарт для ТГ на Python |
| Хостинг | один VPS, docker compose, nginx + certbot | дёшево, всё в одном месте; поводов для Kubernetes нет |
| Фоновые задачи | ARQ (Redis) | позже: ИИ-проверки, рассылки, пересчёт рейтингов |

**Альтернатива, которую отклонил:** делать всё на Next.js без Python-бэкенда. Меньше
движущихся частей, но ИИ-проверка и распознавание фото — центральная фича на горизонте
полугода, и она на Python. Городить второй сервис потом дороже, чем начать с двух сразу.

## Сервисы

```
              nginx (443)
                  │
        ┌─────────┴──────────┐
        │                    │
   Next.js (3000)      FastAPI (8000)
   сайт + Mini App     REST + WebSocket
                             │
                    ┌────────┴────────┐
                Postgres            Redis
                                       │
                                  worker (ARQ)   ← появится на этапе ИИ-проверок
                                       │
                              Telegram bot (aiogram)
```

## Схема БД (первая версия)

```
users            id, tg_id, username, display_name, avatar_url, created_at, last_seen_at
                 rating (Эло, старт 1000), streak_days, streak_last_date

subjects         id, slug (math_prof), title
task_types       id, subject_id, number (номер задания в КИМ), title, description
                 нумерация заданий меняется по годам — держим поле year_spec

tasks            id, task_type_id, statement_md, image_url, answer_type, answer_payload,
                 solution_md, difficulty (1–5), source, status (draft/live/broken), created_at

attempts         id, user_id, task_id, quiz_id, answer_raw, is_correct, time_spent_ms, created_at
                 главная таблица аналитики — из неё растут и статистика, и повторения

quizzes          id, user_id, mode (solo/duel/daily/challenge), task_ids[], score,
                 started_at, finished_at

duels            id, player_a, player_b, task_ids[], score_a, score_b, winner_id,
                 rating_delta_a, rating_delta_b, state, created_at, finished_at

daily_task       date, task_id                       — задача дня, одна на всех
achievements     id, user_id, code, unlocked_at

# Появится позже
essays           id, user_id, subject_id, text, status, submitted_at
essay_reviews    id, essay_id, model, criteria_json, total_score, cost_usd, created_at
```

Индексы, о которых легко забыть: `attempts(user_id, created_at)`,
`attempts(task_id)`, `tasks(task_type_id, status)`.

## Как устроены дуэли

1. Игрок нажимает «Найти соперника» → WebSocket `/ws/duel` → попадает в очередь Redis
   (`ZADD queue rating`), ищем соперника с близким рейтингом
2. Нашли пару → создаём `duel`, обоим шлём `match_found` с составом из 5 задач
3. Одна и та же задача у обоих одновременно. Ответил — `answer` на сервер, сервер
   проверяет (**клиент правильный ответ не получает никогда**), шлёт `opponent_answered`
4. Очки: 100 за верный + бонус за скорость (до 50). Ничья по очкам → выигрывает быстрый
5. Конец матча → пересчёт Эло, запись в `duels`, обоим `match_result`
6. Разрыв связи: 30 секунд на реконнект (состояние в Redis), не вернулся — поражение

**Важные решения:**
- Состояние матча живёт в Redis, а не в памяти процесса — иначе рестарт бэкенда рвёт
  все активные дуэли и нельзя запустить второй воркер
- Таймер авторитетный на сервере. Клиентский — только для отрисовки
- Никого в очереди 15 секунд → предлагаем бота: те же задачи, «соперник» отвечает по
  усреднённой статистике живых игроков на этих задачах. Честно помечаем в интерфейсе

## Аутентификация

Только Telegram Login: на сайте — виджет, в Mini App — `initData`. Обязательно проверять
подпись `initData` HMAC-ом от токена бота на сервере — без этого любой представится кем угодно.
Сессия — JWT в httpOnly-куке.

Email/пароль не заводим: лишние формы, восстановление доступа, утечки паролей — и всё
ради аудитории, которая и так в Telegram.

## Что держим в голове с самого начала

- **Правильные ответы не уходят на клиент** до завершения попытки — иначе весь рейтинг
  фиктивный. Проверка только на сервере
- **Rate limit** на отправку ответов и на создание матчей
- **Всё событийно:** каждая попытка пишется в `attempts` — это фундамент и для статистики,
  и для интервальных повторений, и для персонального плана
- **Предметная независимость:** нигде в коде не должно быть `if subject == "math"`.
  Различия — в данных (`task_types`, `answer_type`), не в ветвлениях
- **Стоимость ИИ-вызовов** пишем в БД с первого дня работы проверок — иначе экономику
  не посчитать
