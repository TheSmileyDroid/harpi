#!/usr/bin/env bash
set -euo pipefail

DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
ROOT=$(cd -- "$DIR/.." && pwd)
GATE=$ROOT/tools/release_gate.py
PYTHON=${PYTHON:-}
if [[ -z $PYTHON ]]; then
  if [[ -x $ROOT/.venv/bin/python ]]; then
    PYTHON=$ROOT/.venv/bin/python
  else
    PYTHON=python3
  fi
fi
HOSTNAME_VALUE=harpi.smileydroid.com.br
NPM_CONTAINER=${NPM_CONTAINER:-nginx-app-1}
NPM_URL=${NPM_URL:-http://100.106.27.40:81}
TIMEOUT=${TIMEOUT:-10}
SEARCH_TIMEOUT=${SEARCH_TIMEOUT:-60}
SCAN_PORTS=${SCAN_PORTS:--}
MODE=
BASE_URL=
SCAN_HOST=
RESULTS=()

usage() {
  printf 'usage: %s --pre\n' "${0##*/}" >&2
  printf '       %s --release --base-url URL\n' "${0##*/}" >&2
  printf '       %s --ports HOST\n' "${0##*/}" >&2
  printf '  --pre      prove the gate is still closed before any DNS or proxy host\n' >&2
  printf '  --release  prove the deployed host answers safely\n' >&2
  printf '  --ports    scan HOST from outside and require only 80 and 443 open\n' >&2
  printf '  HARPI_SESSION_COOKIE holds the login cookie for the authenticated probes\n' >&2
  printf '  NPM_TOKEN is optional; without it --pre reads the rendered proxy configs\n' >&2
  printf '  PYTHON overrides the interpreter (default: the repository .venv)\n' >&2
}

die() {
  printf 'release gate: %s\n' "$1" >&2
  exit 2
}

set_mode() {
  [[ -z $MODE ]] || die 'choose exactly one of --pre, --release, --ports'
  MODE=$1
}

record() {
  local input=$1 line command_name
  shift
  command_name=$*
  line=$(printf '%s' "$input" | "$PYTHON" "$GATE" "$@" 2>&1) || true
  if [[ -z $line ]]; then
    line="FAIL release gate: no output from $command_name"
  fi
  RESULTS+=("$line")
  printf '%s\n' "$line"
}

verified_status_code() {
  local code
  code=$(curl -sS -o /dev/null -w '%{http_code}' --max-time "$TIMEOUT" \
    "$1" 2>/dev/null) || code=000
  printf '%s' "$code"
}

unverified_status_code() {
  local code
  code=$(curl -k -sS -o /dev/null -w '%{http_code}' --max-time "$TIMEOUT" \
    "$1" 2>/dev/null) || code=000
  printf '%s' "$code"
}

response_headers() {
  local headers
  headers=$(curl -sS -D - -o /dev/null --max-time "$TIMEOUT" "$1" \
    2>/dev/null) || headers=
  printf '%s' "$headers"
}

post_code() {
  local code
  code=$(curl -sS -o /dev/null -w '%{http_code}' --max-time "$1" \
    -X POST -H 'Content-Type: application/json' -H "Cookie: $3" \
    --data-binary "$4" "$2" 2>/dev/null) || code=000
  printf '%s' "$code"
}

dns_answer() {
  local answer
  if command -v dig >/dev/null 2>&1; then
    answer=$(
      {
        dig +short A "$HOSTNAME_VALUE"
        dig +short AAAA "$HOSTNAME_VALUE"
      } 2>/dev/null
    ) || return 1
    printf '%s' "$answer"
    return 0
  fi
  getent ahosts "$HOSTNAME_VALUE" 2>/dev/null \
    | awk '{print $1}' | sort -u || true
}

proxy_format() {
  if [[ -n ${NPM_TOKEN:-} ]]; then
    printf 'json'
  elif command -v docker >/dev/null 2>&1 \
    && docker inspect "$NPM_CONTAINER" >/dev/null 2>&1; then
    printf 'config'
  else
    printf 'none'
  fi
}

proxy_payload() {
  if [[ $1 == json ]]; then
    curl -sS --max-time "$TIMEOUT" -H "Authorization: Bearer $NPM_TOKEN" \
      "$NPM_URL/api/nginx/proxy-hosts" 2>/dev/null || true
    return
  fi
  docker exec "$NPM_CONTAINER" sh -c \
    "grep -l 'server_name .*harpi[.]smileydroid[.]com[.]br' /data/nginx/proxy_host/*.conf 2>/dev/null" \
    || true
}

cookie_header() {
  if [[ ${HARPI_SESSION_COOKIE:-} == *=* ]]; then
    printf '%s' "$HARPI_SESSION_COOKIE"
  else
    printf '__Host-harpi=%s' "$HARPI_SESSION_COOKIE"
  fi
}

run_pre() {
  local answer format payload http_code https_code
  if command -v dig >/dev/null 2>&1 \
    || command -v getent >/dev/null 2>&1; then
    if answer=$(dns_answer); then
      record "$answer" dns --hostname "$HOSTNAME_VALUE"
    else
      record '' report --status FAIL --name dns \
        --detail 'the DNS lookup failed; absence is unproven'
    fi
  else
    record '' report --status FAIL --name dns \
      --detail 'neither dig nor getent is installed'
  fi

  format=$(proxy_format)
  if [[ $format == none ]]; then
    record '' report --status FAIL --name 'proxy host' \
      --detail "cannot prove absence: set NPM_TOKEN or run on the Docker host with $NPM_CONTAINER"
  else
    payload=$(proxy_payload "$format")
    record "$payload" proxy --hostname "$HOSTNAME_VALUE" --format "$format"
  fi

  http_code=$(unverified_status_code "http://$HOSTNAME_VALUE/")
  https_code=$(unverified_status_code "https://$HOSTNAME_VALUE/")
  record '' public --http-code "$http_code" --https-code "$https_code"
}

run_release() {
  local headers code set_cookie private_code youtube_code path
  headers=$(response_headers "$BASE_URL/api/session")
  code=$(verified_status_code "$BASE_URL/api/session")
  record '' status --name 'unauthenticated /api/session' \
    --actual "$code" --expected 401
  record "$headers" hsts

  for path in /openapi.json /docs /redocs /scalar; do
    code=$(verified_status_code "$BASE_URL$path")
    record '' status --name "$path" --actual "$code" --expected 404
  done

  headers=$(response_headers "$BASE_URL/api/auth/discord")
  set_cookie=$(printf '%s' "$headers" | tr -d '\r' \
    | grep -i '^set-cookie:' | head -n 1 | cut -d: -f2- \
    | sed 's/^ *//' || true)
  record "$set_cookie" cookie

  if [[ -z ${HARPI_SESSION_COOKIE:-} ]]; then
    record '' report --status SKIP --name 'ssrf queue probe' \
      --detail 'no HARPI_SESSION_COOKIE; the URL policy was not exercised'
    record '' report --status SKIP --name 'youtube url accepted' \
      --detail 'no HARPI_SESSION_COOKIE; the URL policy was not exercised'
    return
  fi

  private_code=$(post_code "$TIMEOUT" "$BASE_URL/api/queue" \
    "$(cookie_header)" '{"url":"http://169.254.169.254/latest/meta-data/"}')
  if [[ $private_code == 404 ]]; then
    record '' report --status FAIL --name 'ssrf queue probe' \
      --detail 'answered 404: connect the bot, select a guild, and retry'
  else
    record '' status --name 'ssrf queue probe' \
      --actual "$private_code" --expected 400
  fi

  youtube_code=$(post_code "$SEARCH_TIMEOUT" "$BASE_URL/api/search" \
    "$(cookie_header)" \
    '{"term":"https://www.youtube.com/watch?v=dQw4w9WgXcQ"}')
  record '' status --name 'youtube url accepted' \
    --actual "$youtube_code" --expected 200
}

run_ports() {
  local scan
  if ! command -v nmap >/dev/null 2>&1; then
    record '' report --status FAIL --name 'open ports' \
      --detail 'nmap is not installed'
    return
  fi
  scan=$(nmap -Pn -p "$SCAN_PORTS" "$SCAN_HOST" 2>/dev/null) || scan=
  record "$scan" ports
}

while [[ $# -gt 0 ]]; do
  case $1 in
    --pre)
      set_mode pre
      shift
      ;;
    --release)
      set_mode release
      shift
      ;;
    --ports)
      set_mode ports
      [[ $# -ge 2 ]] || die '--ports needs a host'
      SCAN_HOST=$2
      shift 2
      ;;
    --base-url)
      [[ $# -ge 2 ]] || die '--base-url needs a url'
      BASE_URL=$2
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

[[ -n $MODE ]] || die 'choose one of --pre, --release, --ports'
command -v "$PYTHON" >/dev/null 2>&1 || die "$PYTHON is required"
[[ -f $GATE ]] || die "missing $GATE"
"$PYTHON" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 13) else 1)' \
  || die "$PYTHON is older than 3.13; set PYTHON to the repository .venv/bin/python"

if [[ $MODE == release ]]; then
  [[ -n $BASE_URL ]] || die '--release needs --base-url'
  [[ $BASE_URL == http://* || $BASE_URL == https://* ]] \
    || die "--base-url takes an http or https URL, not $BASE_URL"
  BASE_URL=${BASE_URL%/}
  command -v curl >/dev/null 2>&1 || die 'curl is required'
fi

if [[ $MODE == pre ]]; then
  command -v curl >/dev/null 2>&1 || die 'curl is required'
fi

case $MODE in
  pre) run_pre ;;
  release) run_release ;;
  ports) run_ports ;;
esac

printf '%s\n' "${RESULTS[@]}" | "$PYTHON" "$GATE" verdict
