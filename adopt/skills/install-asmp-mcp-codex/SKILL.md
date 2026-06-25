---
name: install-asmp-mcp-codex
description: >
  Wire ASMP registry MCP into Codex (~/.codex/config.toml). TOML format — do not
  paste JSON from Cursor install skill.
---

# Install ASMP MCP — Codex

## Detect

```bash
test -f ~/.codex/config.toml && echo present || echo missing
rg -n asmp_registry ~/.codex/config.toml 2>/dev/null || echo not wired
```

## Merge

Add to `~/.codex/config.toml`:

```toml
[mcp_servers.asmp_registry]
command = "python3"
args = ["/Users/dshanklinbv/repos-personal/aic-director-daemon/mcp_server/server.py"]
```

Adapt path to local `aic-director-daemon` checkout.

## Litmus

Codex session can call `service_list` / `service_find`.

## Reload

Restart Codex after editing config.toml.