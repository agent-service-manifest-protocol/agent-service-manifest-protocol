# ASMP release index

Phone book for **shipping ASMP itself** — multi-repo releases, coherence, docs, marketing, and live site.

Read this when the task is about ASMP as a product, not about installing ASMP on a host.
For host adoption, see [INSTALL-INDEX.md](skills/use-asmp/INSTALL-INDEX.md).

## Release layer

| Skill | When | Litmus |
|-------|------|--------|
| [ship-asmp](skills/ship-asmp/SKILL.md) | Coordinated release across spec + runtime + site | All three repos pushed; `check-asmp-coherence` pass |
| [sync-asmp-repos](skills/sync-asmp-repos/SKILL.md) | Bootstrap/CLI/docs/runtime disagree | Sync checklist all green |
| [check-asmp-coherence](skills/check-asmp-coherence/SKILL.md) | Before ship, after big edits, weekly hygiene | `asmp-coherence-check.sh` pass |
| [polish-asmp-docs](skills/polish-asmp-docs/SKILL.md) | New spec feature, stale pages, nav gaps | Build clean; live `/docs` matches local |
| [polish-asmp-marketing](skills/polish-asmp-marketing/SKILL.md) | Homepage feels technical, animation wrong | Human story visible on live `/` |
| [deploy-asmp-site](skills/deploy-asmp-site/SKILL.md) | Push docs/marketing to production | Live URLs return 200; key copy present |

## Repos (canonical paths)

| Repo | Role | Remote |
|------|------|--------|
| `agent-service-manifest-protocol` | Lean spec + `adopt/` skills | `agent-service-manifest-protocol/agent-service-manifest-protocol` |
| `agentservicemanifest.io` | Docs, marketing, bootstrap, CLI | `agent-service-manifest-protocol/agentservicemanifest.io` |
| `aic-director-daemon` | Reference registry + MCP | `dshanklin-bv/aic-director-daemon` |

Default local roots: `~/repos-personal/{repo-name}`.

## Typical release sequence

```
1. sync-asmp-repos      — align cross-repo contracts
2. polish-asmp-docs     — spec pages, guides, llms.txt, docs.json
3. polish-asmp-marketing — homepage story + ship section
4. check-asmp-coherence — gate before push
5. ship-asmp            — commit + push all three repos
6. deploy-asmp-site     — npm run deploy + live verify
```

`deploy-asmp-site` is last because it publishes what was pushed to git.

## Scripts

```bash
./adopt/scripts/asmp-coherence-check.sh   # release gate
./adopt/scripts/asmp-litmus.sh            # host gate (runtime)
./adopt/scripts/discover-agent-tools.sh   # agent-surface gate
```