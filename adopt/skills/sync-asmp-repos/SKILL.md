---
name: sync-asmp-repos
description: >
  Align contracts across ASMP's three repos — bootstrap URLs, CLI commands,
  API endpoints, MCP tools, and adopt skills. Use when repos drifted, after
  copying scripts between repos, or before ship-asmp.
---

# Sync ASMP repos

Keep the **lean spec**, **reference runtime**, and **public site** telling the same story.

## Contract surfaces (must agree)

| Contract | Authority | Consumers |
|----------|-----------|-----------|
| Registration API paths | `aic-director-daemon/registry/server.py` | Site `docs/spec/registration-api.mdx`, `scripts/asmp`, `scripts/asmp-serve.py` |
| MCP tool names | `aic-director-daemon/mcp_server/server.py` | `adopt/catalog/agent-tools.yaml`, docs `guides/mcp-integration.mdx` |
| Bootstrap install | `agentservicemanifest.io/scripts/bootstrap-asmp.sh` | `docs/install.mdx`, GitHub raw URLs everywhere |
| CLI commands | `agentservicemanifest.io/scripts/asmp` | `docs/guides/cli.mdx`, bootstrap output, `asmp-litmus.sh` |
| Ship-with-software | `docs/spec/ship-with-software.mdx` | `discover.py` manifest paths, `asmp scan` |
| Release skills | `adopt/skills/*`, `RELEASE-INDEX.md` | `use-asmp` router table |

## Sync procedure

### 1. API endpoints

Diff runtime server against site docs:

```bash
rg "path ==|do_POST|do_GET" ~/repos-personal/aic-director-daemon/registry/server.py
rg "POST|GET" ~/repos-personal/agentservicemanifest.io/docs/spec/registration-api.mdx
rg '"/' ~/repos-personal/agentservicemanifest.io/scripts/asmp
```

Every endpoint in `server.py` should appear in registration-api.mdx and (if user-facing) in `scripts/asmp`.

### 2. MCP tools

```bash
rg "@mcp.tool" ~/repos-personal/aic-director-daemon/mcp_server/server.py
```

Update `adopt/catalog/agent-tools.yaml` → `registry_mcp.tools` list.

### 3. Bootstrap bundle

These files ship together from `agentservicemanifest.io/scripts/`:

- `bootstrap-asmp.sh`
- `asmp-serve.py`
- `asmp`

Verify bootstrap curls all three to `raw.githubusercontent.com/.../agent-service-manifest-protocol/main/scripts/`.

### 4. Adopt skills

After adding a skill under `adopt/skills/`:

- Add row to `INSTALL-INDEX.md` (host) or `RELEASE-INDEX.md` (release)
- Add router row in `use-asmp/SKILL.md`

### 5. Version strings

ASMP protocol version is `0.1` everywhere (`asmp: "0.1"`). Do not bump protocol version in one repo only.

## Litmus

```bash
./adopt/scripts/asmp-coherence-check.sh
```

## When done

Return to `ship-asmp` if releasing, or `check-asmp-coherence` for a read-only audit.