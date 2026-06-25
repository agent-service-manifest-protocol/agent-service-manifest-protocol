---
name: discover-asmp
description: >
  Find local services by capability or search query via ASMP registry (:7700).
  Use before grepping ports, reading .mcp.json files, or guessing infrastructure.
  When lookup misses but the service is real, drop a discovery todo so the gap self-heals.
---

# Discover ASMP services

## MCP (preferred)

```
service_find(capability="dns.cloudflare")
service_find(query="email")
service_list(section="tools", healthy_only=true)
service_health("director-daemon")
service_scan()
service_todos()
```

## CLI

```bash
asmp find --capability email.ingest
asmp find -q director
asmp scan
asmp todos
```

## HTTP fallback

```bash
curl -s "http://127.0.0.1:7700/capabilities?provides=dns.cloudflare"
curl -s "http://127.0.0.1:7700/services?q=clawd"
curl -s -X POST http://127.0.0.1:7700/discover/scan
curl -s http://127.0.0.1:7700/discoveries
curl -s http://127.0.0.1:7700/health
```

## If empty — self-heal before giving up

Lookup miss does **not** mean the service does not exist. It may be unregistered.

If you observed something real (running process, repo, CLI) that ASMP cannot find:

```
service_todo(
  name="mystery-daemon",
  note="what you observed",
  repo="~/repos-aic/mystery",
  hint="add asmp.yaml and announce"
)
```

Or:

```bash
asmp todo mystery-daemon --note "Runs on :9090" --repo ~/repos-aic/mystery
```

Rules:

- Append-only — never pretend it is registered
- Real systems only — not wishlist items
- Check `asmp todos` / `service_todos()` before duplicating

Promote later: author `asmp.yaml` → `asmp scan` or `asmp announce`.

## If empty — registry troubleshooting

1. Registry up? `curl :7700/health`
2. Manifest has `capabilities.provides`? Check `~/.asmp/services/{name}.asmp.yaml`
3. Stale in-memory registry? `asmp scan` or `POST /discover/scan`
4. New repo? Run `asmp scan` before `service_find`

## Habit

Run during `/pre-flight` and `/takeoff`:

1. `service_scan()` or `asmp scan` — pick up new shipped manifests
2. `service_list()` or `asmp health` — one line: `Host registry: N services, M healthy`
3. `service_todos()` — note any pending discovery gaps to promote