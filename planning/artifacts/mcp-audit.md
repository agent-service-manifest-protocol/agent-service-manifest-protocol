# MCP config audit

**Date:** 2026-06-25

## Summary

| Metric | Count |
|--------|-------|
| Repo `.mcp.json` files | 148 |
| With `director-daemon` / `asmp-registry` | 146 |
| Without registry MCP | 2 |

## Global configs

- **~/.cursor/mcp.json**: registry MCP = **NO**; servers: firecrawl_composio, plaud
- **~/.claude/settings.json**: registry MCP = **NO**; servers: ciso-mcp, forge-forge, railguey, rhea-diagrams, vercel

## Repos without registry MCP

- `repos-aic/aic-diligence` — supabase
- `repos-aic/wrike` — wrike

## Finding

Per-repo configs are widespread (146/148), but **global Cursor and Claude Code configs lack registry MCP**.
Repos without any `.mcp.json` still start blind. Global config is the Tier 1 fix.
