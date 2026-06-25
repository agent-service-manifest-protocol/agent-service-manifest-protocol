---
name: polish-asmp-docs
description: >
  Polish ASMP Mintlify docs — nav, cross-links, spec accuracy, llms.txt, and
  voice. Use when adding spec features, fixing stale pages, or docs feel
  incomplete vs the runtime.
---

# Polish ASMP docs

Site repo: `~/repos-personal/agentservicemanifest.io/docs/`

## Voice rules

- Lead with the human story: **phone book for your AIs**
- Prefer `asmp` CLI examples before raw `curl` where both work
- Ship-with-software first: `asmp.yaml` at repo root, index is cache
- Distinguish **lean spec** (protocol) from **adopt layer** (`adopt/` skills)
- No jargon wall on `what-is-asmp.mdx` — save detail for spec pages

## File map

| File | Purpose |
|------|---------|
| `docs/docs.json` | Nav order — new pages must be added here |
| `docs/llms.txt` | Agent-oriented index — update on every spec change |
| `docs/index.mdx` | Docs home cards |
| `docs/spec/*` | Normative reference |
| `docs/guides/*` | How-to (CLI, discover, ship, MCP) |
| `docs/concepts/*` | Mental models |

## Checklist for new features

When runtime or protocol gains a capability:

1. Add or update spec page under `docs/spec/`
2. Add guide under `docs/guides/` if agents need workflow help
3. Update `docs/spec/registration-api.mdx` endpoint table
4. Update `docs/guides/cli.mdx` if CLI command exists
5. Add entry to `docs/llms.txt`
6. Add page to `docs/docs.json` navigation
7. Cross-link from `what-is-asmp.mdx` or `index.mdx` if user-facing
8. Update `docs/roadmap.mdx` — mark done

## Build verify

```bash
cd ~/repos-personal/agentservicemanifest.io
npm run build
```

Fix MDX errors before ship. Build must complete with no errors.

## Preview (optional)

```bash
npm run dev
# open http://localhost:4321/docs
```

## Spec ↔ runtime accuracy pass

Read `registration-api.mdx` alongside:

```
~/repos-personal/aic-director-daemon/registry/server.py
~/repos-personal/agentservicemanifest.io/scripts/asmp
```

Every documented endpoint must exist in both runtime and CLI (or be marked "runtime only").

## Adopt layer docs

Skills live in spec repo `adopt/skills/`. Link from site docs when helpful:

- Install flow → points to `use-asmp` / INSTALL-INDEX (in repo README or ecosystem page)
- Release flow → RELEASE-INDEX in spec repo

Do not duplicate full skill text in MDX — link to GitHub paths.

## Litmus

- `npm run build` succeeds
- New pages appear in `docs.json`
- `llms.txt` links resolve on live site after deploy

## Next

`deploy-asmp-site` to publish. Do not claim docs are live until deploy completes.