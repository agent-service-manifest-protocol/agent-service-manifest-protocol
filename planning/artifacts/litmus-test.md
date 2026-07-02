# Litmus test — Tier 1 gate

**Date:** 2026-06-25  
**Repo:** `aic-software-engineer-cockpit` (global MCP, no repo-specific change required)  
**Registry:** `http://127.0.0.1:7700`

## Test: `email.ingest` capability lookup

```bash
curl -s "http://127.0.0.1:7700/capabilities?provides=email.ingest"
```

## Result: PASS (discovery)

| Field | Value |
|-------|-------|
| Service | `email` |
| Description | Email ingestion, parsing, threading, entity extraction |
| Port | `8787` |
| Repo | `~/repos-personal/reeves-email` |
| Capabilities | `email.ingest`, `email.parse`, `email.thread`, `email.entity` |
| Health | Unhealthy (connection refused — email daemon not running) |

Discovery works. Health reflects runtime state correctly.

## Test: `email.classify` via director-daemon

```bash
curl -s "http://127.0.0.1:7700/capabilities?provides=email.classify"
```

Returns `director-daemon` on port `7400` (process supervisor path).

## Global MCP changes applied

| Config | Change |
|--------|--------|
| `~/.cursor/mcp.json` | Added `asmp-registry` → director-daemon MCP server |
| `~/.claude/settings.json` | Added `asmp-registry` → director-daemon MCP server |

**Note:** Cursor may require reload/restart to pick up global MCP changes.

## Gate status

- [x] Registry API returns capability matches
- [x] Global Cursor MCP configured
- [x] Global Claude Code MCP configured
- [ ] Verify `service_find` in live Cursor session after reload (manual)