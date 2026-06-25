---
name: discover-agent-tools
description: >
  Continuously discover which major AI coding tools are on this host and whether
  each is wired to the ASMP registry (:7700). Use on takeoff, pre-flight, after
  installing Cursor/Claude/Codex/Grok, or when ambient discovery drifts.
---

# Discover agent tools

Scan the host against `catalog/agent-tools.yaml`. Report present / wired / missing.

## Steps

1. Read `catalog/agent-tools.yaml`.
2. Run `scripts/discover-agent-tools.sh` (or reproduce its checks).
3. For each tool marked `present` but not `wired`, delegate to the `install_skill` from the catalog.
4. Summarize: `Agent surfaces: X/Y wired` with a one-line table.

## What "wired" means

- Global or project MCP config includes `asmp-registry` (or `director-daemon` pointing at the same `server.py`)
- OR shell-http fallback: `:7700/health` responds and the agent has curl

## What to register

When a tool is present and wired, optionally write `~/.asmp/agents/{id}.asmp.yaml`:

```yaml
asmp: "0.1"
kind: agent-surface
name: cursor
capabilities:
  provides: [mcp.client]
  requires: [registry.local]
config_path: ~/.cursor/mcp.json
wired: true
last_scan: "2026-06-25T12:00:00Z"
```

## Drift signals

- Catalog says P0 tool present on disk but MCP entry missing
- Repo has `.mcp.json` without registry server (see planning/artifacts/mcp-audit.md)
- `director-daemon` used instead of `asmp-registry` (works but harder to search — note, don't fail)

## After repair

Tell the user which apps to reload (Cursor, Claude Code, Codex restart).