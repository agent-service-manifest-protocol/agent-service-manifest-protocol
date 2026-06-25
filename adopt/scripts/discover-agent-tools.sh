#!/usr/bin/env bash
# Scan host for major AI coding tools and ASMP registry wiring.
# Reads catalog/agent-tools.yaml paths; reports present / wired / absent.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CATALOG="${ASMP_AGENT_CATALOG:-$ROOT/catalog/agent-tools.yaml}"

expand() {
  local p="${1/#\~/$HOME}"
  printf '%s' "$p"
}

registry_ok() {
  curl -fsS --max-time 2 http://127.0.0.1:7700/health >/dev/null 2>&1
}

mcp_wired() {
  local file="$1"
  local server="$2"
  [[ -f "$file" ]] || return 1
  rg -q "$server" "$file" 2>/dev/null
}

echo "ASMP agent-tool discovery"
echo "catalog: $CATALOG"
echo

if registry_ok; then
  echo "registry :7700  ✓"
else
  echo "registry :7700  ✗ (run install-asmp-host)"
fi
echo

# Fixed checks from catalog (YAML parse-free for portability)
check() {
  local id="$1" name="$2" priority="$3" detect_path="$4" config_file="$5" expected="$6" skill="$7"
  local present=0 wired=0
  local d c
  d="$(expand "$detect_path")"
  c="$(expand "$config_file")"

  if [[ "$detect_path" == "always" ]] || [[ -e "$d" ]]; then
    present=1
  fi

  if [[ -n "$config_file" && "$config_file" != "-" ]]; then
    if mcp_wired "$c" "$expected" || mcp_wired "$c" "director-daemon"; then
      wired=1
    fi
  elif [[ "$id" == "shell-http" ]] && registry_ok; then
    wired=1
  fi

  local pmark wmark
  [[ $present -eq 1 ]] && pmark="present" || pmark="absent"
  [[ $wired -eq 1 ]] && wmark="wired" || wmark="not wired"

  printf "  %-14s %-6s  %-7s  %-10s  → %s\n" "$name" "$priority" "$pmark" "$wmark" "$skill"
}

check cursor        Cursor       P0 "~/.cursor/mcp.json"              "~/.cursor/mcp.json"              asmp-registry install-asmp-mcp-cursor
check claude-code   "Claude Code" P0 "~/.claude/settings.json"        "~/.claude/settings.json"        asmp-registry install-asmp-mcp-claude
check codex         Codex        P0 "~/.codex/config.toml"           "~/.codex/config.toml"           asmp_registry install-asmp-mcp-codex
check grok          Grok         P1 "~/.grok/skills"                   "-"                              asmp-registry install-asmp-mcp-grok
check windsurf      Windsurf     P2 "~/.codeium/windsurf/mcp_config.json" "~/.codeium/windsurf/mcp_config.json" asmp-registry install-asmp-mcp-windsurf
check shell-http    "Shell/HTTP" P0 "always"                           "-"                              asmp-registry install-asmp-host

echo
echo "Delegate repairs via skills/use-asmp/INSTALL-INDEX.md"