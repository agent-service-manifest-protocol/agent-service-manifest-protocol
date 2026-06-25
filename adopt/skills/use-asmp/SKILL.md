---
name: use-asmp
description: >
  Router for ASMP (Agent Service Manifest Protocol). Use when installing ASMP,
  wiring registry MCP, discovering local services, registering manifests, auditing
  agent-tool surfaces, or when an agent asks what handles a capability on this machine.
  Do not improvise install steps — read INSTALL-INDEX.md and delegate to child skills.
---

# Use ASMP

ASMP is the host inventory on `http://127.0.0.1:7700`. This skill routes work to specialized child skills. It does not install everything itself.

## Primary rule

1. Read `INSTALL-INDEX.md` in this directory.
2. Read `adopt/catalog/agent-tools.yaml` in the ASMP spec repo (or `~/.asmp/catalog/agent-tools.yaml` if synced).
3. Run the smallest litmus check first.
4. Delegate to exactly one child skill per surface.

## Litmus (run before claiming ASMP works)

```bash
curl -s http://127.0.0.1:7700/health
```

Pass: JSON with service counts (director-daemon registry) or `"status": "ok"` (bootstrap server).

## Router table

| Situation | Child skill |
|-----------|-------------|
| No `~/.asmp/host.yaml` or `:7700` down | `install-asmp-host` |
| Need to wire Cursor global MCP | `install-asmp-mcp-cursor` |
| Need to wire Claude Code global MCP | `install-asmp-mcp-claude` |
| Need to wire Codex MCP | `install-asmp-mcp-codex` |
| Need to wire Grok / project MCP | `install-asmp-mcp-grok` |
| Audit which AI tools are present + wired | `discover-agent-tools` |
| Find a service by capability | `discover-asmp` |
| Register a new local service | `register-asmp-service` |

Child skills live alongside this one under `skills/` in the ASMP spec repo, or at `~/.agents/skills/<name>/` when installed for the user.

## Discovery habit

Before guessing ports or grepping repos:

```
service_find(capability="dns.cloudflare")
# or
curl -s "http://127.0.0.1:7700/capabilities?provides=dns.cloudflare"
```

## MCP bridge

Preferred global server name: `asmp-registry`

```json
{
  "command": "python3",
  "args": ["/path/to/aic-director-daemon/mcp_server/server.py"]
}
```

`director-daemon` MCP is the same bridge under a different name. Either works; prefer `asmp-registry` for searchability.

## Continuous discovery

Agent runtimes change. On takeoff, pre-flight, or after installing a new coding tool, run `discover-agent-tools` to scan the host against `catalog/agent-tools.yaml` and report drift.

## Docs

- https://agentservicemanifest.io/docs/install
- https://agentservicemanifest.io/docs/guides/ambient-discovery