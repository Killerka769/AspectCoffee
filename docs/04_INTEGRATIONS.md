# 4. Интеграции и переключение тестовых/боевых API

Актуально на 19.07.2026. Реальные ключи находятся только в `/opt/aspectcoffee/.env.prod` или базе данных и в Git не включены.

## Общий принцип

1. Для тестовой и боевой среды использовать разные учётные записи/ключи.
2. Менять связанные параметры комплектом: ID, secret, endpoint, callback/webhook.
3. После изменения перезапускать `web`, `celery` и `celery-beat`.
4. Проверять интеграцию отдельным тестовым заказом/пользователем.
5. Никогда не выводить secret в логи или диагностику.

```bash
cd /opt/aspectcoffee
docker compose up -d --force-recreate web celery celery-beat
docker compose logs --since=10m web celery
```

## Матрица интеграций

| Интеграция | Где лежит конфиг | Как переключить test/live | Основные входящие URL |
|---|---|---|---|
| ЮKassa | `.env.prod`: `YOOKASSA_SHOP_ID`, `YOOKASSA_SECRET_KEY` | Подставить пару ключей тестового либо настоящего магазина | `/payments/webhook/`, `/balance/webhook/` |
| СДЭК API v2 | `.env.prod`: `CDEK_CLIENT_ID`, `CDEK_CLIENT_SECRET`, `CDEK_API_URL`, `CDEK_TEST_MODE` | Одновременно заменить credentials и endpoint среды | Исходящие запросы, входящего webhook нет |
| Яндекс OAuth | Django DB: `SocialApp` provider `yandex`, привязка к `Site` | Создать/выбрать приложение нужной среды и заменить Client ID/secret в админке | `/accounts/yandex/login/callback/` |
| VK ID OAuth | Django DB: `SocialApp` provider `vk`, привязка к `Site` | Заменить Client ID/secret и redirect URI приложения | `/accounts/vk/login/callback/` |
| SMTP | `.env.prod` + Postfix/OpenDKIM на host | Для внешнего SMTP заменить host/port/auth/TLS; текущая схема использует локальный Postfix | SMTP не имеет HTTP callback |
| Web Push | `.env.prod`/файл: `WEBPUSH_VAPID_*` | Сгенерировать отдельную VAPID-пару; заменить публичную и приватную части вместе | Browser push endpoint хранится у пользователя |
| Sentry | `.env.prod`: `SENTRY_DSN`, `ENVIRONMENT` | Разные DSN/project/environment | Исходящие события |
| GitVerse deploy webhook | `.env.prod`: `DEPLOY_SECRET`, `DEPLOY_PATH` | Разные секреты; без секрета endpoint отключён | URL определяется в `apps/pages/urls.py` |

## ЮKassa

Код:

- `apps/payments/services.py` — доверенная повторная проверка платежа через API;
- `apps/payments/views.py` — создание платежа и webhook;
- `apps/payments/tasks.py` — синхронизация ожидающих платежей;
- `apps/orders/tasks.py` — уведомление и создание накладной после оплаты;
- `docker/nginx/nginx.conf` — allowlist IP webhook.

Переключение выполняется только заменой пары:

```dotenv
YOOKASSA_SHOP_ID=<shop-id-нужной-среды>
YOOKASSA_SECRET_KEY=<secret-нужной-среды>
```

