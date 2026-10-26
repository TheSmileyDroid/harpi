#!/usr/bin/env bash
set -euo pipefail

PORT=81
TIMEOUT=5
PUBLIC_IP=${PUBLIC_IP:-}
TAILSCALE_IP=${TAILSCALE_IP:-}
FAILURES=0

usage() {
  printf 'usage: %s [--public-ip IP] [--tailscale-ip IP] [--port N] [--timeout SECONDS]\n' \
    "${0##*/}" >&2
}

die() {
  printf 'admin exposure: %s\n' "$1" >&2
  exit 1
}

pass() {
  printf 'PASS %s\n' "$1"
}

fail() {
  printf 'FAIL %s\n' "$1"
  FAILURES=$((FAILURES + 1))
}

warn() {
  printf 'WARN %s\n' "$1"
}

host_url() {
  if [[ $1 == *:* ]]; then
    printf 'http://[%s]:%s/' "$1" "$PORT"
  else
    printf 'http://%s:%s/' "$1" "$PORT"
  fi
}

probe() {
  local code
  code=$(curl -sS -o /dev/null -w '%{http_code}' --max-time "$TIMEOUT" \
    "$(host_url "$1")" 2>/dev/null) || code=000
  printf '%s' "$code"
}

detect_tailscale_ip() {
  command -v tailscale >/dev/null 2>&1 || return 1
  tailscale ip -4 2>/dev/null | head -n 1
}

detect_public_ip() {
  ip -4 route get 1.1.1.1 2>/dev/null | awk '{print $7; exit}'
}

check_listener() {
  local listeners wildcard
  listeners=$(ss -tlnH "sport = :$PORT" 2>/dev/null | awk '{print $4}')
  if [[ -z $listeners ]]; then
    fail "nothing listens on port $PORT"
    return
  fi
  if grep -qxE "(\*|0\.0\.0\.0|\[::\]|::):$PORT" <<<"$listeners"; then
    wildcard=$(grep -xE "(\*|0\.0\.0\.0|\[::\]|::):$PORT" <<<"$listeners" | paste -sd, -)
    warn "port $PORT listens on $wildcard; the public probe decides whether that is blocked"
  fi
  if grep -qxF "$TAILSCALE_IP:$PORT" <<<"$listeners"; then
    pass "port $PORT is bound to the Tailscale address $TAILSCALE_IP"
  else
    warn "port $PORT is not bound to $TAILSCALE_IP; the Tailscale probe decides whether it answers"
  fi
}

check_public_blocked() {
  local code
  code=$(probe "$PUBLIC_IP")
  if [[ $code == 000 ]]; then
    pass "$PUBLIC_IP:$PORT does not answer"
  else
    fail "$PUBLIC_IP:$PORT answered $code; the admin interface is reachable from the public interface"
  fi
}

check_tailscale_answers() {
  local code
  code=$(probe "$TAILSCALE_IP")
  if [[ $code == 000 ]]; then
    fail "$TAILSCALE_IP:$PORT does not answer; the admin interface is unreachable over Tailscale"
  else
    pass "$TAILSCALE_IP:$PORT answered $code"
  fi
}

while [[ $# -gt 0 ]]; do
  case $1 in
    --public-ip)
      PUBLIC_IP=${2:?--public-ip needs an address}
      shift 2
      ;;
    --tailscale-ip)
      TAILSCALE_IP=${2:?--tailscale-ip needs an address}
      shift 2
      ;;
    --port)
      PORT=${2:?--port needs a number}
      shift 2
      ;;
    --timeout)
      TIMEOUT=${2:?--timeout needs seconds}
      shift 2
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      usage
      exit 2
      ;;
  esac
done

command -v curl >/dev/null || die 'curl is required'
command -v ss >/dev/null || die 'ss is required'
[[ $PORT =~ ^[0-9]+$ ]] || die "--port takes a number, not $PORT"

if [[ -z $TAILSCALE_IP ]]; then
  TAILSCALE_IP=$(detect_tailscale_ip || true)
fi
[[ -n $TAILSCALE_IP ]] || die 'set TAILSCALE_IP or pass --tailscale-ip'

if [[ -z $PUBLIC_IP ]]; then
  PUBLIC_IP=$(detect_public_ip || true)
fi
[[ -n $PUBLIC_IP ]] || die 'set PUBLIC_IP or pass --public-ip'

check_listener
check_public_blocked
check_tailscale_answers

if ((FAILURES > 0)); then
  printf '%d check(s) failed\n' "$FAILURES"
  exit 1
fi
printf 'port %s is reachable over Tailscale and silent on the public interface\n' "$PORT"
