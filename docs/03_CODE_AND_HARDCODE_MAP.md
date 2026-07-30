# 3. Навигация по коду и карта хардкода

## Структура проекта

| Путь | Содержимое |
|---|---|
| `apps/catalog/` | Товары, варианты, фильтры, отзывы, рецепты, настройки сайта, парсер |
| `apps/orders/` | Корзина, оформление, заказы, получатель, повтор заказа, фоновые статусы |
| `apps/payments/` | ЮKassa, локальная модель платежа, webhooks, сверка статусов |
| `apps/delivery/` | Клиент API СДЭК v2, тарифы, ПВЗ, курьер, создание накладной |
| `apps/users/` | Регистрация, вход, OAuth, профиль, адреса, уведомления, баланс, push |
| `apps/blog/` | Журнал, категории, комментарии и статистика просмотров |
| `apps/pages/` | Контентные страницы, сообщество, юридические документы, deploy webhook |
| `apps/warehouse/` | Остатки и складские операции |
| `apps/api/` | REST API |
| `config/settings/` | Настройки Django для base/dev/test/prod |
| `config/urls.py` | Главная карта URL и OAuth callback-маршруты |
| `templates/` | Общие шаблоны, письма, админка и allauth |
| `static/` | Исходная статика проекта |
| `asset/` | Подключённый набор CSS/JS/изображений интерфейса (`STATICFILES_DIRS`) |
| `ref_assets/` | Референсные ресурсы дизайна; не являются runtime-данными пользователей |
| `docker/` | Nginx и вспомогательные Docker-конфиги |
| `tests/` и `apps/*/tests/` | Автоматические тесты |
| `docs/` | Эксплуатационная документация |

Миграции в `apps/*/migrations/` описывают историю схемы и начальные данные. Текущие значения нельзя исправлять редактированием уже применённой миграции: создаётся новая миграция либо меняется объект через админку.

## Карта хардкода

| Что зафиксировано | Где находится | Как менять |
|---|---|---|
| Домены `aspectcoffee.ru`, `www`, публичный IP | `config/settings/prod.py`, `docker/nginx/nginx.conf` | Изменить оба файла, DNS/сертификат и пересобрать контейнеры |
| Привязка Nginx к VPN `10.88.0.1` | `docker-compose.yml` | Изменить `ports`, проверить UFW/HAProxy; ошибочная публикация на `0.0.0.0` откроет сайт наружу |
| Allowlist заказчика `95.31.19.131` | `/etc/haproxy/haproxy.cfg` и UFW, вне Git | Изменить на сервере, проверить конфиг и reload |
| Маршрутизация VPN/сайта | `/etc/haproxy/haproxy.cfg`, `/etc/stunnel/aspect-openvpn.conf`, `/etc/openvpn/server/aspect.conf` | Только через серверный runbook |
| Отправитель СДЭК: Ижевск, код города, адрес | `apps/delivery/cdek.py`: `SENDER_CITY_CODE`, `SENDER_CITY`, `SENDER_ADDRESS` | Изменить код; предпочтительно вынести в `SiteSettings`/env |
| Тарифы и размеры посылки СДЭК | `apps/delivery/cdek.py`: `TARIFF_*`, `DEFAULT_*` | Изменить после сверки с договором СДЭК и теста расчёта |
| Источник каталога Aspect Coffee | `apps/catalog/management/commands/run_parser.py`, `check_images.py`: `BASE_URL` | Изменить код либо отключить задачи; см. документ 5 |
| OAuth endpoints VK ID и Яндекса | `apps/users/oauth_views.py` | Менять только при официальном изменении API провайдера |
| Callback URL OAuth | `config/urls.py`, функции в `apps/users/oauth_views.py` | Синхронно изменить в коде и кабинете провайдера |
| Периодичность Celery | `config/settings/base.py`: `CELERY_BEAT_SCHEDULE` | Изменить секунды/расписание, затем перезапустить `celery-beat` |
| Email From по умолчанию | `config/settings/base.py` | В продакшне переопределять `DEFAULT_FROM_EMAIL` через `.env.prod` |
| Публичный VAPID-ключ по умолчанию | `config/settings/base.py` | Публичная часть не секретна; при ротации менять вместе с приватным ключом |
| Путь deploy script | `DEPLOY_PATH` в `.env.prod`, код `apps/pages/views_webhook.py` | Webhook по умолчанию отключён без `DEPLOY_SECRET` |
| Бренд/заголовки админки | `config/settings/base.py`, `SPECTACULAR_SETTINGS`, `UNFOLD` | Изменить код и проверить кодировку/статические файлы |
| Контакты и ссылки по умолчанию | `apps/catalog/models.py` в `SiteSettings` | Рабочие значения менять через админку; defaults — только для новых БД |
| Юридические реквизиты и Aspect Coffee в историческом контенте | `apps/pages/templates/pages/`, `apps/pages/migrations/0005_*`, записи `LegalDocument` в БД | Текущую публикацию менять в админке; шаблоны/defaults исправлять отдельным коммитом |
| Внешние изображения Aspect Coffee | HTML в `Product.description`, `PromoSlide.background_image_url`, отдельные шаблоны | Перенести в `media/`/`static/` и заменить URL через админку/миграцию |
| Публичные IP ЮKassa для webhook | `docker/nginx/nginx.conf` | Обновлять только по официальной документации ЮKassa |

