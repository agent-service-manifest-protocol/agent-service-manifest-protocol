---
name: deploy-asmp-site
description: >
  Build and deploy agentservicemanifest.io to Cloudflare Pages and verify live
  URLs. Use after ship-asmp, when docs or marketing changed, or Daniel says
  update the website / get ASMP online.
---

# Deploy ASMP site

Publishes marketing + docs to production. Git push alone is not enough.

## Repo

```bash
cd ~/repos-personal/agentservicemanifest.io
```

## Pre-deploy

1. `git status` — commit all intended changes on `main`
2. `npm run build` — must pass locally first
3. Optional: `polish-asmp-docs` and `polish-asmp-marketing` already done

## Deploy

```bash
npm run deploy
```

Runs `astro build` + `wrangler pages deploy dist --project-name agentservicemanifest-io`.

Requires Cloudflare auth (wrangler logged in or `CLOUDFLARE_API_TOKEN`).

## Live URLs

| URL | Expected |
|-----|----------|
| https://asmp.eidosagi.com | Marketing + `/docs` |
| https://agentservicemanifest-io.pages.dev | Pages default |
| https://agentservicemanifest.io | Apex (may pending DNS) |

## Post-deploy verification

```bash
# Marketing story
curl -sL https://asmp.eidosagi.com/ | rg -c "phone book"

# Key doc pages
curl -sL -o /dev/null -w "%{http_code}\n" https://asmp.eidosagi.com/docs/guides/cli
curl -sL -o /dev/null -w "%{http_code}\n" https://asmp.eidosagi.com/docs/spec/ship-with-software
curl -sL -o /dev/null -w "%{http_code}\n" https://asmp.eidosagi.com/docs/install

# Bootstrap scripts (GitHub raw — independent of Pages, but verify on release)
curl -fsSL -o /dev/null -w "%{http_code}\n" \
  https://raw.githubusercontent.com/agent-service-manifest-protocol/agent-service-manifest-protocol/main/scripts/bootstrap-asmp.sh
```

All HTTP codes should be `200`.

## Registry announce

After deploy, handshake the site manifest so the host index knows it's live:

```bash
asmp announce ~/repos-personal/agentservicemanifest.io/asmp.yaml
asmp get agentservicemanifest-io
```

## CI alternative

`.github/workflows/deploy.yml` deploys on push to `main` when secrets are set:

- `CLOUDFLARE_API_TOKEN`
- `CLOUDFLARE_ACCOUNT_ID`

If CI is wired, push to `main` may auto-deploy — still run live verification.

## Litmus

- `https://asmp.eidosagi.com/docs/guides/cli` title contains `CLI reference`
- Homepage contains `Ship with software` section
- `asmp find --capability asmp.marketing` returns healthy or registered entry

## On failure

| Problem | Action |
|---------|--------|
| Build fails | Fix MDX/Astro errors, re-run `npm run build` |
| Wrangler auth | `npx wrangler login` or set API token |
| Live stale | Purge Cloudflare cache; confirm deploy URL in wrangler output |
| Docs 404 | Check `docs.json` nav and `npm run build` output page list |