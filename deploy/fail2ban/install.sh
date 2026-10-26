#!/usr/bin/env bash
set -euo pipefail

DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
TARGET=/etc/fail2ban
ADMIN_LOG=/home/opc/external/nginx/data/logs/admin_access.log
PROXY_LOG_GLOB='/home/opc/external/nginx/data/logs/proxy-host-*_access.log'

die() {
  printf 'fail2ban install: %s\n' "$1" >&2
  exit 1
}

[[ ${EUID:-$(id -u)} -eq 0 ]] || die 'run as root'
[[ -d $TARGET ]] || die "fail2ban is not installed under $TARGET"
command -v fail2ban-client >/dev/null || die 'fail2ban-client is missing'
[[ -e $ADMIN_LOG ]] \
  || die "$ADMIN_LOG does not exist; mount deploy/npm/admin-production.conf into the NPM container first"
compgen -G "$PROXY_LOG_GLOB" >/dev/null \
  || die "no $PROXY_LOG_GLOB; create the proxy host first"

install -m 0644 "$DIR/filter.d/npm-admin-auth.conf" "$TARGET/filter.d/npm-admin-auth.conf"
install -m 0644 "$DIR/filter.d/harpi-auth.conf" "$TARGET/filter.d/harpi-auth.conf"
install -m 0644 "$DIR/action.d/npm-docker-user.conf" "$TARGET/action.d/npm-docker-user.conf"
install -m 0644 "$DIR/jail.d/harpi-edge.local" "$TARGET/jail.d/harpi-edge.local"

fail2ban-client -t
systemctl reload fail2ban 2>/dev/null || systemctl restart fail2ban

fail2ban-client status npm-admin-auth
fail2ban-client status harpi-auth
fail2ban-client status sshd
printf 'installed; banned addresses appear under each jail status\n'
