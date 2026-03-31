# ASMP — Agent Service Manifest Protocol v0.1

**Status:** Draft
**Author:** Daniel Shanklin
**Date:** 2026-03-31

## What This Is

A three-part standard for AI-native personal infrastructure:

1. **Host Profile** — what this device is and can do
2. **Service Manifest** — what each service is, written by the agent that built it
3. **Registration Protocol** — how agents register, discover, and extend services

Designed to compose with MCP (tool discovery) and A2A (agent communication) at the host layer.

## Positioning

| Protocol | Layer | Question |
|----------|-------|----------|
| MCP | Tool | "What tools can I use?" |
| A2A / ACP | Agent | "What agents can I talk to?" |
| **ASMP** | **Host** | **"What services run here and how do I register new ones?"** |

ASMP does not replace systemd, launchd, Docker Compose, or Kubernetes. It is a **declaration layer** they can all consume. The host runtime maps ASMP manifests into its native format (plists, units, compose files).

## Part 1: Host Profile

A JSON/YAML document at a well-known path that describes the device.

**Location:** `~/.asmp/host.yaml` (personal) or `/etc/hmp/host.yaml` (system)

```yaml
asmp: "0.1"
kind: host

host_id: "daniels-macbook-2026"
device_class: personal_computer

os:
  name: macOS
  version: "15.3.1"
  arch: arm64

hardware:
  cores: 12
  ram_gb: 36
  gpu: "Apple M4 Pro"

capabilities:
  - files.local
  - email.local
  - calendar.local
  - networking
  - containers
  - gpu.inference

registry:
  path: ~/.asmp/services/
  api: http://127.0.0.1:7700

policy:
  agent_can_register: true
  requires_approval: true
  max_services: 100
  allowed_ports: "7000-9999"
  data_sensitivity_default: medium

observability:
  logs: ~/.local/log/
  metrics: http://127.0.0.1:9090
```

## Part 2: Service Manifest

A YAML file per service, written by the agent that built it. Lives in `~/.asmp/services/`.

**File:** `~/.asmp/services/email-daemon.asmp.yaml`

```yaml
asmp: "0.1"
kind: service

# ── Identity ────────────────────────────────────────────────
name: email-daemon
description: "Email intelligence — ingest, analyze, decide, verify"
version: "1.0.0"
created_by: claude-code
owner: daniel
created_at: "2026-03-31T03:00:00Z"

# ── Runtime ─────────────────────────────────────────────────
run:
  command: python3
  args: [main.py]
  working_dir: ~/repos-personal/aic-director-daemon
  env:
    PYTHONPATH: .
  restart: always
  depends_on:
    - name: apple-mail
      kind: soft

lifecycle:
  start: "launchctl load ~/Library/LaunchAgents/com.aicholdings.director-daemon.plist"
  stop: "launchctl unload ~/Library/LaunchAgents/com.aicholdings.director-daemon.plist"
  reload: "launchctl kickstart -k gui/501/com.aicholdings.director-daemon"

state: running

# ── Network ─────────────────────────────────────────────────
endpoints:
  - protocol: http
    host: 127.0.0.1
    port: 7400
    path: /
    visibility: loopback

health:
  method: http
  target: http://127.0.0.1:7400/health
  interval: 30s
  timeout: 5s

# ── Capabilities ────────────────────────────────────────────
capabilities:
  provides:
    - email.ingest
    - email.classify
    - email.decide
    - email.search
    - email.read
  requires:
    - apple-mail.envelope-index:read
    - claude-p:execute
    - filesystem:read:~/Library/Mail

data:
  sensitivity: medium
  stores:
    - path: ~/repos-personal/aic-director-of-ai-cockpit/cockpit-director-of-ai/data/email/email-brain.db
      type: sqlite
      contains: [email_metadata, email_bodies, ai_analysis, decisions]

# ── Mods ────────────────────────────────────────────────────
mods:
  - name: compliance-scanner
    description: "Scans classified emails for PII, HIPAA/SOX violations"
    agent: security-mod
    attaches_to: [email.classify]
    capabilities:
      provides: [compliance.pii_detect, compliance.audit_log]
      requires: [email.read]
    state: available  # available, attached, disabled

  - name: crm-sync
    description: "Detects new contacts, creates records in relationships service"
    agent: relationship-mod
    attaches_to: [email.ingest]
    capabilities:
      provides: [contact.create, relationship.track]
      requires: [email.read, relationships.write]
    state: available

# ── Observability ───────────────────────────────────────────
logs:
  path: ~/.director-daemon/supervisor.log
  format: text

metrics:
  table: email-brain.db/metrics

repo: ~/repos-personal/aic-director-daemon

# ── Display (for dashboards) ───────────────────────────────
display:
  icon: "\U0001F3AF"
  section: tools
  critical: true
  url: http://localhost:7400/status
```

