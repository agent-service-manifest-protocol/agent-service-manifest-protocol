---
name: polish-asmp-marketing
description: >
  Polish ASMP marketing homepage — human story, See it animation, ship-with-
  software section, typography, and visual QA. Use when homepage feels technical,
  animation shows grep/ports, or marketing lags behind spec.
---

# Polish ASMP marketing

Site repo: `~/repos-personal/agentservicemanifest.io/`

## Files

| File | What it controls |
|------|------------------|
| `src/pages/index.astro` | Page structure, copy, sections |
| `public/marketing.js` | See it animation phases |
| `public/marketing.css` | Typography, colors, motion |

## Story rules (non-negotiable)

The homepage tells a **human story**, not a debugger session.

| Use | Avoid |
|-----|-------|
| "Phone book for your AIs" | `grep`, port numbers, API paths |
| "Inbox helper" | `inbox-triage`, service names from inventory |
| "Your AI" / "New session" | Terminal commands in the animation |
| "250ms" discovery | Technical latency diagrams |

The **See it** animation contrast lines ("Dig through old setups") may mention pain — the **answer** must be human.

## Required sections

1. **Hero** — phone book headline + typing line
2. **See it** — ask once, find in 250ms (human labels)
3. **Ship with software** — `asmp.yaml`, scan, announce
4. **Install** — bootstrap one-liner + agent prompt link
5. **What / Stack / Host / Manifest / Registration** — three-piece spec story
6. **Roadmap** — honest phase status

## Visual polish

- Fonts: Instrument Serif + DM Sans + JetBrains Mono (already in `index.astro`)
- Amber accent on ASMP layer in stack diagram
- Animation: `data-phase` driven, accessible `aria-label` on demo
- Mobile: nav toggle works, demo readable at 375px

Use `frontend-design` skill judgment for spacing and hierarchy — avoid template-default look.

## Verify locally

```bash
cd ~/repos-personal/agentservicemanifest.io
npm run dev
# http://localhost:4321/
```

Watch full See it animation cycle. Confirm no technical service names flash in the answer panel.

## Verify live (after deploy)

```bash
curl -sL https://asmp.eidosagi.com/ | rg "Inbox helper|phone book|Ship with software"
curl -sL https://asmp.eidosagi.com/ | rg "grep -r|inbox-triage|:7700/capabilities" | head -3
```

Second command should return empty or only oblique references — not the old demo.

## Litmus

- Hero says "phone book"
- See it answer says "Inbox helper" (or equivalent human label)
- Ship section links to `/docs/spec/ship-with-software`
- `npm run build` succeeds

## Next

`deploy-asmp-site` to publish marketing changes.