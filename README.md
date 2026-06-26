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

## Lean core vs adoption layer

| Layer | Location | What it is |
|-------|----------|------------|
| **Lean spec** | This README + [agentservicemanifest.io](https://asmp.eidosagi.com/docs) | Host profile, service manifest, registration API |
| **Adoption** | `adopt/` in this repo | Skills, agent-tool catalog, litmus scripts — not part of the protocol |

Software authors ship `asmp.yaml` at repo root. The host registry scans configured paths and syncs into `~/.asmp/services/`. See [ship with software](https://asmp.eidosagi.com/docs/spec/ship-with-software).

The adoption layer also includes **ASMP Ambient**, a tiny lifecycle-context shim
for agent hosts. Ambient reminds agents to ask the local ASMP registry before
guessing tools, ports, repos, or service owners. See
[`adopt/docs/asmp-ambient.md`](adopt/docs/asmp-ambient.md).

The adoption/product layer now also includes **Eidos Oracle**, a deliberative
mission-contract layer that uses ASMP registry context when deterministic
routing is ambiguous, cross-role, low-confidence, or high-stakes. Oracle is not
the lean ASMP protocol core; it is the Eidos product that interprets what ASMP
ambient and service manifests imply for answering a question well. See
[`adopt/docs/eidos-oracle.md`](adopt/docs/eidos-oracle.md).

## Part 2: Service Manifest

A YAML file per service. **Ships with the code** (`asmp.yaml` at repo root). The host index lives in `~/.asmp/services/`.

**Source:** `~/repos/my-service/asmp.yaml`  
**Index:** `~/.asmp/services/email-daemon.asmp.yaml`

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
  # Optional routing semantics for registries that answer natural-language
  # questions such as "what should handle this job?"
  owns:
    - email.workflow.intelligence
    - email.question.answering
  supports:
    - crm.contact.create
    - compliance.pii.review
  aliases:
    - email brain
    - inbox intelligence
    - mail questions
  anti_routes:
    - calendar.schedule
    - filesystem.backup
  requires:
    - apple-mail.envelope-index:read
    - claude-p:execute
    - filesystem:read:~/Library/Mail

positive_examples:
  - "answer a question from recent email"
  - "classify inbound mail"
  - "find the thread about a customer"

negative_examples:
  - query: "schedule a meeting from this email"
    handoff: calendar-agent
  - query: "back up the Mail directory"
    handoff: backup-daemon

when_not_to_use:
  - "Do not use for calendar writes; hand off to the calendar service."
  - "Do not use for raw filesystem backups."

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
POST   /services/announce     Handshake register (returns ack)
POST   /discover/scan         Scan shipped asmp.yaml files into index
POST   /reload                Re-read index from disk
GET    /services              List all registered services
GET    /services/{name}       Get a specific service manifest + runtime state
PATCH  /services/{name}       Update a manifest
DELETE /services/{name}       Deregister a service

GET    /host                  Get the host profile
GET    /capabilities          Query services by capability
POST   /services/{name}/mods  Attach a mod to a service
DELETE /services/{name}/mods/{mod}  Detach a mod
```

### Natural-language discovery (adoption layer)

The lean ASMP core is service declaration and capability discovery. Hosts may
also expose a natural-language routing endpoint for agents:

```text
GET /ask?q=<plain-language-question>
```

This endpoint should not replace the manifest. It should search registered
manifests, apply local routing policy, and return an explainable owner:

```json
{
  "query": "ship data to Supabase",
  "owner": "greenmark-data-shipper",
  "confidence": "high",
  "boundary_decision": {
    "method": "boundary-policy-v0",
    "margin": 0.18,
    "runner_up": {"service": "cerebro-shipr", "score": 0.41},
    "rule_hits": [
      {
        "boundary": "application release vs data publication",
        "hit_counts": {"greenmark-data-shipper": 2}
      }
    ]
  },
  "results": [
    {"service": "greenmark-data-shipper", "score": 0.59},
    {"service": "cerebro-shipr", "score": 0.41}
  ]
}
```

Recommended response fields:

- `owner`: the selected service, or `null` if the registry abstains.
- `confidence`: `high`, `medium`, `low`, or `none`.
- `boundary_decision`: how local policy resolved close candidates.
- `results`: ranked candidates with scores and evidence.
- `alternates`: plausible handoffs when the owner is uncertain.

Generated explanations are not proof. A registry should expose retrieval
evidence, rule hits, and confidence so another agent can challenge or audit the
decision.

## Policy and decision boundaries

ASMP manifests describe services. They should not try to encode all local
judgment into every service file. When two services are easy to confuse, use an
external policy file owned by the host or organization:

```yaml
asmp_policy: "0.1"
name: routing-policy
defaults:
  boundary_win_bonus: 0.12
  boundary_margin: 0.04
  high_confidence_margin: 0.08
boundaries:
  - name: application release vs data publication
    services: [app-shipper, data-shipper]
    phrases:
      app-shipper:
        - deploy app
        - production release
      data-shipper:
        - publish data
        - publication batch
        - warehouse parity
```

Policy files are intentionally outside the lean manifest. This keeps ASMP
portable while still allowing a host to learn local decision boundaries over
time.

Practical routing model:

1. Search manifests with keyword, lexical, semantic, or RRF-style retrieval.
2. Use `owns`, `supports`, `aliases`, examples, and `anti_routes` as evidence.
3. Apply local boundary policy when top candidates are close.
4. Return owner, confidence, runner-up, and rule hits.
5. Add human corrections to policy or service examples, not to hidden prompts.

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

## Adoption layer (`adopt/`)

Optional tooling for getting ASMP wired on a machine:

| Path | Purpose |
|------|---------|
| `adopt/skills/use-asmp/` | Router skill — host + release delegation |
| `adopt/skills/use-asmp/INSTALL-INDEX.md` | Host adoption phone book |
| `adopt/RELEASE-INDEX.md` | Release phone book (ship, deploy, docs, marketing) |
| `adopt/catalog/agent-tools.yaml` | Living catalog of major AI coding tools |
| `adopt/scripts/asmp-litmus.sh` | Host gate: health, capabilities, scan |
| `adopt/scripts/asmp-coherence-check.sh` | Release gate: repos, live site, API parity |
| `adopt/scripts/discover-agent-tools.sh` | Refresh agent-tool catalog |

Run gates:

```bash
./adopt/scripts/asmp-litmus.sh           # host
./adopt/scripts/asmp-coherence-check.sh   # release
```

## Next Steps

1. **JSON Schema** — formalize the manifest schema so agents can validate before submitting
2. **Reference implementation** — registration API + scan loop (live in `aic-director-daemon`)
3. **Reeves migration** — convert all 35+ services to shipped `asmp.yaml`
4. **Eidos package** — extract as open-source, framework-agnostic package
5. **MCP bridge** — auto-generate MCP tool manifests from ASMP service capabilities