## Part 3: Registration Protocol

A localhost HTTP API that agents use to register, discover, and manage services.

**Default endpoint:** `http://127.0.0.1:7700` (configurable in host profile)

### Endpoints

```
POST   /services              Register a new service (submit manifest)
GET    /services              List all registered services
GET    /services/{name}       Get a specific service manifest + runtime state
PATCH  /services/{name}       Update a manifest
DELETE /services/{name}       Deregister a service

GET    /host                  Get the host profile
GET    /capabilities          Query services by capability
POST   /services/{name}/mods  Attach a mod to a service
DELETE /services/{name}/mods/{mod}  Detach a mod
```

### Registration flow

```
1. Agent builds a service (writes code, tests it)
2. Agent writes a .asmp.yaml manifest
3. Agent POSTs manifest to /services
4. Host validates:
   - Schema valid?
   - Port available?
   - Policy allows it? (agent_can_register, requires_approval)
   - Data sensitivity acceptable?
5. If requires_approval: queue for human review
6. If approved: host provisions
   - Generates LaunchAgent plist (macOS) or systemd unit (Linux)
   - Adds Caddy/nginx route if endpoints have visibility != loopback
   - Creates log directory
   - Starts the service
7. Service is now discoverable via GET /services
8. Other agents can query GET /capabilities to find it
9. Mods can attach via POST /services/{name}/mods
```

### Mod attachment flow

```
1. Mod agent queries GET /capabilities?provides=email.classify
2. Finds email-daemon
3. POSTs mod manifest to /services/email-daemon/mods
4. Host validates:
   - Mod's requires are satisfied by the service's provides?
   - Policy allows this mod?
5. If approved: mod is attached
   - Mod can now read from the service's API
   - Mod appears in the service's manifest under mods[]
6. Service doesn't change. Mod observes and extends.
```

## Design Principles

1. **Agent-first, human-audited.** Agents write manifests. Humans approve. The format is optimized for AI generation and human review.

2. **Host-centric.** Anchored to a device. Not a cloud, not a cluster, not a network. Your Mac. Your homelab. Your machine.

3. **Runtime-neutral.** Maps to launchd, systemd, Docker, k8s, supervisord, or a custom Python supervisor. ASMP is the declaration. The runtime is the execution.

4. **Composable with MCP and A2A.** ASMP operates at a different layer. A service registered via ASMP can expose MCP tools. An agent discovered via A2A can register services via ASMP. They compose, not compete.

5. **Small surface area.** Enough fields to automate everything. Not so many that agents hallucinate invalid manifests. Fixed enums, tight schemas, predictable keys.

6. **Mods are first-class.** Services can be extended by agents that didn't build them. The mod system is in the spec, not an afterthought. This is what makes ASMP different from every other service declaration format.

## What This Replaces (in the Reeves ecosystem)

| Before | After |
|--------|-------|
| `~/.config/reeves/apps.yaml` | `~/.asmp/services/*.asmp.yaml` |
| `daniel-macdash/config/services.yaml` | Dashboard reads from `~/.asmp/services/` |
| Manual LaunchAgent plist creation | Generated from ASMP manifest on registration |
| Manual Caddyfile edits | Generated from ASMP endpoint declarations |
| Two registries that drift | One directory of manifests, many consumers |

## Next Steps

1. **JSON Schema** — formalize the manifest schema so agents can validate before submitting
2. **Reference implementation** — the registration API server (Python, runs on localhost)
3. **Reeves migration** — convert all 35+ services to ASMP manifests
4. **Eidos package** — extract as open-source, framework-agnostic package
5. **MCP bridge** — auto-generate MCP tool manifests from ASMP service capabilities
