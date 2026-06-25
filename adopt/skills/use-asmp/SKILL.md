---
name: use-asmp
description: >
  Router for ASMP (Agent Service Manifest Protocol). Use when installing ASMP,
  wiring registry MCP, discovering local services, registering manifests, auditing
  agent-tool surfaces, shipping ASMP releases, deploying the website, or when an
  agent asks what handles a capability on this machine. Do not improvise — read
  INSTALL-INDEX.md (host) or RELEASE-INDEX.md (product) and delegate to child skills.
---

# Use ASMP

ASMP is the host inventory on `http://127.0.0.1:7700`. This skill routes work to specialized child skills. It does not install everything itself.

## Primary rule

1. **Host work** → read `INSTALL-INDEX.md` in this directory.
2. **Release work** (ship, deploy, docs, marketing, coherence) → read `RELEASE-INDEX.md` in `adopt/`.
3. Read `adopt/catalog/agent-tools.yaml` in the ASMP spec repo (or `~/.asmp/catalog/agent-tools.yaml` if synced).
4. Run the smallest litmus check first (`asmp litmus` for host, `asmp-coherence-check.sh` for release).
5. Delegate to exactly one child skill per task.

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

## Release router table

| Situation | Child skill |
|-----------|-------------|
| Ship coordinated release across 3 repos | `ship-asmp` |
| Bootstrap/CLI/docs/runtime disagree | `sync-asmp-repos` |
| Pre-ship gate or "is ASMP in sync?" | `check-asmp-coherence` |
| Docs stale, new spec page, nav gaps | `polish-asmp-docs` |
| Homepage technical, animation wrong | `polish-asmp-marketing` |
| Push site to asmp.eidosagi.com | `deploy-asmp-site` |

Child skills live under `adopt/skills/` in the ASMP spec repo, or at `~/.agents/skills/<name>/` when installed for the user.

## Discovery habit

Before guessing ports or grepping repos:

```
service_scan()
service_find(capability="dns.cloudflare")
# or
curl -s "http://127.0.0.1:7700/capabilities?provides=dns.cloudflare"
```

If lookup misses but you found real software with no manifest, **self-heal**:

```
service_todo(name="...", note="what you observed", repo="...")
# or: asmp todo <name> --note "..."
```

Review backlog: `service_todos()` or `asmp todos`. Promote with `asmp.yaml` + announce.

## Boundary habit

When natural-language discovery returns multiple plausible services, do not
blindly trust the top ranked result. Use the ASMP boundary pattern:

1. Read the top candidates and their manifest evidence.
2. Prefer `owns` over `supports`, and `supports` over generic `provides`.
3. Apply `aliases`, `positive_examples`, `negative_examples`, and `anti_routes`
   as routing evidence.
4. If two services remain close, use or create an external routing-policy file
   owned by the host or organization.
5. Return `owner`, `confidence`, `runner_up`, `rule_hits`, and `alternates`.
6. Store durable learning in manifests, policy, or the local memory system; do
   not bury the correction in a chat transcript.

ASMP is the interconnect and discovery layer. It should find candidates and
expose evidence. Local policy decides close ownership boundaries.

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
- https://agentservicemanifest.io/docs/guides/cli
- https://agentservicemanifest.io/docs/guides/ambient-discovery
- `adopt/RELEASE-INDEX.md` — release skill phone book (in spec repo)
