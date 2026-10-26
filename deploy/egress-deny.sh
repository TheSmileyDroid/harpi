#!/usr/bin/env bash
set -euo pipefail

CONTAINER="harpi-backend"
CHAIN="DOCKER-USER"
TAG="harpi-egress-deny"
IPV4_DESTINATIONS=(127.0.0.0/8 10.0.0.0/8 172.16.0.0/12 192.168.0.0/16 169.254.0.0/16 224.0.0.0/4)
IPV6_DESTINATIONS=(::1/128 fc00::/7 fe80::/10 ff00::/8)

die() {
  printf 'egress deny: %s\n' "$1" >&2
  exit 1
}

usage() {
  printf 'usage: %s <apply|remove|print> [--container NAME] [--source ADDRESS]...\n' \
    "${0##*/}" >&2
}

binary_for() {
  case "$1" in
    *:*) printf 'ip6tables' ;;
    *) printf 'iptables' ;;
  esac
}

is_address() {
  [[ $1 =~ ^[0-9]{1,3}(\.[0-9]{1,3}){3}$ || $1 == *:* ]]
}

destinations_for() {
  if [[ "$1" == *:* ]]; then
    printf '%s\n' "${IPV6_DESTINATIONS[@]}"
  else
    printf '%s\n' "${IPV4_DESTINATIONS[@]}"
  fi
}

container_addresses() {
  local addresses address
  addresses=$(docker inspect --format \
    '{{range .NetworkSettings.Networks}}{{.IPAddress}} {{.GlobalIPv6Address}} {{end}}' \
    "$CONTAINER") || die "cannot inspect $CONTAINER"
  for address in $addresses; do
    is_address "$address" || continue
    printf '%s\n' "$address"
  done
}

print_rules() {
  local source destination
  for source in "$@"; do
    while IFS= read -r destination; do
      printf '%s -I %s -s %s -d %s -m comment --comment %s -j DROP\n' \
        "$(binary_for "$source")" "$CHAIN" "$source" "$destination" "$TAG"
    done < <(destinations_for "$source")
  done
}

apply_rules() {
  local source destination binary listing installed=0
  local -a match
  for source in "$@"; do
    binary=$(binary_for "$source")
    listing=$("$binary" -S "$CHAIN" 2>&1) \
      || die "$binary cannot list $CHAIN: $listing"
  done
  for source in "$@"; do
    binary=$(binary_for "$source")
    while IFS= read -r destination; do
      match=(-s "$source" -d "$destination" -m comment --comment "$TAG" -j DROP)
      if "$binary" -C "$CHAIN" "${match[@]}" 2>/dev/null; then
        continue
      fi
      "$binary" -I "$CHAIN" "${match[@]}" \
        || die "cannot insert rule for $source to $destination"
      installed=$((installed + 1))
    done < <(destinations_for "$source")
  done
  printf 'installed %d rule(s)\n' "$installed"
}

remove_rules() {
  local binary rule listing removed=0
  local -a tokens
  for binary in iptables ip6tables; do
    listing=$("$binary" -S "$CHAIN" 2>&1) || {
      [[ $binary == ip6tables ]] && continue
      die "$binary cannot list $CHAIN: $listing"
    }
    while IFS= read -r rule; do
      [[ $rule == *"$TAG"* ]] || continue
      read -r -a tokens <<< "${rule#-A }"
      "$binary" -D "${tokens[@]}" || die "cannot delete rule: $rule"
      removed=$((removed + 1))
    done < <(printf '%s\n' "$listing")
  done
  printf 'removed %d rule(s)\n' "$removed"
}

action=${1:-}
[[ -n $action ]] || {
  usage
  exit 2
}
shift

sources=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --container)
      CONTAINER=${2:?--container needs a name}
      shift 2
      ;;
    --source)
      address=${2:?--source needs an address}
      is_address "$address" || die "--source is not an address: $address"
      sources+=("$address")
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

case "$action" in
  print | apply)
    if [[ ${#sources[@]} -eq 0 ]]; then
      mapfile -t sources < <(container_addresses)
    fi
    [[ ${#sources[@]} -gt 0 ]] \
      || die "$CONTAINER has no address; is the container running on harpi-edge?"
    if [[ $action == print ]]; then
      print_rules "${sources[@]}"
    else
      apply_rules "${sources[@]}"
    fi
    ;;
  remove)
    remove_rules
    ;;
  *)
    usage
    exit 2
    ;;
esac