API URL задаёт SDK ЮKassa и в проекте отдельно не переопределяется. Для тестов используются ID и secret тестового магазина; для реальных платежей — настоящего. Это соответствует [официальной инструкции ЮKassa по тестированию](https://yookassa.ru/developers/payment-acceptance/testing-and-going-live/testing).

После переключения проверить:

1. создание платежа и redirect;
2. запись `Payment.yookassa_id`;
3. webhook и повторную проверку суммы/статуса;
4. переход заказа в `paid`;
5. повторную доставку того же webhook — она не должна дублировать операцию;
6. фоновую сверку `sync_pending_payments`.

## СДЭК

Код:

- `apps/delivery/cdek.py` — основной API v2 client;
- `apps/orders/views.py` — расчёт/валидация ПВЗ и доставки до двери;
- `apps/orders/tasks.py` — создание накладной и трекинг;
- `apps/orders/models.py` — коды доставки и поля СДЭК.

Текущая боевая конфигурация использует:

```dotenv
CDEK_API_URL=https://api.cdek.ru/v2
CDEK_TEST_MODE=False
```

При переходе в тестовую среду заменить `CDEK_API_URL`, `CDEK_CLIENT_ID` и `CDEK_CLIENT_SECRET` на значения, выданные тестовым кабинетом СДЭК. Нельзя использовать тестовые credentials с боевым endpoint или наоборот.

Отправитель и размеры посылки пока находятся в коде `apps/delivery/cdek.py`:

- `SENDER_CITY_CODE`;
- `SENDER_CITY`;
- `SENDER_ADDRESS`;
- `DEFAULT_LENGTH`, `DEFAULT_WIDTH`, `DEFAULT_HEIGHT`;
- `TARIFF_WAREHOUSE_TO_*`.

После переключения проверить получение токена, поиск города, ПВЗ, расчёт двух тарифов, создание заказа, трек-номер и повторное выполнение задачи создания накладной.

## Яндекс OAuth

Реквизиты берутся из `django-allauth` модели `SocialApp`, а не напрямую из `YANDEX_CLIENT_ID`/`YANDEX_CLIENT_SECRET` в `.env.prod`.

Путь в админке:

```text
/admin/socialaccount/socialapp/
```

Для приложения Yandex должны быть заполнены Client ID, Secret и привязка к `Site` с доменом `aspectcoffee.ru`.

Боевой redirect URI:

```text
https://aspectcoffee.ru/accounts/yandex/login/callback/
```

Для тестового домена создать отдельное OAuth-приложение и отдельную запись `SocialApp`. В коде используются русская страница авторизации `https://oauth.yandex.ru/authorize` и scopes из `SOCIALACCOUNT_PROVIDERS` в `config/settings/base.py`. Регистрация и Redirect URI выполняются в кабинете Яндекс OAuth: [официальная документация](https://yandex.ru/dev/id/doc/ru/register-client).

## VK ID OAuth

Реквизиты также хранятся в `SocialApp` provider `vk` и должны быть привязаны к текущему `Site`.

Боевой redirect URI:

```text
https://aspectcoffee.ru/accounts/vk/login/callback/
```

Код `apps/users/oauth_views.py` использует VK ID OAuth 2.1 + PKCE:

- authorize: `https://id.vk.ru/authorize`;
- token: `https://id.vk.ru/oauth2/auth`;
- user info: `https://id.vk.ru/oauth2/user_info`.

Для тестовой среды создаётся отдельное приложение VK и отдельная запись `SocialApp`. После замены проверить redirect URI, state, PKCE challenge, callback и повторный вход существующего пользователя.

Переменные `VK_APP_ID`, `VK_API_SECRET`, `YANDEX_CLIENT_ID`, `YANDEX_CLIENT_SECRET`, если они остались в старом `.env.prod`, являются наследием прежней настройки и текущими OAuth views автоматически не читаются. Источником истины является `SocialApp` в базе.

## Web Push

Настройки:

```dotenv
WEBPUSH_VAPID_PRIVATE_KEY=/run/secrets/vapid_private.pem
WEBPUSH_VAPID_PUBLIC_KEY=<public-key>
WEBPUSH_VAPID_SUBJECT=mailto:info@aspectcoffee.ru
```

Приватный ключ запрещено хранить в Git или Docker image. При ротации старые browser subscriptions могут перестать работать, поэтому пользователям потребуется повторная подписка.

## Sentry

```dotenv
SENTRY_DSN=
ENVIRONMENT=production
```

Пустой `SENTRY_DSN` полностью отключает отправку. Для stage/prod должны использоваться разные проекты или как минимум разные `ENVIRONMENT`.

## Deploy webhook

Файл: `apps/pages/views_webhook.py`.

```dotenv
DEPLOY_SECRET=<long-random-secret>
DEPLOY_PATH=/opt/aspectcoffee
```

Без `DEPLOY_SECRET` webhook отвечает `503` и ничего не запускает. Секрет должен совпадать с HMAC SHA-256 secret в GitVerse. Скрипт `deploy.sh` должен существовать, принадлежать отдельному deploy-пользователю и выполнять только заранее определённые команды. Запуск webhook от root не рекомендуется.

## Безопасная проверка конфигурации

Проверять только наличие значений, не печатая их:

```bash
docker compose exec -T web python manage.py shell -c '
from django.conf import settings
for name in ("YOOKASSA_SHOP_ID", "YOOKASSA_SECRET_KEY", "CDEK_CLIENT_ID", "CDEK_CLIENT_SECRET", "SENTRY_DSN"):
    print(name, bool(getattr(settings, name, "")))
'
```

OAuth:

```bash
docker compose exec -T web python manage.py shell -c '
from allauth.socialaccount.models import SocialApp
print([(a.provider, bool(a.client_id), bool(a.secret), list(a.sites.values_list("domain", flat=True))) for a in SocialApp.objects.all()])
'
```
