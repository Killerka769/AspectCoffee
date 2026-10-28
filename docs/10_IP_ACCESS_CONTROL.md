# Ограничение сайта по IP: изменение и полное снятие

Проверено на действующем сервере 28.10.2026. Этот документ не снимает
защиту автоматически. Изменения выполняет администратор по SSH через VPN
или с уже разрешённого адреса. Сохраните действующее SSH-подключение до проверки.

## Где находятся правила

| Уровень | Рабочий файл / команда | Назначение |
| --- | --- | --- |
| HAProxy | `/etc/haproxy/haproxy.cfg` | Выбор сайта/VPN по IP и TLS SNI; запреты HTTP |
| Шаблон в Git | `deploy/haproxy/haproxy.cfg` | Версионируемый образец; merge сам не заменяет серверный файл |
| UFW | `ufw status numbered`, `/etc/ufw/user.rules`, `/etc/ufw/user6.rules` | Сетевой доступ к портам; править через `ufw` |

В **обоих** блоках `frontend public_https` и `frontend public_http` параметр:

```haproxy
acl customer_ip src 95.31.19.131/32 84.54.70.81/32 195.19.120.238/32 46.16.231.69/32
```

Это фактический список на дату проверки. Шаблон Git содержит исходный пример
с одним адресом; не заменяйте им рабочий файл целиком, иначе потеряете добавления.
UFW отдельно разрешает HTTP/SSH доверенным IP; публичный TCP 443 уже открыт
для входа VPN. Открытый порт 443 сам по себе не открывает сайт в HAProxy.

Allowlist ЮKassa в `docker/nginx/nginx.conf` относится к платёжным webhook.
Это отдельная защита; её не нужно снимать для открытия сайта посетителям.

## Добавить или заменить один IP

1. Сохранить конфигурацию:

   ```bash
   cp -a /etc/haproxy/haproxy.cfg /root/haproxy.before-ip-change.cfg
   ufw status numbered > /root/ufw.before-ip-change.txt
   ```

2. В `/etc/haproxy/haproxy.cfg` добавить `НОВЫЙ_IP/32` в **обе** строки
   `acl customer_ip src`. Для замены сначала добавить новый адрес и проверить
   доступ с него, затем удалить старый. Не менять `test_sni`, backend и VPN.
3. Разрешить HTTP новому адресу:

   ```bash
   ufw allow proto tcp from НОВЫЙ_IP to any port 80
   haproxy -c -f /etc/haproxy/haproxy.cfg
   systemctl reload haproxy
   ```

4. Проверить основной и тестовый сайты с нового адреса. Старое правило UFW
   удалить только после проверки. SSH-порт 22 открывается отдельно, только
   если этому адресу действительно нужен серверный доступ.

## Полностью убрать IP-ограничение сайтов и сохранить VPN

В `frontend public_https` заменить фрагмент маршрутизации:

```haproxy
acl customer_ip src ...
acl test_sni req.ssl_sni -i test.aspectcoffee.ru

use_backend test_site_https if customer_ip test_sni
use_backend test_blocked_https if test_sni
use_backend customer_site_https if customer_ip
default_backend openvpn_tls
```

на:

```haproxy
acl test_sni req.ssl_sni -i test.aspectcoffee.ru
acl site_sni req.ssl_sni -i aspectcoffee.ru www.aspectcoffee.ru

use_backend test_site_https if test_sni
use_backend customer_site_https if site_sni
default_backend openvpn_tls
```

SNI выбирает сайт независимо от IP. Прочий TLS-трафик по-прежнему направляется
в `openvpn_tls`; не заменяйте default backend на сайт, иначе можно потерять VPN.
Неиспользуемый блок `backend test_blocked_https` можно оставить либо удалить.
Для нового hostname сначала добавьте его в сертификат и конфигурацию сайта,
затем в соответствующую SNI ACL.

В `frontend public_http` удалить обе строки запрета:

```haproxy
http-request deny deny_status 503 if test_host !customer_ip !acme_challenge
http-request deny deny_status 403 if !customer_ip !acme_challenge
```

Затем можно удалить неиспользуемые HTTP ACL `customer_ip` и `acme_challenge`.
Оставить `test_host`, `use_backend test_site_http if test_host` и
`default_backend customer_site_http`.

Разрешить публичный HTTP в UFW и применить проверенный HAProxy-конфиг:

```bash
ufw allow 80/tcp
haproxy -c -f /etc/haproxy/haproxy.cfg
systemctl reload haproxy
systemctl is-active haproxy
ufw status numbered
```

TCP 443 уже разрешён публично. Если это изменилось, выполнить `ufw allow 443/tcp`.
Не отключать UFW целиком и не открывать SSH/БД всем. Удалять старые адресные
правила HTTP необязательно: общее разрешение 80 делает их избыточными.

Проверить **с внешнего неразрешённого ранее IP** HTTPS и HTTP обоих hostname,
переход на HTTPS, сертификат и действующее VPN-подключение. Публичный тестовый
сайт станет доступен посторонним; его отдельная тестовая БД и отключённые
интеграции должны сохраниться. Индексация теста остаётся запрещённой.

## Откат

```bash
cp -a /root/haproxy.before-ip-change.cfg /etc/haproxy/haproxy.cfg
haproxy -c -f /etc/haproxy/haproxy.cfg
systemctl reload haproxy
```

Если общее `ufw allow 80/tcp` было добавлено именно при этом изменении,
удалить его `ufw delete allow 80/tcp`. Не удалять ранее существовавшие правила
443/VPN и адресные разрешения. Проверить сайт с доверенного IP и VPN.

Несекретные изменения шаблона и инструкции проходят PR/review в Git.
Применение `/etc/haproxy/haproxy.cfg` и UFW — отдельная операция на сервере;
нажатие merge не изменяет эти правила автоматически.
