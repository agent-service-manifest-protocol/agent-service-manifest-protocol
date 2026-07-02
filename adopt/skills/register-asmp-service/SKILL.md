---
name: register-asmp-service
description: >
  Register a local service with ASMP — write ~/.asmp/services/{name}.asmp.yaml
  or POST to :7700/services. Every manifest MUST include capabilities.provides.
---

# Register ASMP service

## When

You find a daemon, CLI, API, or MCP server running on this host that other agents should discover.

## Manifest minimum

```yaml
asmp: "0.1"
kind: service
name: my-service
description: One line — what it does for humans
section: tools
capabilities:
  provides:
    - tools.my-service
  requires: []
```

Use real capability names (`email.classify`, `dns.cloudflare`) when known — not just `tools.{name}`.

## Register

**File:**

```bash
# ~/.asmp/services/my-service.asmp.yaml
```

**API:**

```bash
curl -s -X POST http://127.0.0.1:7700/services \
  -H 'Content-Type: application/json' \
  -d @manifest.json
```

**MCP:**

```
service_register(name="...", description="...", capabilities_provides=["..."])
```

## Litmus

```bash
curl -s "http://127.0.0.1:7700/capabilities?provides=tools.my-service"
```