## Настройки, управляемые из админки

| Раздел/модель | Что управляет |
|---|---|
| `Каталог → Настройки сайта` (`SiteSettings`) | Контакты, тексты, таймаут оплаты, способы доставки, блоки главной |
| `Каталог → Настройки фильтра` | Подписи/параметры фильтра |
| `Каталог → Настройки парсера` (`ParserSetting`) | Автоматический запуск и его служебный интервал |
| `Каталог → Слайды/навигация` | Баннеры и меню |
| `Страницы → Юридические документы` (`LegalDocument`) | Публичная оферта, политика и соглашение |
| `Social accounts → Social applications` (`SocialApp`) | Client ID/secret VK и Яндекс, привязка к домену |
| `Sites → Sites` | Домен, к которому привязаны OAuth-приложения |

Значения из базы имеют приоритет над default-значениями моделей. Изменение default в Python не обновляет уже существующую строку `SiteSettings`.

## Где искать конкретную функцию

| Сценарий | Основные файлы |
|---|---|
| Фильтр → каталог → карточка | `apps/catalog/facets.py`, `filters.py`, `views.py`, `templates/catalog/` |
| Корзина/регистрация/заказ | `apps/orders/cart_service.py`, `checkout_service.py`, `views.py`, `templates/orders/basket.html` |
| Успешная оплата/статус заказа | `apps/payments/services.py`, `views.py`, `tasks.py`, `apps/orders/tasks.py` |
| СДЭК ПВЗ/дверь/накладная | `apps/delivery/cdek.py`, `apps/orders/views.py`, `apps/orders/tasks.py` |
| Другой получатель/повтор заказа | `apps/orders/models.py`, `reorder.py`, `apps/users/templates/users/order_detail.html` |
| OAuth VK/Яндекс | `apps/users/oauth_views.py`, `adapters.py`, `config/urls.py` |
| Email и уведомления | `apps/users/notifications.py`, `apps/users/tasks.py`, `apps/orders/tasks.py` |
| Отзывы/рецепты/сообщество | `apps/catalog/models.py`, `tasks.py`, `apps/pages/models.py`, `views.py` |
| Поиск каталога/журнала | `apps/catalog/views.py`, `apps/blog/views.py`, `static/asset/js/custom.js` |

## Команды поиска хардкода

```bash
rg -n "aspectcoffee|aspectcoffee|45\.155\.52\.48|10\.88\.0\.1|95\.31\.19\.131" .
rg -n "https?://" apps config templates static
rg -n "config\(|os\.environ|getenv\(" apps config
rg -n "CLIENT_ID|CLIENT_SECRET|SECRET_KEY|API_KEY|TOKEN|PASSWORD" apps config
```

При поиске исключать `.git`, `.env*`, `media`, `staticfiles`, базы и резервные копии. Результаты с секретами нельзя вставлять в тикеты или чат.
