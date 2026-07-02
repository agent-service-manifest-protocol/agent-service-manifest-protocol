---
name: install-asmp-mcp-claude
description: >
  Wire ASMP registry MCP into global Claude Code config (~/.claude/settings.json).
  Merge asmp-registry under mcpServers — never overwrite unrelated servers.
---

# Install ASMP MCP — Claude Code

## Detect

```bash
test -f ~/.claude/settings.json && echo present || echo missing
rg -n asmp-registry ~/.claude/settings.json 2>/dev/null || echo not wired
```

## Merge

```json
"asmp-registry": {
  "command": "python3",
  "args": [
    "/Users/dshanklinbv/repos-personal/aic-director-daemon/mcp_server/server.py"
  ]
}
```

## Litmus

`service_list()` returns services from this host.

## Reload

Restart Claude Code or start a new session after editing global settings.