---
name: install-asmp-mcp-cursor
description: >
  Wire ASMP registry MCP into global Cursor config (~/.cursor/mcp.json).
  Merge asmp-registry — never overwrite existing mcpServers. Reload Cursor after.
---

# Install ASMP MCP — Cursor

## Detect

```bash
test -f ~/.cursor/mcp.json && echo present || echo missing
rg -n asmp-registry ~/.cursor/mcp.json 2>/dev/null || echo not wired
```

## Merge (do not overwrite)

Add under `mcpServers`:

```json
"asmp-registry": {
  "command": "python3",
  "args": [
    "/Users/dshanklinbv/repos-personal/aic-director-daemon/mcp_server/server.py"
  ]
}
```

Adapt the path if `aic-director-daemon` lives elsewhere on this host.

## Litmus

In Cursor after reload: call `service_list()` or `service_find(capability="email.classify")`.

## Notes

Per-repo `.mcp.json` is not enough for repos without one. Global config is the Tier-1 fix.