# 5. Почта, парсер и фоновые службы

Актуально на 19.07.2026.

## Почтовая схема

```text
Django web/celery
    |
    | SMTP 172.18.0.1:587, только Docker bridge
    v
Postfix на host
    |
    | OpenDKIM selector=default, socket 127.0.0.1:8891
    v
Почтовый сервер получателя
```

Входящие письма домена обслуживает VK WorkSpace/Mail.ru через MX `emx.mail.ru`. Исходящие автоматические письма сайта отправляет локальный Postfix с IP `45.155.52.48`.

### Runtime-настройки Django

| Параметр | Текущее значение |
|---|---|
| `EMAIL_BACKEND` | `django.core.mail.backends.smtp.EmailBackend` |
| `EMAIL_HOST` | `172.18.0.1` |
| `EMAIL_PORT` | `587` |
| `EMAIL_USE_TLS` | `False` |
| `EMAIL_USE_SSL` | `False` |
| SMTP auth | не используется |
| `DEFAULT_FROM_EMAIL` | `Aspect Coffee <info@aspectcoffee.ru>` |

Отсутствие TLS/auth допустимо только для внутреннего Docker-to-host канала: UFW разрешает `587/tcp` исключительно сети `172.18.0.0/16`. Нельзя открывать этот порт всему интернету.

### Postfix и OpenDKIM

| Компонент | Путь/параметр |
|---|---|
| Postfix main | `/etc/postfix/main.cf` |
| Postfix services | `/etc/postfix/master.cf` |
| `myhostname` | `mail.aspectcoffee.ru` |
| `mydomain`/`myorigin` | `aspectcoffee.ru` |
| IP stack | IPv4 |
| DKIM milter | `inet:localhost:8891` |
| OpenDKIM config | `/etc/opendkim.conf` |
| DKIM selector | `default` |
| DKIM key | `/etc/opendkim/keys/aspectcoffee.ru/` — приватный файл не копировать |

### DNS на 19.07.2026

| Запись | Состояние |
|---|---|
| MX | одна запись `emx.mail.ru`, priority `10` — корректно |
| SPF | `v=spf1 ip4:45.155.52.48 include:_spf.mail.ru ~all` — опубликован |
| PTR | `45.155.52.48 → mail.aspectcoffee.ru` — опубликован |
| DMARC | `v=DMARC1; p=none; rua=mailto:info@aspectcoffee.ru` — мониторинг |
| DKIM `default._domainkey` | временно отсутствует; публикация нового SHA-256/RSA ключа запрошена у DNS-поддержки |

После публикации DKIM публичный ключ обязан соответствовать приватному ключу OpenDKIM. Для исходящей почты VK WorkSpace может использовать отдельный selector `mailru`; он не должен заменять серверный `default`.

Проверка DNS:

```bash
dig +short MX aspectcoffee.ru
dig +short TXT aspectcoffee.ru
dig +short TXT default._domainkey.aspectcoffee.ru
dig +short TXT _dmarc.aspectcoffee.ru
dig +short -x 45.155.52.48
```

Проверка служб и отправки:

```bash
systemctl status postfix opendkim
postfix check
opendkim-testkey -d aspectcoffee.ru -s default -vvv
tail -f /var/log/mail.log

cd /opt/aspectcoffee
docker compose exec -T web python manage.py shell -c '
from django.core.mail import send_mail
print(send_mail("Aspect Coffee SMTP test", "Test", None, ["controlled-test@example.com"]))
'
```

Тест отправлять только на контролируемый ящик. В заголовке полученного письма проверить `spf=pass`, `dkim=pass`, `dmarc=pass`.

## Парсер каталога

### Состав

| Файл | Назначение |
|---|---|
| `apps/catalog/management/commands/run_parser.py` | Получение каталога/товаров/изображений с `shop.tastycoffee.ru` |
| `apps/catalog/tasks.py` | Celery wrapper и проверка флага автоматического обновления |
| `apps/catalog/models.py` → `ParserSetting` | Флаг, интервал, время последнего запуска |
| `apps/catalog/models.py` → `ParserLog` | История выполнения |
| `apps/catalog/admin.py` | Настройки, ручная кнопка и логи |
| `check_images.py` | Восстановление пропавших локальных изображений из внешнего источника |

