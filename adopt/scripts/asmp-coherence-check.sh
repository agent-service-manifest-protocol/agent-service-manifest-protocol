#!/usr/bin/env bash
# ASMP coherence gate — repos, live site, bootstrap URLs, runtime parity.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SITE="${ASMP_SITE_REPO:-$HOME/repos-personal/agentservicemanifest.io}"
RUNTIME="${ASMP_RUNTIME_REPO:-$HOME/repos-personal/aic-director-daemon}"
LIVE="${ASMP_LIVE_URL:-https://asmp.eidosagi.com}"
RAW_BASE="https://raw.githubusercontent.com/agent-service-manifest-protocol/agentservicemanifest.io/main/scripts"
PASS=0
FAIL=0
WARN=0

page_has() {
  local url="$1" pattern="$2"
  local tmp
  tmp="$(mktemp)"
  curl -sL "$url" -o "$tmp" 2>/dev/null || true
  rg -q "$pattern" "$tmp"
  local rc=$?
  rm -f "$tmp"
  return $rc
}

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

warn() {
  local name="$1"
  local cmd="$2"
  echo "→ $name"
  if eval "$cmd" >/dev/null 2>&1; then
    echo "  ✓ PASS"
    PASS=$((PASS + 1))
  else
    echo "  ⚠ WARN"
    WARN=$((WARN + 1))
  fi
}

echo "ASMP coherence check"
echo "  spec:  $ROOT"
echo "  site:  $SITE"
echo "  live:  $LIVE"
echo ""

# Host runtime
if command -v asmp >/dev/null 2>&1; then
  ASMP=asmp
elif [[ -x "${HOME}/.asmp/bin/asmp" ]]; then
  ASMP="${HOME}/.asmp/bin/asmp"
else
  ASMP=""
fi

if [[ -n "$ASMP" ]]; then
  check "host litmus" "$ASMP litmus"
else
  warn "host litmus" "curl -fsS http://127.0.0.1:7700/health"
fi

# Live marketing story
check "live: phone book copy" "curl -fsSL '$LIVE/' | rg -q 'phone book'"
check "live: human See it answer" "curl -fsSL '$LIVE/' | rg -q 'Inbox helper'"
check "live: ship-with-software section" "curl -fsSL '$LIVE/' | rg -q 'Ship with software'"

# Live docs
check "live: CLI docs" "page_has '$LIVE/docs/guides/cli' 'CLI reference'"
check "live: ship-with-software spec" "page_has '$LIVE/docs/spec/ship-with-software' 'asmp.yaml'"

# Bootstrap bundle on GitHub (warn — repo may be private)
warn "raw: bootstrap-asmp.sh" "curl -fsSL -o /dev/null '$RAW_BASE/bootstrap-asmp.sh'"
warn "raw: asmp CLI" "curl -fsSL -o /dev/null '$RAW_BASE/asmp'"
warn "raw: asmp-serve.py" "curl -fsSL -o /dev/null '$RAW_BASE/asmp-serve.py'"

# Local bootstrap bundle must exist
check "local: bootstrap-asmp.sh" "test -f '$SITE/scripts/bootstrap-asmp.sh'"
check "local: asmp CLI" "test -f '$SITE/scripts/asmp'"
check "local: asmp-serve.py" "test -f '$SITE/scripts/asmp-serve.py'"

# Bootstrap installs CLI
check "bootstrap mentions asmp CLI" "rg -q 'scripts/asmp' '$SITE/scripts/bootstrap-asmp.sh'"

# API parity: discover/scan in runtime and bootstrap server
if [[ -f "$RUNTIME/registry/server.py" ]]; then
  check "runtime: /discover/scan" "rg -q '/discover/scan' '$RUNTIME/registry/server.py'"
  check "runtime: /services/announce" "rg -q '/services/announce' '$RUNTIME/registry/server.py'"
fi
if [[ -f "$SITE/scripts/asmp-serve.py" ]]; then
  check "bootstrap server: /discover/scan" "rg -q '/discover/scan' '$SITE/scripts/asmp-serve.py'"
  check "bootstrap server: /services/announce" "rg -q '/services/announce' '$SITE/scripts/asmp-serve.py'"
fi

# CLI parity
if [[ -f "$SITE/scripts/asmp" ]]; then
  check "CLI: scan command" "rg -q 'cmd_scan' '$SITE/scripts/asmp'"
  check "CLI: litmus command" "rg -q 'cmd_litmus' '$SITE/scripts/asmp'"
fi

# Docs nav includes CLI guide
check "docs.json: cli guide" "rg -q 'guides/cli' '$SITE/docs/docs.json'"

# Release skills indexed
check "RELEASE-INDEX: ship-asmp" "test -f '$ROOT/adopt/skills/ship-asmp/SKILL.md'"
check "RELEASE-INDEX: deploy-asmp-site" "test -f '$ROOT/adopt/skills/deploy-asmp-site/SKILL.md'"

# MCP catalog lists service_scan
warn "catalog: service_scan" "rg -q 'service_scan' '$ROOT/adopt/catalog/agent-tools.yaml'"
warn "catalog: service_todo" "rg -q 'service_todo' '$ROOT/adopt/catalog/agent-tools.yaml'"
warn "catalog: service_todos" "rg -q 'service_todos' '$ROOT/adopt/catalog/agent-tools.yaml'"

# Repo cleanliness (warn only)
for repo in "$ROOT" "$SITE" "$RUNTIME"; do
  if [[ -d "$repo/.git" ]]; then
    name="$(basename "$repo")"
    warn "git clean: $name" "test -z \"\$(git -C '$repo' status --porcelain)\""
  fi
done

echo ""
echo "Results: $PASS passed, $FAIL failed, $WARN warnings"
if [[ "$FAIL" -gt 0 ]]; then
  exit 1
fi
echo "Coherence check passed."