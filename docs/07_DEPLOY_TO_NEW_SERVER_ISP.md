# 7. Инструкция по передаче репозитория и деплою Aspect Coffee на новый сервер (ISPmanager 6)

Актуально на 06.08.2026.

## Назначение документа

Данный документ содержит точную техническую спецификацию и пошаговый регламент развёртывания приложения **Aspect Coffee** (`aspectcoffee.ru`) на новом VDS/VPS сервере под управлением панели **ISPmanager 6**, составленный на основе полного аудита рабочего окружения `/opt/aspectcoffee`.

---

## 1. Архитектура и стек приложения

Приложение Aspect Coffee реализовано на **Django 5.2 (Python 3.12)** и разворачивается в **Docker Compose** с шестью взаимодействующими контейнерами:

| Контейнер | Образ / База | Назначение | Порт / Тома |
|---|---|---|---|
| `web` | `aspectcoffee-web` (Dockerfile) | Django / Gunicorn WSGI сервер | Порт `8000` (внутренний), тома `db.sqlite3` и `media` |
| `celery` | `aspectcoffee-web` | Фоновый воркер задач (`concurrency=1`) | Том `db.sqlite3`, `media` |
| `celery-beat` | `aspectcoffee-web` | Планировщик периодических задач | Том `db.sqlite3`, `media` |
| `redis` | `redis:7-alpine` | Брокер сообщений для Celery | Внутренний |
| `nginx` | `nginx:1.25-alpine` | TLS 1.2/1.3, Nginx Reverse Proxy, статика | Порты `80` и `443` |
| `certbot` | `certbot/certbot` | Авто-обновление Let's Encrypt SSL | Тома `certbot_www`, `certbot_conf` |

---

## 2. Первичное поднятие сервера и панели ISPmanager 6

### 2.1 Минимальные системные требования
* **ОС:** Ubuntu 22.04 LTS (x86_64) — чистая система.
* **Ресурсы:** 2–4 CPU, 4 ГБ RAM, 30+ ГБ NVMe/SSD.
* **Сетевые порты:** `80` (HTTP), `443` (HTTPS), `22` (SSH), `1500` (ISPmanager).

### 2.2 Установка панели ISPmanager 6
1. Подключитесь к новому серверу под пользователем `root`:
   ```bash
   ssh root@<IP_НОВОГО_СЕРВЕРА>
   ```
2. Установите панель ISPmanager 6:
   ```bash
   wget https://download.ispmanager.com/install.sh -O install.sh
   sh install.sh --ispmanager-lite
   ```
3. Откройте панель в браузере: `https://<IP_НОВОГО_СЕРВЕРА>:1500/ispmgr` и активируйте лицензию.

---

## 3. Подготовка окружения (Docker Engine & Git)

1. Подключитесь по SSH к новому серверу и установите Docker Engine:
   ```bash
   curl -fsSL https://get.docker.com | sh
   apt-get install -y docker-compose-plugin git curl
   ```

2. Проверьте работоспособность Docker:
   ```bash
   docker --version
   docker compose version
   ```

---

## 4. Передача и клонирование репозитория

1. **Генерация SSH Deploy Key:**
   На новом сервере выполните:
   ```bash
   ssh-keygen -t ed25519 -C "deploy@aspectcoffee.ru" -f /root/.ssh/id_ed25519_deploy -N ""
   cat /root/.ssh/id_ed25519_deploy.pub
   ```
   Добавьте публичный ключ в профиле репозитория **GitVerse** (`https://gitverse.ru/svpromo/AspectCoffee.git`) в разделе **Настройки → Ключи деплоя (Deploy Keys)**.

2. **Клонирование проекта в `/opt/aspectcoffee`:**
   ```bash
   mkdir -p /opt
   cd /opt
   git clone git@gitverse.ru:svpromo/AspectCoffee.git aspectcoffee
   cd /opt/aspectcoffee
   ```

---

## 5. Конфигурация параметров окружения (`.env.prod`)

Скопируйте шаблон и настройте боевые параметры:
```bash
cd /opt/aspectcoffee
cp .env.example .env.prod
nano .env.prod
```

