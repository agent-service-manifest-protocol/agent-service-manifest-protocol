# ASMP Planning

Planning documents for the Agent Service Manifest Protocol bootstrap.

## Documents

| Doc | Purpose |
|-----|---------|
| [BOOTSTRAP-50.md](./BOOTSTRAP-50.md) | Master execution plan — 50 items in dependency order |
| `artifacts/` | Audit outputs (MCP matrix, registry consumers, litmus tests) |
| `adrs/` | Architecture decision records (capability URI, well-known bootstrap, analogs) |

## Current priority

**Tier 1 (items 1–8):** Ambient discovery — global MCP, litmus test, docs.

**Litmus test:** `service_find("email.ingest")` works from `aic-software-engineer-cockpit` with no per-repo MCP config.

## Gate criteria

Do not start Tier N+1 until Tier N gate passes. See BOOTSTRAP-50.md for each tier.

## GitHub tracking

- **Milestones:** Tier 1–7 in [agent-service-manifest-protocol](https://github.com/agent-service-manifest-protocol/agent-service-manifest-protocol/milestones)
- **Issues:** [#1]–[#50] bootstrap items — [all issues](https://github.com/agent-service-manifest-protocol/agent-service-manifest-protocol/issues?q=label%3Abootstrap)
- **Recreate:** `SKIP_SETUP=1 ./scripts/create-bootstrap-issues.sh` (idempotent)