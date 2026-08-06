# Инструкция по передаче репозитория и деплою Aspect Coffee на новый сервер (ISPmanager 6)

Данный документ разработан для передачи продакшн-репозитория и полной настройки деплоя приложения **Aspect Coffee** (`aspectcoffee.ru`) на любой новый VDS/VPS сервер под управлением панели **ISPmanager 6**.

---

## 1. Поднятие и первичная настройка сервера с панелью ISPmanager

### 1.1 Требования к серверу (Hardware & OS)
* **ОС:** Ubuntu 22.04 LTS (x86_64) — чистая система без предустановленного веб-сервера.
* **Ресурсы:** Минимум 2 CPU, 2–4 ГБ RAM, SSD/NVMe диск от 30 ГБ.
* **Сетевые порты:** Открытые 80 (HTTP), 443 (HTTPS), 22 (SSH), 1500 (ISPmanager).

### 1.2 Установка панели ISPmanager 6
1. Подключитесь к чистому серверу по SSH под пользователем `root`:
   ```bash
   ssh root@<IP_НОВОГО_СЕРВЕРА>
   ```
2. Запустите официальный скрипт установки ISPmanager 6:
   ```bash
   wget https://download.ispmanager.com/install.sh -O install.sh
   sh install.sh --ispmanager-lite
   ```
3. После завершения установки перейдите в веб-интерфейс панели:
   `https://<IP_НОВОГО_СЕРВЕРА>:1500/ispmgr`
4. Авторизуйтесь под логином `root` и активируйте лицензию.

---

## 2. Настройка окружения сервера (Environment Setup)

### 2.1 Создание пользователя и сайта в ISPmanager
1. В левом меню перейдите в **Пользователи** -> **Создать пользователя** (например, `aspect_user`).
2. В меню **Сайты** -> **Создать сайт**:
   * **Доменное имя:** `aspectcoffee.ru` (или поддомен для тестов).
   * **Владелец:** `aspect_user`.
   * **Корневая директория:** `/var/www/aspect_user/data/www/aspectcoffee.ru`.
3. Вкладка **SSL-сертификаты** -> Включить бесплатный SSL-сертификат **Let's Encrypt** и автоматически включить перенаправление HTTP -> HTTPS.

### 2.2 Установка Runtime зависимостей (Node.js & Process Manager)
Подключитесь к серверу по SSH и установите рабочее окружение:

```bash
# Установка Node.js v20 LTS
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
apt-get install -y nodejs git build-essential

# Установка глобального менеджера процессов PM2
npm install -g pm2

# Проверка версий
node -v
npm -v
pm2 -v
```

### 2.3 Настройка Базы Данных и Конфигурации (`.env`)
1. В ISPmanager перейдите в **Базы данных** -> **Создать базу данных**:
   * **Имя БД:** `aspect_db`
   * **Пользователь:** `aspect_dbuser`
   * **Пароль:** `<НАДЕЖНЫЙ_ПАРОЛЬ>`
2. В директории проекта `/var/www/aspect_user/data/www/aspectcoffee.ru` создайте рабочий файл параметров `.env`:
   ```env
   NODE_ENV=production
   PORT=3000
   DATABASE_URL=postgresql://aspect_dbuser:<ПАРОЛЬ>@localhost:5432/aspect_db
   
   # Интеграции
   YOOKASSA_SHOP_ID=<ID_МАГАЗИНА>
   YOOKASSA_SECRET_KEY=<СЕКРЕТНЫЙ_КЛЮЧ>
   CDEK_CLIENT_ID=<CDEK_ID>
   CDEK_CLIENT_SECRET=<CDEK_SECRET>
   CDEK_TEST_MODE=false
   
   # JWT & App Keys
   JWT_SECRET=<СУПЕР_СЕКРЕТНЫЙ_КЛЮЧ>
   ```

---

## 3. Конфигурация в репозитории и на сервере для деплоя (CI/CD Auto-Deploy)

### 3.1 Передача и клонирование репозитория
1. **Добавление SSH-ключа деплоя:**
   На новом сервере сгенерируйте SSH-ключ для чтения репозитория:
   ```bash
   ssh-keygen -t ed25519 -C "deploy@aspectcoffee.ru" -f /root/.ssh/id_ed25519_deploy -N ""
   cat /root/.ssh/id_ed25519_deploy.pub
   ```
   Скопируйте публичный ключ и добавьте его в GitHub/GitLab репозиторий в раздел **Settings -> Deploy keys** (с правом чтения).

2. **Первичное клонирование проекта:**
   ```bash
   cd /var/www/aspect_user/data/www/aspectcoffee.ru
   git clone git@github.com:<ORGA_OR_USER>/aspect-coffee.git .
   npm install --production
   npm run build
   ```

### 3.2 Настройка процесса PM2 и Reverse Proxy (Nginx)
1. Запустите приложение через PM2:
   ```bash
   pm2 start npm --name "aspect-coffee" -- start
   pm2 save
   pm2 startup
   ```
2. В ISPmanager перейдите в раздел **Сайты -> aspectcoffee.ru -> Конфигурация Nginx** и настройте проксирование на локальный порт `3000`:
   ```nginx
   location / {
       proxy_pass http://127.0.0.1:3000;
       proxy_http_version 1.1;
       proxy_set_header Upgrade $http_upgrade;
       proxy_set_header Connection 'upgrade';
       proxy_set_header Host $host;
       proxy_set_header X-Real-IP $remote_addr;
       proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
       proxy_set_header X-Forwarded-Proto $scheme;
       proxy_cache_bypass $http_upgrade;
   }
   ```

### 3.3 Настройка Авто-деплоя (GitHub Actions / Git Hook)
Создайте в вашем GitHub-репозитории файл `.github/workflows/deploy.yml`:

```yaml
name: Deploy Aspect Coffee to New Server

on:
  push:
    branches:
      - main

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Executing remote SSH commands for deploy
        uses: appleboy/ssh-action@v1.0.0
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: root
          key: ${{ secrets.SERVER_SSH_KEY }}
          script: |
            cd /var/www/aspect_user/data/www/aspectcoffee.ru
            git pull origin main
            npm install --production
            npm run build
            pm2 reload aspect-coffee
```

**В GitHub Secrets репозитория (Settings -> Secrets and variables -> Actions) необходимо добавить:**
* `SERVER_HOST`: IP-адрес нового сервера.
* `SERVER_SSH_KEY`: Содержимое приватного ключа `/root/.ssh/id_ed25519_deploy`.

---

### Чек-лист проверки работы после деплоя
- [ ] Сервер отвечает по HTTPS (`https://aspectcoffee.ru`).
- [ ] Процесс `pm2 status` отображает статус `online`.
- [ ] Ошибок в логах `pm2 logs aspect-coffee` нет.
- [ ] Интеграция CDEK и ЮKassa работают в боевом режиме.
- [ ] При `git push origin main` новые изменения автоматически деплоятся на сервер за 1-2 минуты.
