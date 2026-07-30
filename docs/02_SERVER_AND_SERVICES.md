# 2. Сервер и поднятые сервисы

Актуально на 19.07.2026. Секреты, закрытые ключи и содержимое пользовательской базы здесь не приводятся.

## Характеристики сервера

| Параметр | Текущее значение |
|---|---|
| ОС | Ubuntu 22.04.5 LTS |
| Ядро | Linux 5.15.0-185-generic |
| CPU | 2 vCPU |
| RAM | 1.9 GiB |
| Swap | 2.0 GiB |
| Диск | 40 GiB, занято около 84% на дату проверки |
| Публичный IPv4 | `45.155.52.48` |
| VPN-интерфейс | `tun0`, сервер `10.88.0.1/24` |
| Каталог приложения | `/opt/aspectcoffee` |

При заполнении диска более 90% возможны сбои SQLite, Docker и журналов. Необходимо контролировать `df -h`, размер Docker-слоёв, медиа и резервных копий.

## Схема доступа

```text
Интернет :443
    |
    v
HAProxy (45.155.52.48)
    |-- IP 95.31.19.131 --> Nginx сайта (10.88.0.1:443)
    `-- остальные IP ----> stunnel (127.0.0.1:8443)
                              `--> OpenVPN (127.0.0.1:1194)

VPN-клиент 10.88.0.0/24
    |-- SSH 10.88.0.1:22
    |-- HTTP 10.88.0.1:80
    `-- HTTPS 10.88.0.1:443
```

Публичный порт 80 HAProxy разрешает только заказчику `95.31.19.131`. Контейнер Nginx опубликован только на `10.88.0.1`, поэтому доступ к сайту для остальных пользователей появляется после VPN либо изменения правил HAProxy/UFW.

## Системные службы

| Служба | Назначение | Основные конфиги/данные |
|---|---|---|
| `docker` | Контейнеры приложения | `/opt/aspectcoffee/docker-compose.yml`, `/var/lib/docker/` |
| `haproxy` | Разделение публичного HTTPS между сайтом заказчика и VPN | `/etc/haproxy/haproxy.cfg` |
| `stunnel4` | TLS-обёртка для OpenVPN | `/etc/stunnel/aspect-openvpn.conf` |
| `openvpn` | VPN `10.88.0.0/24` | `/etc/openvpn/server/aspect.conf`, PKI в `/etc/openvpn/pki-build/` |
| `ssh` | Администрирование | `/etc/ssh/sshd_config`, ключи пользователей в `~/.ssh/authorized_keys` |
| `ufw` | Фильтрация портов | `/etc/ufw/`, управление командой `ufw status numbered` |
| `postfix` | Исходящая SMTP-почта сайта | `/etc/postfix/main.cf`, `/etc/postfix/master.cf` |
| `opendkim` | DKIM-подпись исходящей почты | `/etc/opendkim.conf`, ключ в `/etc/opendkim/keys/aspectcoffee.ru/` |
| `redis-server` | Локальный host Redis, не используемый Docker Compose приложения | `/etc/redis/redis.conf` |

Служба UFW может показываться `inactive` в `systemctl` после загрузки правил, при этом `ufw status` корректно показывает `Status: active`. Источником истины являются активные правила UFW и `iptables/nftables`.

## Действующие правила UFW

- публичный `443/tcp` — вход в HAProxy/OpenVPN;
- `22`, `80`, `443` на `tun0` — для VPN-клиентов;
- публичные `22` и `80` — только от `95.31.19.131`;
- `587/tcp` — только из Docker-сети `172.18.0.0/16` для отправки почты;
- IPv6 разрешает публичный `443`, а администрирование — через `tun0`.

Перед изменением firewall необходимо держать открытой существующую SSH-сессию и проверять новый доступ второй сессией, чтобы не заблокировать сервер.

## Docker Compose

Версии на дату проверки: Docker 29.5.3, Docker Compose 5.1.4.

| Контейнер | Образ/команда | Назначение | Внешний порт |
|---|---|---|---|
| `web` | локальный `aspectcoffee-web`, Gunicorn, 4 workers | Django | нет, только `8000` внутри сети |
| `celery` | тот же образ, concurrency `1` | Фоновые задания | нет |
| `celery-beat` | тот же образ | Расписание заданий | нет |
| `redis` | `redis:7-alpine` | Broker/результаты Celery | нет |
| `nginx` | `nginx:1.25-alpine` | TLS, статика, reverse proxy, rate limits | `10.88.0.1:80/443` |
| `certbot` | `certbot/certbot` | Обновление сертификата каждые 6 часов | нет |

Зависимости и ключевые параметры находятся в:

- `docker-compose.yml` — контейнеры, volumes, команды, привязка портов;
- `Dockerfile` — Python 3.12, зависимости, Gunicorn;
- `docker/nginx/nginx.conf` — домены, TLS, лимиты, статика, webhooks;
- `config/settings/base.py` — Django-приложения и общие настройки;
- `config/settings/prod.py` — SQLite, безопасность, логирование, Redis;
- `.env.prod` — реальные секреты и адреса, файл не хранится в Git.

## Постоянные данные

| Данные | Путь на сервере | Подключение в контейнер |
|---|---|---|
| База SQLite | `/opt/aspectcoffee/db.sqlite3` | `/app/data/db.sqlite3` |
| Пользовательские файлы | `/opt/aspectcoffee/media/` | `/app/media/` |
| Собранная статика | `/opt/aspectcoffee/staticfiles/` | Nginx `/app/staticfiles/` |
| Переменные среды | `/opt/aspectcoffee/.env.prod` | `env_file` для web/celery/beat |
| Сертификаты сайта | Docker volume `certbot_conf` | `/etc/letsencrypt` в Nginx/Certbot |

SQLite подключается в `web`, `celery` и `celery-beat`. Celery намеренно работает с concurrency `1`, чтобы уменьшить вероятность `database is locked`. Для дальнейшего роста рекомендуется PostgreSQL и отдельное резервное копирование.

## Nginx

`docker/nginx/nginx.conf` содержит:

- перенаправление HTTP и `www` на `https://aspectcoffee.ru`;
- TLS 1.2/1.3 и HSTS;
- раздачу `/static/` и `/media/` напрямую;
- rate limits для общего трафика, API и авторизации;
- проксирование `/admin/` в Django;
- allowlist официальных IP ЮKassa для `/payments/webhook/` и `/balance/webhook/`;
- ACME location для Certbot;
- максимальный размер тела запроса 20 MiB.

