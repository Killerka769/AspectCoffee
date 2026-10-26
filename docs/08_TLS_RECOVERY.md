# TLS recovery — 2026-09-26

The certificate shared by Nginx and the stunnel/OpenVPN wrapper expired on
2026-09-15. The container renewal could not reach HTTP-01 through UFW. The
host renewal script used standalone mode, conflicting with HAProxy's port 80.

## Deployed fix

- `deploy/aspect-vpn-cert-renew` is installed, root-owned and mode 0700, as
  `/usr/local/sbin/aspect-vpn-cert-renew`.
- The existing `aspect-vpn-cert-renew.timer` runs this script twice daily.
- Renewal uses the existing Compose Certbot volumes and Nginx webroot. Neither
  HAProxy nor OpenVPN is stopped for validation.
- A dedicated, temporary UFW rule permits HTTP to the server IPv4 during the
  check. HAProxy continues to reject non-allowlisted requests except ACME
  challenge paths. The script removes only its specific rule on exit.
- Successful certificate changes trigger Nginx validation/reload and a
  stunnel restart. The applied fingerprint is recorded only after success,
  so a failed activation is retried on the next run.
- `deploy/systemd/stunnel4.service.d/aspect.conf` is installed as
  `/etc/systemd/system/stunnel4.service.d/aspect.conf`. It tracks the configured
  pidfile and stops the whole service cgroup. The old SysV wrapper had left
  an orphan process serving the expired certificate after a restart.

## Checks

From a root console or an already established SSH session:

```sh
sh -n /usr/local/sbin/aspect-vpn-cert-renew
/usr/local/sbin/aspect-vpn-cert-renew --dry-run
systemctl start aspect-vpn-cert-renew.service
systemctl show aspect-vpn-cert-renew.service -p Result -p ExecMainStatus
systemctl is-active stunnel4 haproxy openvpn-server@aspect
systemctl is-enabled aspect-vpn-cert-renew.timer
openssl x509 -in /var/lib/docker/volumes/aspectcoffee_certbot_conf/_data/live/aspectcoffee.ru/fullchain.pem -noout -dates
```

The recovery was checked with a successful staging renewal, successful live
renewal, a repeated service run, trusted external TLS hostname/chain validation,
and an OpenVPN client completing initialization. The replacement certificate
covers both `aspectcoffee.ru` and `www.aspectcoffee.ru`, expiring on 2026-12-25.
Certificate verification was not disabled on the client.

Original configuration and certificate-volume backups remain only on the
server in `/root/aspect-recovery-20260926-ssl` (mode 0700). Do not copy private
keys, ACME account data, or server environment files into Git.
