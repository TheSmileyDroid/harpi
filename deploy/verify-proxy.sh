#!/usr/bin/env bash
set -euo pipefail

DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
HOSTNAME_VALUE=harpi.smileydroid.com.br
MIN_DAYS=14
NPM_CONTAINER=nginx-app-1
PUBLIC_IP=${PUBLIC_IP:-}
TAILSCALE_IP=${TAILSCALE_IP:-}
FAILURES=0
HEADERS=

usage() {
  printf 'usage: %s [--hostname NAME] [--min-days N] [--public-ip IP] [--tailscale-ip IP] [--npm-container NAME]\n' \
    "${0##*/}" >&2
}

die() {
  printf 'verify proxy: %s\n' "$1" >&2
  exit 2
}

pass() {
  printf 'PASS %s\n' "$1"
}

fail() {
  printf 'FAIL %s\n' "$1"
  FAILURES=$((FAILURES + 1))
}

header_value() {
  printf '%s' "$HEADERS" | tr -d '\r' | grep -i "^$1:" | head -n 1 | cut -d: -f2- | sed 's/^ *//' || true
}

check_certificate() {
  local chain issuer enddate
  if ! chain=$(openssl s_client -connect "$HOSTNAME_VALUE:443" \
    -servername "$HOSTNAME_VALUE" -verify_return_error </dev/null 2>/dev/null); then
    fail 'certificate: the TLS handshake or the chain verification failed'
    return
  fi
  if ! issuer=$(printf '%s' "$chain" | openssl x509 -noout -issuer 2>/dev/null); then
    fail 'certificate: the peer did not present a certificate'
    return
  fi
  enddate=$(printf '%s' "$chain" | openssl x509 -noout -enddate 2>/dev/null | cut -d= -f2)
  if [[ $issuer == *"Let's Encrypt"* ]]; then
    pass "certificate: issued by Let's Encrypt ($enddate)"
  else
    fail "certificate: issuer is $issuer, not Let's Encrypt"
  fi
  if printf '%s' "$chain" | openssl x509 -noout -checkend $((MIN_DAYS * 86400)) >/dev/null 2>&1; then
    pass "certificate: valid for at least $MIN_DAYS days"
  else
    fail "certificate: expires within $MIN_DAYS days ($enddate)"
  fi
}

check_forced_https() {
  local answer code url
  if ! answer=$(curl -sS -o /dev/null -w '%{http_code} %{redirect_url}' --max-time 10 \
    "http://$HOSTNAME_VALUE/"); then
    fail 'forced HTTPS: plain HTTP did not answer'
    return
  fi
  code=${answer%% *}
  url=${answer#* }
  if [[ ($code == 301 || $code == 308) && $url == "https://$HOSTNAME_VALUE"* ]]; then
    pass "forced HTTPS: $code to $url"
  else
    fail "forced HTTPS: plain HTTP answered $code to ${url:-nothing}"
  fi
}

fetch_headers() {
  HEADERS=$(curl -sS -D - -o /dev/null --max-time 10 "https://$HOSTNAME_VALUE/") \
    || return 1
}

check_hsts() {
  local hsts
  hsts=$(header_value strict-transport-security)
  if [[ -z $hsts ]]; then
    fail 'HSTS: the response carries no Strict-Transport-Security header'
  elif [[ $hsts != *max-age=* ]]; then
    fail "HSTS: $hsts has no max-age"
  elif [[ ${hsts,,} == *includesubdomains* ]]; then
    fail "HSTS: $hsts includes subdomains"
  else
    pass "HSTS: $hsts"
  fi
}

check_http2() {
  local version
  if ! curl -V | grep -qi 'HTTP2'; then
    fail 'HTTP/2: this curl has no HTTP/2 support'
    return
  fi
  if ! version=$(curl --http2 -sS -o /dev/null -w '%{http_version}' --max-time 10 \
    "https://$HOSTNAME_VALUE/"); then
    fail 'HTTP/2: the request failed'
    return
  fi
  if [[ $version == 2 ]]; then
    pass 'HTTP/2: the response is HTTP/2'
  else
    fail "HTTP/2: the response is HTTP/$version"
  fi
}

check_websocket() {
  local code
  code=$(curl -sS --http1.1 -o /dev/null -w '%{http_code}' --max-time 10 \
    -H 'Connection: Upgrade' -H 'Upgrade: websocket' \
    -H 'Sec-WebSocket-Version: 13' -H 'Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==' \
    "https://$HOSTNAME_VALUE/" 2>/dev/null) || code=000
  case $code in
    101 | 400)
      pass "websocket: the upgrade reached the app ($code)"
      ;;
    200)
      fail 'websocket: the proxy answered 200, so it stripped the upgrade headers'
      ;;
    *)
      fail "websocket: the upgrade answered $code"
      ;;
  esac
}

