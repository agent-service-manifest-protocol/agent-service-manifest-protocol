---
name: install-asmp-mcp-grok
description: >
  Wire ASMP registry into Grok sessions via project .mcp.json and/or user skills.
  Accepts asmp-registry or director-daemon as the bridge name.
---

# Install ASMP MCP — Grok

## Surfaces

- Project: `.mcp.json` → `mcpServers.director-daemon` or `asmp-registry`
- User skills: install `use-asmp` to `~/.agents/skills/use-asmp/` or `~/.grok/skills/use-asmp/`

## Project merge (.mcp.json)

```json
"director-daemon": {
  "type": "stdio",
  "command": "python3",
  "args": [
    "/Users/dshanklinbv/repos-personal/aic-director-daemon/mcp_server/server.py"
  ]
}
```

Or duplicate entry as `asmp-registry` with the same args for searchability.

## User skill install

Copy `skills/use-asmp/` from the ASMP spec repo into the user's skills directory so Grok auto-invokes on ASMP-shaped questions.

## Litmus

Session MCP includes registry tools; or agent follows `use-asmp` and curls `:7700/health`.