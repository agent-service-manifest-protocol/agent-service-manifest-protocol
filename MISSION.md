# ASMP — Agent Service Manifest Protocol

## Vision

The declaration standard for AI-native personal infrastructure. Agents build services. ASMP registers them. Any tool — supervisor, dashboard, router, policy engine — consumes the manifest.

MCP standardized tool discovery. A2A standardized agent communication. ASMP standardizes the host layer: what services run here, how agents register new ones, and how mods extend them.

## Status: Incubation

Single maintainer. Proving the spec against 35+ real services in the Reeves ecosystem.

---

## Milestones

### Slice 1: Spec v0.1
**Status: DONE**

- [x] Host Profile schema (device, capabilities, policy, registry path)
- [x] Service Manifest schema (identity, runtime, network, capabilities, data, mods, observability, display)
- [x] Registration Protocol API (CRUD for services, mod attachment, host profile, capability query)
- [x] Positioning doc (MCP = tools, A2A = agents, ASMP = host)
- [x] Mod system design (agents that attach to services as capability multipliers)

### Slice 2: JSON Schema
**Status: NOT STARTED**

- [ ] Formal JSON Schema for Host Profile
- [ ] Formal JSON Schema for Service Manifest
- [ ] Validation library (Python + TypeScript)
- [ ] Schema tests against example manifests

### Slice 3: Reference Registration Server
**Status: NOT STARTED**

- [ ] Python server on localhost (HTTP API)
- [ ] Reads/writes `~/.asmp/services/` directory
- [ ] Validates manifests against JSON Schema
- [ ] Policy enforcement (requires_approval, allowed_ports)
- [ ] LaunchAgent/systemd generation from manifest
- [ ] Caddy route generation from endpoint declarations
- [ ] Health check orchestration

### Slice 4: Reeves Migration
**Status: NOT STARTED**

- [ ] Convert all 35+ services to .asmp.yaml manifests
- [ ] Dashboard reads from `~/.asmp/services/` instead of services.yaml
- [ ] Reeves platform reads from `~/.asmp/services/` instead of apps.yaml
- [ ] Deprecate apps.yaml and services.yaml
- [ ] One registry, many consumers

### Slice 5: Python SDK
**Status: NOT STARTED**

- [ ] `asmp.register(manifest)` — register a service
- [ ] `asmp.discover(capability)` — find services by capability
- [ ] `asmp.attach_mod(service, mod)` — attach a mod
- [ ] `asmp.health()` — check service health
- [ ] pip installable

### Slice 6: TypeScript SDK
**Status: NOT STARTED**

- [ ] Same API surface as Python SDK
- [ ] npm installable

### Slice 7: MCP Bridge
**Status: NOT STARTED**

- [ ] Auto-generate MCP tool manifests from ASMP service capabilities
- [ ] Service registered via ASMP automatically discoverable as MCP tools
- [ ] Bidirectional: MCP servers can declare themselves via ASMP

### Slice 8: Docs Site
**Status: NOT STARTED**

- [ ] asmp.io domain registered
- [ ] Mintlify-powered docs (same stack as modelcontextprotocol.io)
- [ ] MDX content in GitHub repo
- [ ] Getting started, spec reference, examples, community

### Slice 9: Community & Adoption
**Status: NOT STARTED**

- [ ] 3-5 external projects using ASMP
- [ ] Community manifests in registry repo
- [ ] Steering committee formed
- [ ] Conference talk or blog post

### Slice 10: Foundation Governance
**Status: NOT STARTED**

- [ ] Submit to Linux Foundation / Agentic AI Foundation
- [ ] "Agent Service Manifest Protocol, a Series of LF Projects, LLC"
- [ ] Trademark protection
- [ ] Neutral governance

---

## Org Repos

| Repo | Purpose | Status |
|------|---------|--------|
| `agent-service-manifest-protocol` | Spec, JSON Schema, docs | Active |
| `reference` | Reference registration server (Python) | Planned |
| `sdk-python` | Python SDK | Planned |
| `sdk-typescript` | TypeScript SDK | Planned |
| `registry` | Community manifests | Planned |
| `examples` | Example .asmp.yaml files | Planned |

## Domain

- `asmp.io` — to be registered for docs site (Mintlify)

## License

Apache 2.0

## Governance

See [GOVERNANCE.md](GOVERNANCE.md) for the three-stage roadmap to neutral foundation governance.
