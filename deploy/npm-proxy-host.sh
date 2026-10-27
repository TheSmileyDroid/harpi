#!/usr/bin/env bash
set -euo pipefail

DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
TEMPLATE=$DIR/npm/proxy-host.json
ADVANCED=$DIR/npm/harpi-advanced.conf
HOSTNAME_VALUE=harpi.smileydroid.com.br
UPSTREAM=harpi-backend:8000
NPM_URL=${NPM_URL:-http://100.106.27.40:81}
APPLY=false
CHECK=false
CERTIFICATE=

usage() {
  printf 'usage: %s [--apply | --check] [--certificate new|ID] [--url URL]\n' "${0##*/}" >&2
  printf '  without --apply it prints every request and body it would send\n' >&2
  printf '  --check reads the host back and fails unless exactly one claims the hostname\n' >&2
  printf '  credentials: NPM_TOKEN, or NPM_IDENTITY and NPM_PASSWORD\n' >&2
}

die() {
  printf 'npm proxy host: %s\n' "$1" >&2
  exit 1
}

render() {
  python3 - "$TEMPLATE" "$ADVANCED" "$NPM_URL" "$HOSTNAME_VALUE" "$UPSTREAM" "$1" "$2" <<'PY'
import json
import os
import sys
from pathlib import Path

template_path, advanced_path, base_url, hostname, upstream, mode, certificate = sys.argv[1:8]
text = Path(template_path).read_text()
placeholder = '"{{ADVANCED_CONFIG}}"'
if text.count(placeholder) != 1:
    raise SystemExit(f"{template_path} must contain exactly one {placeholder} placeholder")


def body_for(certificate_value):
    payload = json.loads(
        text.replace(placeholder, json.dumps(Path(advanced_path).read_text()))
    )
    payload["certificate_id"] = certificate_value
    if certificate_value == "new":
        payload.setdefault("meta", {})["letsencrypt_email"] = (
            os.environ.get("NPM_EMAIL") or os.environ.get("NPM_IDENTITY", "")
        )
    if certificate_value == 0:
        payload["ssl_forced"] = False
        payload["http2_support"] = False
        payload["hsts_enabled"] = False
    return payload


def certificate_value():
    if certificate == "new":
        return "new"
    return int(certificate)


collection = f"{base_url}/api/nginx/proxy-hosts"
plan = {
    "hostname": hostname,
    "upstream": f"http://{upstream}",
    "query": {
        "method": "GET",
        "url": collection,
        "purpose": "count the hosts claiming the hostname and refuse when more than one does",
    },
    "create": {
        "method": "POST",
        "url": collection,
        "body": body_for(0),
    },
    "attach_certificate": None,
}
if certificate:
    plan["attach_certificate"] = {
        "method": "PUT",
        "url": f"{collection}/{{id}}",
        "body": body_for(certificate_value()),
    }

if mode == "plan":
    print(json.dumps(plan, indent=2))
elif mode == "create":
    print(json.dumps(body_for(0)))
elif mode == "tls":
    print(json.dumps(body_for(certificate_value())))
else:
    raise SystemExit(f"unknown render mode {mode}")
PY
}

api() {
  local method=$1 path=$2 body=${3-} response status payload
  if [[ -n $body ]]; then
    response=$(curl -sS --max-time 60 -X "$method" \
      -H "Authorization: Bearer $TOKEN" \
      -H 'Content-Type: application/json' \
      --data-binary "$body" -w '\n%{http_code}' "$NPM_URL$path") || return 1
  else
    response=$(curl -sS --max-time 60 -X "$method" \
      -H "Authorization: Bearer $TOKEN" -w '\n%{http_code}' "$NPM_URL$path") || return 1
  fi
  status=${response##*$'\n'}
  payload=${response%$'\n'*}
  if [[ $status != 2* ]]; then
    printf '%s\n' "$payload" >&2
    return 1
  fi
  printf '%s' "$payload"
}

authenticate() {
  if [[ -n ${NPM_TOKEN:-} ]]; then
    TOKEN=$NPM_TOKEN
    return
  fi
  [[ -n ${NPM_IDENTITY:-} && -n ${NPM_PASSWORD:-} ]] \
    || die 'needs NPM_TOKEN, or NPM_IDENTITY and NPM_PASSWORD'
  local credentials response
  credentials=$(python3 -c \
    'import json, sys; print(json.dumps({"identity": sys.argv[1], "secret": sys.argv[2]}))' \
    "$NPM_IDENTITY" "$NPM_PASSWORD")
  response=$(curl -sS --max-time 30 -H 'Content-Type: application/json' \
    --data-binary "$credentials" "$NPM_URL/api/tokens") \
    || die "cannot reach $NPM_URL/api/tokens; is port 81 reachable over Tailscale?"
  TOKEN=$(printf '%s' "$response" \
    | python3 -c 'import json, sys; print(json.load(sys.stdin).get("token", ""))') \
    || die 'NPM did not answer with a token'
  [[ -n $TOKEN ]] || die 'NPM rejected the credentials'
}

hosts_matching() {
  api GET /api/nginx/proxy-hosts | python3 -c '
import json
import sys

hostname = sys.argv[1]
for row in json.load(sys.stdin):
    if hostname in (row.get("domain_names") or []):
        print(row["id"], row.get("certificate_id") or 0)
' "$HOSTNAME_VALUE"
}

verify_host() {
  local id=$1 certificate=$2 problems
  problems=$(api GET "/api/nginx/proxy-hosts/$id" | python3 -c '
import json
import sys

row = json.load(sys.stdin)
with_tls = sys.argv[1] != ""
hostname = sys.argv[2]
forward = (row.get("forward_scheme"), row.get("forward_host"), row.get("forward_port"))
failures = []
if row.get("domain_names") != [hostname]:
    failures.append("domain_names=%s" % (row.get("domain_names"),))
if forward != ("http", "harpi-backend", 8000):
    failures.append("forward=%s://%s:%s" % forward)
if not row.get("allow_websocket_upgrade"):
    failures.append("websocket upgrade is off")
if not row.get("block_exploits"):
    failures.append("block exploits is off")
if with_tls:
    if not row.get("ssl_forced"):
        failures.append("forced HTTPS is off")
    if not row.get("http2_support"):
        failures.append("HTTP/2 is off")
    if not row.get("hsts_enabled"):
        failures.append("HSTS is off")
    if row.get("hsts_subdomains"):
        failures.append("HSTS includes subdomains")
    if not row.get("certificate_id"):
        failures.append("no certificate is attached")
if failures:
    print("; ".join(failures))
    sys.exit(1)
' "$certificate" "$HOSTNAME_VALUE") \
    || die "the applied host does not match the desired state: $problems"
}

apply_host() {
  command -v curl >/dev/null || die 'curl is required'
  command -v python3 >/dev/null || die 'python3 is required'
  authenticate

  local matches count id existing_certificate certificate_value response
  matches=$(hosts_matching)
  count=0
  if [[ -n $matches ]]; then
    count=$(printf '%s\n' "$matches" | wc -l)
  fi
  if ((count > 1)); then
    die "found $count hosts claiming $HOSTNAME_VALUE ($(printf '%s' "$matches" | awk '{print $1}' | paste -sd, -)); remove the extra rows in the NPM UI first"
  fi

  id=
  existing_certificate=0
  if ((count == 1)); then
    read -r id existing_certificate <<<"$matches"
  fi

  certificate_value=
  if [[ -n $CERTIFICATE ]]; then
    if [[ $CERTIFICATE == new ]] && ((existing_certificate > 0)); then
      certificate_value=$existing_certificate
    else
      certificate_value=$CERTIFICATE
    fi
  elif ((existing_certificate > 0)); then
    certificate_value=$existing_certificate
  fi

  if [[ -z $id ]]; then
    if ! response=$(api POST /api/nginx/proxy-hosts "$(render create 0)"); then
      die "NPM refused the proxy host: $response"
    fi
    id=$(printf '%s' "$response" \
      | python3 -c 'import json, sys; print(json.load(sys.stdin)["id"])') \
      || die 'NPM did not return the created host id'
    printf 'created proxy host %s for %s\n' "$id" "$HOSTNAME_VALUE"
  fi

  if [[ -n $certificate_value ]]; then
    if ! response=$(api PUT "/api/nginx/proxy-hosts/$id" "$(render tls "$certificate_value")"); then
      die "NPM refused the certificate update: $response"
    fi
    printf 'attached certificate %s to proxy host %s\n' "$certificate_value" "$id"
  elif ((count == 1)); then
    if ! response=$(api PUT "/api/nginx/proxy-hosts/$id" "$(render create 0)"); then
      die "NPM refused the host update: $response"
    fi
    printf 'updated proxy host %s for %s\n' "$id" "$HOSTNAME_VALUE"
  fi

  verify_host "$id" "$certificate_value"
  count=0
  matches=$(hosts_matching)
  if [[ -n $matches ]]; then
    count=$(printf '%s\n' "$matches" | wc -l)
  fi
  [[ $count == 1 ]] \
    || die "expected one proxy host for $HOSTNAME_VALUE, found $count"

  if [[ -n $certificate_value ]]; then
    printf 'forced HTTPS, HTTP/2, HSTS without includeSubDomains, websocket upgrade are on\n'
  else
    printf 'no certificate attached; NPM keeps forced HTTPS, HTTP/2 and HSTS off until one is\n'
  fi
  printf 'next: deploy/verify-proxy.sh\n'
}

check_host() {
  command -v curl >/dev/null || die 'curl is required'
  command -v python3 >/dev/null || die 'python3 is required'
  authenticate
  local matches count
  matches=$(hosts_matching)
  count=0
  if [[ -n $matches ]]; then
    count=$(printf '%s\n' "$matches" | wc -l)
  fi
  if ((count != 1)); then
    printf 'found %d hosts claiming %s\n' "$count" "$HOSTNAME_VALUE" >&2
    [[ -z $matches ]] || printf '%s\n' "$matches" >&2
    exit 1
  fi
  printf 'one host claims %s: %s\n' "$HOSTNAME_VALUE" "$matches"
}

while [[ $# -gt 0 ]]; do
  case $1 in
    --apply)
      APPLY=true
      shift
      ;;
    --check)
      CHECK=true
      shift
      ;;
    --certificate)
      CERTIFICATE=${2:?--certificate needs new or a certificate id}
      shift 2
      ;;
    --url)
      NPM_URL=${2:?--url needs a base url}
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

if [[ -n $CERTIFICATE ]]; then
  [[ $CERTIFICATE =~ ^(new|[0-9]+)$ ]] \
    || die "--certificate takes new or a certificate id, not $CERTIFICATE"
fi

if [[ $APPLY == true && $CHECK == true ]]; then
  die '--apply and --check are exclusive'
fi

if [[ $CHECK == true ]]; then
  check_host
elif [[ $APPLY == true ]]; then
  apply_host
else
  render plan "$CERTIFICATE"
fi
