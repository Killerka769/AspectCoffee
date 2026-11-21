# Aspect Coffee

Интернет-магазин Aspect Coffee на Django 5.2: каталог, корзина, ЮKassa, СДЭК, личный кабинет и PWA. В репозитории исходный код, миграции, шаблоны, статика, Docker и документация.

В git нет `.env.prod`, базы, `media/`, приватных ключей, логов и собранного `staticfiles/`.

Публичные контакты: **+7 988 291-93-92**, **aspectcoffeeroasters@gmail.com**. Они лежат в `SiteSettings` (админка «Настройки сайта») и подставляются в подвал, контакты и партнёрам. Оферта и политика читаются из документов в базе. Миграции `catalog.0052` и `pages.0020` записывают новые контакты поверх старых `+7 800 333 49 80`, `hello@aspectcoffee.ru` и WhatsApp `79508382000`. Свой номер или почта, уже введённые в админке, не затираются.

Письма с сайта уходят через почтовый сервер хоста. Адрес отправителя — `DEFAULT_FROM_EMAIL` в `.env.prod`. Заявки приходят на email из настроек сайта, затем на `CONTACT_EMAIL`.

## Документация

1. [Репозитории, ветки и выпуск](docs/01_REPOSITORY_WORKFLOW.md)
2. [Сервер и сервисы](docs/02_SERVER_AND_SERVICES.md)
3. [Карта кода](docs/03_CODE_AND_HARDCODE_MAP.md)
4. [Интеграции](docs/04_INTEGRATIONS.md)
5. [Почта и фоновые задачи](docs/05_MAIL_PARSER_AND_JOBS.md)
6. [Тестовый контур](docs/06_TEST_ENVIRONMENT.md)
7. [Новый сервер под ISPmanager](docs/07_DEPLOY_TO_NEW_SERVER_ISP.md)
8. [Восстановление TLS](docs/08_TLS_RECOVERY.md)
9. [Приёмка](docs/09_HANDOVER_ACCEPTANCE.md)

## Запуск с нуля на своём компьютере

Нужны Docker Desktop. Отдельный Python на Windows не нужен: ярлык из Microsoft Store не запускает Django.

```bash
docker compose -f compose.local.yml up --build -d
```

Сайт: `http://127.0.0.1:8000`. База и картинки живут в отдельных томах. Миграции и статика выполняются сами (`RUN_MIGRATIONS=1`). Письма печатаются в консоль контейнера, ключи оплаты пустые. Это не боевой режим.

Остановить:

```bash
docker compose -f compose.local.yml down
```

Без Docker, если установлен нормальный Python 3.12:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements/dev.txt
copy .env.example .env
python manage.py migrate
python manage.py runserver
```

На Linux и macOS окружение включается командой `source .venv/bin/activate`. `manage.py` по умолчанию берёт `config.settings.dev`: SQLite и почта в консоль.

## Боевой сервер

Каталог на сервере: `/opt/aspectcoffee`. Источник кода — GitVerse, ветка `main`. Файл `.env.prod` остаётся только на сервере и перекрывает настройки из кода, в том числе модуль Django.

Перед обновлением посмотрите, нет ли местных правок:

```bash
cd /opt/aspectcoffee
git status
git diff
```

Если git отказывается обновляться и просит commit или stash, эти файлы лежат только на сервере. Случайную правку верните так: `git restore путь/к/файлу`. Нужную спрячьте: `git stash push -m "server" -- путь/к/файлу`, затем после pull верните `git stash pop`.

Дальше:

```bash
git pull --ff-only
docker compose build
docker compose run --rm web python manage.py migrate
docker compose run --rm web python manage.py collectstatic --noinput
docker compose up -d
```

`migrate` нужен, когда в выпуске есть миграции. Для смены контактов он обязателен: без него в базе останутся старые телефон и почта, даже если шаблоны уже новые.

Проверка, что собрался новый код:

- в выводе `git pull` есть `Updating …`;
- в сборке шаг `COPY . /app/` не помечен `CACHED`;
- `git rev-parse --short HEAD` совпадает с коммитом, который отправили в GitVerse.

Nginx отдаёт стили и скрипты из папки `staticfiles` на хосте, а не из слоя образа. Поэтому после правок CSS и JS нужен `collectstatic`. Шаблоны попадают на сайт только через пересборку образа: каталог проекта в контейнер `web` не смонтирован, подключены `media`, `data` и `staticfiles`.

Боевая база — `data/db.sqlite3` на хосте. Файл `/app/db.sqlite3` внутри образа к магазину не относится. Резервную копию `data/db.sqlite3` и `media/` снимайте до миграций.

`.env.prod` и `docker-compose.yml` с сервера не затирайте локальной копией.

## Что уже ломалось

**Обновление не доезжало до сайта.** `git pull` останавливался из-за незакоммиченных правок `requirements/base.txt` и `requirements/prod.txt`. Сборка при этом проходила, но Docker брал старый слой `COPY . /app/` и помечал его `CACHED`. На сервере оставался прежний коммит. Лечится так: убрать или спрятать местные правки, дождаться успешного pull и только потом собирать образ.

**Стили не менялись после сборки.** Новый CSS оказывался внутри образа, а Nginx продолжал читать старый `./staticfiles`. Нужен `collectstatic` в контейнере, у которого эта папка смонтирована.

**Кнопка «Установить приложение».** Скрипт в `catalog/base.html` ловит `beforeinstallprompt` и показывает кнопку только на экране уже 1099px и только пока браузер отдал это событие. На компьютере кнопка скрыта. В уже установленном приложении её тоже нет. `static/js/aspect-cinematic.js` к установке не относится: таймеры там только у анимации корзины. Браузер может не прислать событие вообще. Так бывает в Safari и на iPhone (там только «На экран Домой»), в Firefox, в режиме инкогнито, без HTTPS, и в Chrome, пока сайт не проходит его проверку: манифест, service worker и короткий визит. Пока события нет, кнопку не показывают нарочно, а не по таймеру.

## Правила

- Не коммитить `.env.prod`, SQLite, `media/`, ключи VAPID, DKIM, TLS и токены.
- Не хранить токен в URL `origin`.
- Перед выпуском с миграциями копировать `data/db.sqlite3` и `media/`.
- Значения в `.env.example` — шаблон, не боевые секреты.
