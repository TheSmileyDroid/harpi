#!/usr/bin/env bash
set -euo pipefail

BASE_URL=${BASE_URL:-https://harpi.smileydroid.com.br}
AUTH_PATH=/api/auth/discord
API_PATH=/api/session
AUTH_LIMIT=10
API_LIMIT=60
AUTH_BURST=3
API_BURST=10
TIMEOUT=10
FAILURES=0

usage() {
  printf 'usage: %s [--url URL] [--auth-path PATH] [--api-path PATH]\n' "${0##*/}" >&2
  printf '          [--auth-limit N] [--api-limit N] [--auth-burst N] [--api-burst N]\n' >&2
  printf '          [--timeout SECONDS]\n' >&2
  printf '  sends read-only GET bursts and fails when a burst is not answered with 429\n' >&2
}

die() {
  printf 'rate limits: %s\n' "$1" >&2
  exit 1
}

pass() {
  printf 'PASS %s\n' "$1"
}

fail() {
  printf 'FAIL %s\n' "$1"
  FAILURES=$((FAILURES + 1))
}

status_code() {
  local code
  code=$(curl -sS -o /dev/null -w '%{http_code}' --max-time "$TIMEOUT" \
    "$BASE_URL$1" 2>/dev/null) || code=000
  printf '%s' "$code"
}

first_limited_request() {
  local path=$1 attempts=$2 code i
  for ((i = 1; i <= attempts; i++)); do
    code=$(status_code "$path")
    if [[ $code == 429 ]]; then
      printf '%d' "$i"
      return 0
    fi
  done
  return 1
}

check_burst() {
  local name=$1 path=$2 limit=$3 burst=$4 attempts limited
  attempts=$((limit + burst + 10))
  if limited=$(first_limited_request "$path" "$attempts"); then
    pass "$name: request $limited of $attempts to $path answered 429"
  else
    fail "$name: $attempts requests to $path never answered 429"
  fi
}

while [[ $# -gt 0 ]]; do
  case $1 in
    --url)
      BASE_URL=${2:?--url needs a base url}
      shift 2
      ;;
    --auth-path)
      AUTH_PATH=${2:?--auth-path needs a path}
      shift 2
      ;;
    --api-path)
      API_PATH=${2:?--api-path needs a path}
      shift 2
      ;;
    --auth-limit)
      AUTH_LIMIT=${2:?--auth-limit needs a number}
      shift 2
      ;;
    --api-limit)
      API_LIMIT=${2:?--api-limit needs a number}
      shift 2
      ;;
    --auth-burst)
      AUTH_BURST=${2:?--auth-burst needs a number}
      shift 2
      ;;
    --api-burst)
      API_BURST=${2:?--api-burst needs a number}
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
for value in "$AUTH_LIMIT" "$API_LIMIT" "$AUTH_BURST" "$API_BURST"; do
  [[ $value =~ ^[0-9]+$ ]] || die "limits and bursts take numbers, not $value"
done
[[ $BASE_URL == https://* ]] || die "the base url must be https, not $BASE_URL"

printf 'probing %s; this leaves the calling address rate limited for up to a minute\n' \
  "$BASE_URL"

check_burst auth "$AUTH_PATH" "$AUTH_LIMIT" "$AUTH_BURST"
check_burst api "$API_PATH" "$API_LIMIT" "$API_BURST"

if ((FAILURES > 0)); then
  printf '%d check(s) failed\n' "$FAILURES"
  exit 1
fi
printf 'both bursts are limited at %s\n' "$BASE_URL"