## HAProxy, stunnel и OpenVPN

- HAProxy: `/etc/haproxy/haproxy.cfg`.
- stunnel: `/etc/stunnel/aspect-openvpn.conf`.
- OpenVPN: `/etc/openvpn/server/aspect.conf`.
- VPN слушает `127.0.0.1:1194/tcp`, сеть клиентов `10.88.0.0/24`.
- Используются SHA-256 и AES-GCM; сертификаты и ключи в Git не копируются.

После изменения конфигов:

```bash
haproxy -c -f /etc/haproxy/haproxy.cfg
systemctl reload haproxy

stunnel -version
systemctl restart stunnel4

openvpn --config /etc/openvpn/server/aspect.conf --test-crypto
systemctl restart openvpn
```

Перезапуск OpenVPN/HAProxy может оборвать доступ. Его проводят только при наличии резервного доступа через панель VM.

## Команды эксплуатации

```bash
cd /opt/aspectcoffee
docker compose ps
docker compose logs --since=1h web celery celery-beat nginx
docker compose exec -T web python manage.py check --deploy
docker compose exec -T web python manage.py showmigrations
docker compose exec -T web python manage.py migrate --plan
ss -lntup
ufw status numbered
df -h
```

Для применения новой версии:

```bash
docker compose build
docker compose run --rm web python manage.py migrate
docker compose run --rm web python manage.py collectstatic --noinput
docker compose up -d
```

## Известный технический долг

На 19.07.2026 полный набор из 21 Django-теста проходит успешно. Команда
`check --deploy` дополнительно показывает предупреждения, которые не блокируют
работу сайта:

- `ckeditor.W001`: пакет `django-ckeditor` содержит CKEditor 4.22.1, для которого
  прекращена бесплатная поддержка безопасности; редактор следует отдельной
  задачей заменить на CKEditor 5 либо поддерживаемую LTS-версию;
- предупреждения `drf_spectacular` относятся к описанию схемы API и устраняются
  добавлением типов/serializer-классов, не меняя рабочие API-сценарии;
- `security.W008` ожидаем при текущей архитектуре: HTTP перенаправляет на HTTPS
  Nginx, поэтому `SECURE_SSL_REDIRECT=False` внутри Django;
- `security.W009` требует плановой замены действующего `SECRET_KEY` на длинное
  случайное значение. Замена завершит текущие пользовательские сессии, поэтому
  её проводят в согласованное окно и только в серверном `.env.prod`.

## Журналы

- Django/Gunicorn/Celery/Nginx: `docker compose logs <service>`;
- Postfix: `/var/log/mail.log`;
- OpenDKIM: `/var/log/mail.log` и syslog;
- HAProxy: journald/syslog;
- stunnel: `/var/log/stunnel4/aspect-openvpn.log`;
- OpenVPN: journald, status `/run/openvpn-server/status.log`;
- UFW: `/var/log/ufw.log`, если логирование включено.