check_server_tokens() {
  local server
  server=$(header_value server)
  if [[ -n $server ]]; then
    fail "server tokens: the response advertises $server"
  else
    pass "server tokens: no Server header"
  fi
}

check_admin_exposure() {
  local output
  local -a arguments=()
  [[ -z $PUBLIC_IP ]] || arguments+=(--public-ip "$PUBLIC_IP")
  [[ -z $TAILSCALE_IP ]] || arguments+=(--tailscale-ip "$TAILSCALE_IP")
  if output=$("$DIR/check-admin-exposure.sh" "${arguments[@]}"); then
    pass "admin port 81: $(printf '%s' "$output" | tail -n 1)"
  else
    printf '%s\n' "$output" | sed 's/^/     /'
    fail 'admin port 81: the public interface answers or Tailscale does not'
  fi
}

check_single_host() {
  local count
  local -a arguments=()
  [[ -z ${NPM_URL:-} ]] || arguments+=(--url "$NPM_URL")
  if [[ -n ${NPM_TOKEN:-} || (-n ${NPM_IDENTITY:-} && -n ${NPM_PASSWORD:-}) ]]; then
    if "$DIR/npm-proxy-host.sh" --check "${arguments[@]}" >/dev/null 2>&1; then
      pass "single host: the NPM API reports one host for $HOSTNAME_VALUE"
    else
      fail "single host: the NPM API does not report exactly one host for $HOSTNAME_VALUE"
    fi
    return
  fi
  if command -v docker >/dev/null 2>&1 \
    && docker inspect "$NPM_CONTAINER" >/dev/null 2>&1; then
    count=$(docker exec "$NPM_CONTAINER" sh -c \
      "grep -l 'server_name .*harpi[.]smileydroid[.]com[.]br' /data/nginx/proxy_host/*.conf 2>/dev/null | wc -l")
    if [[ $count == 1 ]]; then
      pass "single host: one rendered config names $HOSTNAME_VALUE"
    else
      fail "single host: $count rendered configs name $HOSTNAME_VALUE"
    fi
    return
  fi
  fail "single host: set NPM_TOKEN or run this on the Docker host with $NPM_CONTAINER"
}

while [[ $# -gt 0 ]]; do
  case $1 in
    --hostname)
      HOSTNAME_VALUE=${2:?--hostname needs a name}
      shift 2
      ;;
    --min-days)
      MIN_DAYS=${2:?--min-days needs a number}
      shift 2
      ;;
    --public-ip)
      PUBLIC_IP=${2:?--public-ip needs an address}
      shift 2
      ;;
    --tailscale-ip)
      TAILSCALE_IP=${2:?--tailscale-ip needs an address}
      shift 2
      ;;
    --npm-container)
      NPM_CONTAINER=${2:?--npm-container needs a name}
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
command -v openssl >/dev/null || die 'openssl is required'
[[ $MIN_DAYS =~ ^[0-9]+$ ]] || die "--min-days takes a number, not $MIN_DAYS"

check_certificate
check_forced_https
if fetch_headers; then
  check_hsts
  check_server_tokens
else
  fail 'headers: the HTTPS request failed'
fi
check_http2
check_websocket
check_admin_exposure
check_single_host

if ((FAILURES > 0)); then
  printf '%d check(s) failed\n' "$FAILURES"
  exit 1
fi
printf 'all checks passed for %s\n' "$HOSTNAME_VALUE"
