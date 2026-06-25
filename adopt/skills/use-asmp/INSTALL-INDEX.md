# ASMP install index

Phone book for installation skills. Agents read this before doing any ASMP work.

## Host layer

| Skill | When | Litmus |
|-------|------|--------|
| [install-asmp-host](../install-asmp-host/SKILL.md) | No `~/.asmp/`, registry not listening | `curl :7700/health` |

## Agent surfaces (wire MCP)

| Skill | When | Litmus |
|-------|------|--------|
| [install-asmp-mcp-cursor](../install-asmp-mcp-cursor/SKILL.md) | Cursor installed, no `asmp-registry` in `~/.cursor/mcp.json` | `service_list()` in Cursor |
| [install-asmp-mcp-claude](../install-asmp-mcp-claude/SKILL.md) | Claude Code, missing global MCP | `service_find` in Claude session |
| [install-asmp-mcp-codex](../install-asmp-mcp-codex/SKILL.md) | `~/.codex/config.toml` exists, no asmp MCP | Codex MCP panel shows registry |
| [install-asmp-mcp-grok](../install-asmp-mcp-grok/SKILL.md) | Grok project, missing registry MCP | Session has `asmp-registry` or `director-daemon` |

## Operations

| Skill | When | Litmus |
|-------|------|--------|
| [discover-agent-tools](../discover-agent-tools/SKILL.md) | Takeoff, audit, new tool installed, drift suspected | Report N/M surfaces wired |
| [discover-asmp](../discover-asmp/SKILL.md) | "What handles X?" before building | Non-empty capability query |
| [register-asmp-service](../register-asmp-service/SKILL.md) | New daemon/API found on host | `GET /services/{name}` |

## Catalog

Living list of agent tools: [`catalog/agent-tools.yaml`](../../catalog/agent-tools.yaml)

Update the catalog when a new major AI coding tool ships. Scanners diff disk against this file — do not hardcode tool paths in skills.

## Scan script

```bash
./scripts/discover-agent-tools.sh
```

Or ask an agent to follow `discover-agent-tools` skill.