Файл `.env.prod` должен содержать:
```env
DEBUG=False
SECRET_KEY=<ДЛИННЫЙ_СЛУЧАЙНЫЙ_СЕКРЕТНЫЙ_КЛЮЧ>
ALLOWED_HOSTS=aspectcoffee.ru,www.aspectcoffee.ru,10.88.0.1,localhost,127.0.0.1

# SQLite база данных
DATABASE_URL=sqlite:////app/data/db.sqlite3

# Сервис оплаты ЮKassa
YOOKASSA_SHOP_ID=<ID_МАГАЗИНА_ЮКАССА>
YOOKASSA_SECRET_KEY=<СЕКРЕТНЫЙ_КЛЮЧ_ЮКАССА>

# СДЭК доставка
CDEK_CLIENT_ID=<CDEK_ID>
CDEK_CLIENT_SECRET=<CDEK_SECRET>
CDEK_TEST_MODE=false
```

---

## 6. Сборка и запуск контейнеров Docker Compose

Выполните регламентный запуск в каталоге `/opt/aspectcoffee`:

```bash
cd /opt/aspectcoffee

# 1. Сборка Docker-образов приложения
docker compose build

# 2. Выполнение миграций SQLite
docker compose run --rm web python manage.py migrate

# 3. Сбор статических файлов
docker compose run --rm web python manage.py collectstatic --noinput

# 4. Запуск всех фоновых сервисов
docker compose up -d

# 5. Проверка статуса контейнеров
docker compose ps
```

---

## 7. Настройка Nginx и SSL в панели ISPmanager 6

1. В веб-интерфейсе ISPmanager перейдите в **Сайты → Создать сайт**:
   - **Домен:** `aspectcoffee.ru`
   - **IP-адрес:** IP вашего сервера
   - **SSL-сертификат:** Включить Let's Encrypt (автоматическое перенаправление HTTP → HTTPS).

2. В разделе **Конфигурация Nginx** укажите правила проксирования и отдачи статики из объемов Docker:
   ```nginx
   # Статика и Медиа (прямая отдача Nginx)
   location /static/ {
       alias /opt/aspectcoffee/staticfiles/;
       expires 365d;
       add_header Cache-Control "public, immutable";
   }

   location /media/ {
       alias /opt/aspectcoffee/media/;
       expires 30d;
       add_header Cache-Control "public";
   }

   # Ограничение IP для вебхуков ЮKassa
   location = /payments/webhook/ {
       allow 185.71.76.0/27;
       allow 185.71.77.0/27;
       allow 77.75.153.0/25;
       allow 77.75.156.11;
       allow 77.75.156.35;
       allow 77.75.154.128/25;
       deny all;
       proxy_pass http://127.0.0.1:8000;
       proxy_set_header Host $host;
       proxy_set_header X-Real-IP $remote_addr;
       proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
       proxy_set_header X-Forwarded-Proto $scheme;
   }

   # Основное Django приложение
   location / {
       proxy_pass http://127.0.0.1:8000;
       proxy_set_header Host $host;
       proxy_set_header X-Real-IP $remote_addr;
       proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
       proxy_set_header X-Forwarded-Proto $scheme;
       client_max_body_size 20M;
   }
   ```

---

## 8. Скрипт автоматического обновления (Auto-Deploy)

Для накатывания обновлений с ветки `main` создайте скрипт `/opt/aspectcoffee/deploy.sh`:

```bash
#!/bin/bash
set -e
cd /opt/aspectcoffee
git pull origin main
docker compose build web
docker compose run --rm web python manage.py migrate
docker compose run --rm web python manage.py collectstatic --noinput
docker compose up -d
docker compose ps
```

Сделайте файл исполняемым:
```bash
chmod +x /opt/aspectcoffee/deploy.sh
```

---

## 9. Контрольный чек-лист проверки после деплоя

- [ ] `docker compose ps` показывает 5 активных контейнеров (`web`, `celery`, `celery-beat`, `redis`, `nginx`).
- [ ] Сайт доступен по HTTPS: `https://aspectcoffee.ru`.
- [ ] Статические файлы (`/static/`) и изображения товаров (`/media/`) загружаются.
- [ ] Команда проверки `docker compose exec -T web python manage.py check --deploy` проходит без критических ошибок.
- [ ] Оплата через ЮKassa и расчет доставки СДЭК функционируют.
