---
name: ship-asmp
description: >
  Coordinated ASMP release across spec, runtime, and website repos. Use when
  shipping a feature end-to-end, cutting a v0.1.x release, or Daniel says
  "ship ASMP", "release ASMP", or "land the ASMP work".
---

# Ship ASMP

Multi-repo release. Do not push one repo and forget the others.

## Read first

1. [RELEASE-INDEX.md](../../RELEASE-INDEX.md) — repo map and sequence
2. Run `check-asmp-coherence` (or `adopt/scripts/asmp-coherence-check.sh`) — must pass before push

## Repos and order

| Order | Repo | What ships |
|-------|------|------------|
| 1 | `aic-director-daemon` | Registry API, `discover.py`, MCP tools (`service_scan`, …) |
| 2 | `agent-service-manifest-protocol` | `adopt/` skills, catalog, coherence scripts |
| 3 | `agentservicemanifest.io` | Docs MDX, marketing, `scripts/asmp`, bootstrap |

Runtime first (consumers depend on API). Spec second (documents the API). Site last (publishes docs + bootstrap URLs).

## Pre-ship checklist

- [ ] `asmp litmus` passes on this host
- [ ] `adopt/scripts/asmp-coherence-check.sh` passes
- [ ] No uncommitted work in the three repos (or intentional WIP called out)
- [ ] Bootstrap raw URLs in docs match `main` branch paths on GitHub
- [ ] New API endpoints documented in `docs/spec/registration-api.mdx`
- [ ] `adopt/catalog/agent-tools.yaml` MCP tool list matches `mcp_server/server.py`

## Commit messages

One commit per repo minimum. Use complete sentences. Example:

```
Add ASMP source manifest discovery and service_scan MCP tool

Scan shipped asmp.yaml files into host index, support announce handshake,
background scan loop, and MCP service_scan for agent-triggered discovery.
```

## Push

```bash
cd ~/repos-personal/aic-director-daemon && git push origin main
cd ~/repos-personal/agent-service-manifest-protocol && git push origin main
cd ~/repos-personal/agentservicemanifest.io && git push origin main
```

## Post-ship

Delegate to `deploy-asmp-site` — git push does not update Cloudflare Pages.

```bash
asmp announce ~/repos-personal/agentservicemanifest.io/asmp.yaml
```

## Litmus

- All three remotes at expected commits
- `curl -s https://asmp.eidosagi.com/docs/guides/cli` contains `CLI reference`
- `asmp find --capability asmp.marketing` returns `agentservicemanifest-io`

## Do not

- Push bootstrap script changes without pushing `scripts/asmp` and `scripts/asmp-serve.py` in the same site release
- Ship runtime API changes without updating site spec docs
- Skip coherence check because "it's just docs"