#!/usr/bin/env bash
# ASMP litmus — quick gate checks for registry + discovery.
# Prefer: asmp litmus  (if ~/.asmp/bin/asmp is installed)
set -euo pipefail

if command -v asmp >/dev/null 2>&1; then
  exec asmp litmus
fi
if [[ -x "${HOME}/.asmp/bin/asmp" ]]; then
  exec "${HOME}/.asmp/bin/asmp" litmus
fi

REGISTRY="${ASMP_REGISTRY_URL:-http://127.0.0.1:7700}"
PASS=0
FAIL=0

check() {
  local name="$1"
  local cmd="$2"
  echo "→ $name"
  if eval "$cmd" >/dev/null 2>&1; then
    echo "  ✓ PASS"
    PASS=$((PASS + 1))
  else
    echo "  ✗ FAIL"
    FAIL=$((FAIL + 1))
  fi
}

echo "ASMP litmus — $REGISTRY"
echo ""

check "health endpoint" "curl -fsS '$REGISTRY/health'"
check "host profile" "curl -fsS '$REGISTRY/host' | python3 -c 'import sys,json; json.load(sys.stdin)'"
check "list services" "curl -fsS '$REGISTRY/services' | python3 -c 'import sys,json; d=json.load(sys.stdin); assert isinstance(d,list)'"
check "capability index" "curl -fsS '$REGISTRY/capabilities' | python3 -c 'import sys,json; d=json.load(sys.stdin); assert \"capabilities\" in d'"
check "email.ingest lookup" "curl -fsS '$REGISTRY/capabilities?provides=email.ingest' | python3 -c 'import sys,json; d=json.load(sys.stdin); assert len(d)>=1'"
check "discover scan" "curl -fsS -X POST '$REGISTRY/discover/scan' | python3 -c 'import sys,json; d=json.load(sys.stdin); assert \"scanned\" in d'"

echo ""
echo "Results: $PASS passed, $FAIL failed"
if [[ "$FAIL" -gt 0 ]]; then
  exit 1
fi
echo "All litmus checks passed."