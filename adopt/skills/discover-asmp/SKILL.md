---
name: discover-asmp
description: >
  Find local services by capability or search query via ASMP registry (:7700).
  Use before grepping ports, reading .mcp.json files, or guessing infrastructure.
---

# Discover ASMP services

## MCP (preferred)

```
service_find(capability="dns.cloudflare")
service_find(query="email")
service_list(section="tools", healthy_only=true)
service_health("director-daemon")
```

## HTTP fallback

```bash
curl -s "http://127.0.0.1:7700/capabilities?provides=dns.cloudflare"
curl -s "http://127.0.0.1:7700/services?q=clawd"
curl -s http://127.0.0.1:7700/health
```

## If empty

1. Registry up? `curl :7700/health`
2. Manifest has `capabilities.provides`? Check `~/.asmp/services/{name}.asmp.yaml`
3. Stale in-memory registry? POST manifest or restart registry daemon

## Habit

Run during `/pre-flight` and `/takeoff` — one line: `Host registry: N services, M healthy`.