### Текущее состояние

- `is_auto_update_enabled=False`;
- интервал установлен в максимальное значение `9223372036854775807` часов;
- последний успешный запуск — 18.07.2026 09:49 по московскому времени;
- активных/ожидающих Celery-задач парсера при проверке не было;
- старый `ParserLog id=3` от 26.05.2026 ошибочно остался в `running`, но реального процесса за ним нет;
- все 381 основных изображения товара находятся локально.

Автоматическая задача `catalog-parser-sync` всё ещё отправляется Celery Beat раз в сутки, но `run_catalog_parser_task` проверяет флаг и возвращает `Disabled` до любого HTTP-запроса.

Важно: ручная кнопка админки вызывает задачу с `force=True`, поэтому запускает парсер даже при выключенном переключателе.

### Отдельная проверка изображений

`check-product-images` выполняется раз в сутки независимо от флага парсера. Пока все файлы присутствуют, задача только проверяет локальный диск. Если изображение исчезнет, она обратится к `shop.tastycoffee.ru` и попробует скачать файл заново.

На фронте также могут оставаться клиентские запросы к внешнему источнику каталога:

- изображения внутри `Product.description`;
- `PromoSlide.background_image_url`;
- внешние ссылки/контакты.

Это запросы браузера посетителя, а не серверного парсера.

### Обычное выключение

В админке:

```text
Каталог → Настройки парсера → Автоматическое обновление = выключено
```

Этого достаточно, чтобы ежедневный основной парсер не выполнял HTTP-запросы. Ручная кнопка остаётся доступной персоналу.

### Полная изоляция от `shop.tastycoffee.ru`

Если запрещены абсолютно любые соединения:

1. Выключить `ParserSetting.is_auto_update_enabled`.
2. Удалить/закомментировать `catalog-parser-sync` и `check-product-images` в `CELERY_BEAT_SCHEDULE`.
3. Убрать или ограничить permission ручного `run_parser_view`/admin action.
4. Перезапустить `celery` и `celery-beat`.
5. Перенести внешние изображения из описаний и слайдов в локальное `media/`/`static/`.
6. При необходимости запретить исходящий DNS/IP на уровне firewall/proxy.

```bash
docker compose up -d --force-recreate celery celery-beat
docker compose exec -T celery celery -A config inspect active
docker compose exec -T celery celery -A config inspect reserved
docker compose exec -T celery celery -A config inspect scheduled
```

## Celery Beat

| Задача | Период | Назначение |
|---|---:|---|
| `sync-pending-yookassa-payments` | 60 секунд | Сверка ожидающих платежей с ЮKassa |
| `check-cdek-tracking` | 1 час | Обновление статусов отправлений СДЭК |
| `update-product-ratings` | 24 часа | Пересчёт рейтингов товаров |
| `catalog-parser-sync` | 24 часа | Парсер; при выключенном флаге завершается без HTTP |
| `check-product-images` | 24 часа | Проверка локальных изображений; скачивание только отсутствующих |

Изменение `ParserSetting.update_interval_hours` не изменяет расписание Celery Beat: фактический период сейчас захардкожен в `config/settings/base.py`. Чтобы поле интервала действительно управляло расписанием, потребуется отдельная доработка dynamic schedule.

## Диагностика фоновых задач

```bash
cd /opt/aspectcoffee
docker compose ps
docker compose logs --since=24h celery celery-beat
docker compose exec -T celery celery -A config inspect active
docker compose exec -T celery celery -A config inspect reserved
docker compose exec -T celery celery -A config inspect scheduled
```

Лог в базе со статусом `running` не доказывает наличие процесса. Источником истины являются Celery inspect, процессы контейнера и свежие логи.

## Другие уведомления

Уведомления формируются в `apps/users/notifications.py`, `apps/users/tasks.py`, `apps/orders/tasks.py` и task-модулях каталога/страниц. Один сценарий может создавать:

- email через SMTP;
- уведомление-колокольчик в `UserNotification`;
- browser push при наличии активной подписки.

При диагностике проверять отдельно каждый канал и таблицу `EmailLog`, потому что успешное создание колокольчика не означает успешную SMTP-доставку.
