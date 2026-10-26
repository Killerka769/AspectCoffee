# Aspect Coffee

Интернет-магазин Aspect Coffee на Django 5.2. В репозитории находятся исходный код, миграции, шаблоны, статические исходники, Docker-конфигурация и эксплуатационная документация.

Снимок подготовлен из работающего проекта `/opt/aspectcoffee` 19 июля 2026 года. В него намеренно не включены `.env.prod`, база данных, пользовательские медиафайлы, приватные ключи, логи, собранный `staticfiles/`, резервные копии и временные скрипты.

## Документация

1. [Репозитории, ветки и выпуск изменений](docs/01_REPOSITORY_WORKFLOW.md)
2. [Сервер и поднятые сервисы](docs/02_SERVER_AND_SERVICES.md)
3. [Навигация по коду и карта хардкода](docs/03_CODE_AND_HARDCODE_MAP.md)
4. [Интеграции и переключение тестовых/боевых API](docs/04_INTEGRATIONS.md)
5. [Почта, парсер и фоновые службы](docs/05_MAIL_PARSER_AND_JOBS.md)
6. [Тестовый контур и безопасное влитие](docs/06_TEST_ENVIRONMENT.md)
7. [Инструкция по деплою на новый сервер под панелью ISPmanager 6](docs/07_DEPLOY_TO_NEW_SERVER_ISP.md)

## Быстрый запуск для разработки

Требования: Python 3.12 и Redis, если нужны Celery-задачи.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements/dev.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
```

На Windows активация окружения выполняется командой `.venv\Scripts\activate`.

По умолчанию `manage.py` использует `config.settings.dev`: SQLite и вывод писем в консоль. OAuth, реальные платежи и СДЭК без отдельных тестовых реквизитов запускать нельзя.

## Запуск через Docker Compose

Чистый локальный стенд одной командой, без VPN, TLS и рабочих секретов:

```bash
docker compose -f compose.local.yml up --build -d
```

Откройте `http://127.0.0.1:8000`. База и media создаются в отдельных named volumes; миграции и статика выполняются автоматически. Письма локально выводятся в консоль, платежные ключи пустые. Это не production-конфигурация. Подробности исправлений и приёмки: [handover](docs/09_HANDOVER_ACCEPTANCE.md).

Существующий production/VPN-контур:

```bash
cp .env.example .env.prod
# Заполнить секреты и реквизиты в .env.prod
docker compose build
docker compose run --rm web python manage.py migrate
docker compose run --rm web python manage.py collectstatic --noinput
docker compose up -d
docker compose ps
```

`docker-compose.yml` рассчитан на текущую серверную схему: SQLite и каталог `media/` подключаются как volumes, Redis работает отдельным контейнером, Nginx публикуется только на VPN-адресе `10.88.0.1`.

## Правила безопасности

- Никогда не коммитить `.env.prod`, SQLite, `media/`, VAPID/DKIM/TLS/OpenVPN-ключи и токены GitVerse.
- Не хранить токен в URL `origin`; использовать SSH-ключ или менеджер учётных данных.
- Перед каждым релизом выполнять поиск секретов, тесты, миграции и резервное копирование базы/медиа.
- `main` обновлять только через запрос на слияние после проверки чистой ветки.

Все значения в `.env.example` являются шаблонами, а не рабочими секретами.
