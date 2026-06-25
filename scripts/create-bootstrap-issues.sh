#!/usr/bin/env bash
# Create BOOTSTRAP-50 milestones and issues via gh CLI
set -euo pipefail

REPO="agent-service-manifest-protocol/agent-service-manifest-protocol"
PLAN_URL="https://github.com/${REPO}/blob/main/planning/BOOTSTRAP-50.md"

if [[ "${SKIP_SETUP:-}" != "1" ]]; then
echo "Creating labels..."
for i in 1 2 3 4 5 6 7; do
  gh label create "tier-${i}" --repo "$REPO" --color "1D76DB" --description "Bootstrap tier ${i}" --force 2>/dev/null || true
done
for sz in S M L; do
  gh label create "size-${sz}" --repo "$REPO" --color "C5DEF5" --description "Estimate: ${sz}" --force 2>/dev/null || true
done
gh label create "bootstrap" --repo "$REPO" --color "FEF2C0" --description "BOOTSTRAP-50 plan item" --force 2>/dev/null || true
gh label create "external-repo" --repo "$REPO" --color "D93F0B" --description "Work primarily outside spec repo" --force 2>/dev/null || true

create_milestone() {
  local title="$1"
  local desc="$2"
  local num
  num=$(gh api "repos/${REPO}/milestones" -f title="$title" -f description="$desc" --jq '.number')
  echo "Milestone #${num}: ${title}"
}

echo "Creating milestones..."
create_milestone "Tier 1: Ambient discovery" "Items 1-8. Gate: service_find works from 3+ repos without per-repo MCP."
create_milestone "Tier 2: One registry" "Items 9-16. Gate: Macdash reads ~/.asmp/ only; drift check green."
create_milestone "Tier 3: Public reference" "Items 17-24. Gate: pip install asmp-registry && serve on fresh machine."
create_milestone "Tier 4: Schema & validation" "Items 25-30. Gate: 46/46 example manifests pass schema tests."
create_milestone "Tier 5: Provisioning" "Items 31-36. Gate: POST manifest → plist → healthy without hand edit."
create_milestone "Tier 6: Adoption UX" "Items 37-42. Gate: Demo GIF recorded; blog draft reviewed."
create_milestone "Tier 7: Expand surface" "Items 43-50. Gate: External adopter runs ASMP without Daniel."
fi

create_issue() {
  local num="$1"
  local tier="$2"
  local title="$3"
  local size="$4"
  local deps="$5"
  local repos="$6"
  local tasks="$7"
  local deliverable="$8"
  local success="$9"
  local extra_labels="${10:-}"

  local milestone="Tier ${tier}:"
  case $tier in
    1) milestone="Tier 1: Ambient discovery" ;;
    2) milestone="Tier 2: One registry" ;;
    3) milestone="Tier 3: Public reference" ;;
    4) milestone="Tier 4: Schema & validation" ;;
    5) milestone="Tier 5: Provisioning" ;;
    6) milestone="Tier 6: Adoption UX" ;;
    7) milestone="Tier 7: Expand surface" ;;
  esac

  local labels="bootstrap,tier-${tier},size-${size}${extra_labels:+,${extra_labels}}"

  local body
  body=$(cat <<EOF
## Bootstrap item ${num}

📋 Plan: [BOOTSTRAP-50.md item ${num}](${PLAN_URL})

| Field | Value |
|-------|-------|
| **Tier** | ${tier} |
| **Dependencies** | ${deps} |
| **Size** | ${size} |
| **Repos** | ${repos} |

### Tasks
${tasks}

### Deliverable
${deliverable}

### Success criteria
${success}
EOF
)

  if gh issue list --repo "$REPO" --search "repo:${REPO} \"[${num}]\" in:title" --json number --jq 'length' 2>/dev/null | grep -qv '^0$'; then
    echo "Skip existing: [${num}] ${title}"
    return 0
  fi
  gh issue create --repo "$REPO" \
    --title "[${num}] ${title}" \
    --body "$body" \
    --milestone "$milestone" \
    --label "$labels"
  sleep 0.5
}

echo "Creating issues..."

create_issue 1 1 "Audit MCP config sprawl" S "None" \
  "\`~/repos-personal/*/.mcp.json\`, \`~/.cursor/mcp.json\`" \
  "- Find all \`.mcp.json\` under repos-personal and repos-aic\n- Mark which include director-daemon / registry MCP\n- Produce matrix: repo × MCP servers × has service_find" \
  "\`planning/artifacts/mcp-audit.md\`" \
  "Complete list; count of repos with vs without registry MCP"

create_issue 2 1 "Global Cursor MCP config → registry" S "Item 1" \
  "\`~/.cursor/mcp.json\`" \
  "- Add asmp-registry entry pointing to aic-director-daemon MCP server\n- Match args from working repos (e.g. reeves-cockpit)\n- Verify MCP connects in Cursor" \
  "Updated \`~/.cursor/mcp.json\`" \
  "Cursor MCP panel shows registry connected; service_list callable"

create_issue 3 1 "Global Claude Code MCP config" S "Item 2" \
  "Claude Code global config" \
  "- Locate Claude Code global MCP config on this machine\n- Add same registry server as item 2\n- Document config path" \
  "Global Claude MCP config + doc note" \
  "Claude sessions inherit registry without per-repo config"

create_issue 4 1 "Litmus test from software-engineer cockpit" S "Items 2, 3" \
  "\`aic-software-engineer-cockpit\`" \
  "- Open cockpit with only global MCP\n- Run service_find(capability=email.ingest)\n- Record result in planning/artifacts/litmus-test.md" \
  "Litmus test log" \
  "Returns email or director-daemon with endpoint and health"

create_issue 5 1 "Registry always on boot" S "None" \
  "\`aic-director-daemon\`, LaunchAgents" \
  "- Confirm :7700 registry relationship to director-daemon\n- Ensure LaunchAgent loads on login\n- Add health check to doctor script" \
  "LaunchAgent or documented dependency chain" \
  "After reboot, :7700/health returns 200 within 60s of login"

create_issue 6 1 "Session-start playbook — query registry" S "Item 4" \
  "\`aic-software-engineer-cockpit/.claude/skills\`" \
  "- Optional pre-flight registry query\n- CLAUDE.md rule: query registry before guessing ports\n- Keep takeoff lightweight" \
  "Skill or CLAUDE.md patch" \
  "Takeoff briefing can include N services registered, M healthy"

create_issue 7 1 "Docs: host bootstrap path" S "Item 2" \
  "\`agentservicemanifest.io\`" \
  "- Add guides/ambient-discovery.mdx\n- Link from index + quickstart" \
  "Docs page in agentservicemanifest.io repo" \
  "Page describes Cursor + Claude paths on macOS"

create_issue 8 1 "Cap analog research at top 7" M "None" \
  "\`research\`" \
  "- Create 007-analog-study with 7 findings only\n- Format: steal / skip / ASMP slice\n- Defer deep competitive landscape" \
  "7 finding files + README" \
  "Each finding maps to actionable slice; no open-ended research"

create_issue 9 2 "Inventory all registry consumers" S "Tier 1 gate" \
  "macdash, reeves-daemon, reeves-3, Caddy, infra" \
  "- Grep for apps.yaml, services.yaml, .asmp\n- Map consumer → file → count → owner repo" \
  "\`planning/artifacts/registry-consumers.md\`" \
  "Every read path documented; drift numbers reconciled"

create_issue 10 2 "Macdash reads ~/.asmp/services/ only" M "Item 9" \
  "\`daniel-macdash\`" \
  "- Add load_from_asmp() in registry.py\n- Map display, health, endpoints, capabilities to models\n- Feature flag ASMP_REGISTRY=1" \
  "PR to daniel-macdash" \
  "Dashboard health view works from ASMP source" \
  "external-repo"

create_issue 11 2 "Remove macdash services.yaml fallback" S "Item 10" \
  "\`daniel-macdash\`" \
  "- Delete or archive config/services.yaml\n- Remove fallback code path" \
  "macdash PR merged" \
  "App fails loudly if ~/.asmp/services/ empty" \
  "external-repo"

create_issue 12 2 "Backfill manifests for macdash gaps" M "Item 10" \
  "\`~/.asmp/services/\`" \
  "- Diff macdash services vs ASMP manifests\n- Write or deprecate missing entries\n- Populate display, health, endpoints" \
  "Updated .asmp.yaml files" \
  "Zero services macdash expects but ASMP lacks"

create_issue 13 2 "Migrate Reeves apps.yaml → ASMP" M "Item 11" \
  "\`~/.config/reeves/apps.yaml\`, \`~/.asmp/\`" \
  "- Script: apps.yaml → ASMP manifests\n- Preserve launchd labels, ports, repos" \
  "Migration script + 13 manifests confirmed" \
  "Every apps.yaml entry has matching .asmp.yaml"

create_issue 14 2 "Reconcile 33-service delta" M "Item 13" \
  "macdash, ~/.asmp/, reeves" \
  "- List 33 dashboard-only services\n- Tag state: planned | running | deprecated" \
  "\`planning/artifacts/service-reconciliation.md\`" \
  "Every service has explicit lifecycle state"

create_issue 15 2 "Drift check script" S "Items 11, 13" \
  "spec repo or reference scripts/" \
  "- Compare apps.yaml, services.yaml, ~/.asmp counts\n- Exit 1 on divergence\n- Optional daily LaunchAgent" \
  "asmp-drift-check script + docs" \
  "Script passes after migration complete"

create_issue 16 2 "Caddy routes from ASMP endpoints" M "Item 12" \
  "Caddy config / asmp-infra" \
  "- Generate routes from visibility != loopback\n- Dry-run first, manual apply" \
  "asmp-caddy-gen script" \
  "New service with display.url gets route proposal"

create_issue 17 3 "Create reference org repo" S "Tier 2 gate" \
  "\`agent-service-manifest-protocol/reference\` (new)" \
  "- gh repo create\n- Apache 2.0, README, pyproject.toml, CI stub" \
  "Empty installable package" \
  "pip install -e . works"

create_issue 18 3 "Extract registry/engine.py" M "Item 17" \
  "\`aic-director-daemon\`, \`reference\`" \
  "- Copy engine with minimal deps\n- Configurable ASMP_DIR env\n- Unit tests" \
  "asmp_registry/engine.py + tests" \
  "Engine loads 46 manifests in CI fixture" \
  "external-repo"

create_issue 19 3 "Extract registry/server.py" M "Item 18" \
  "\`reference\`" \
  "- HTTP server module, PORT env\n- All v0.1 API endpoints\n- Integration test POST + GET" \
  "asmp_registry/server.py" \
  "curl localhost:7700/services works after serve"

create_issue 20 3 "Extract MCP tools" M "Item 18" \
  "\`reference\`, \`aic-director-daemon/mcp_server\`" \
  "- Extract service_find, service_list, service_health, service_register\n- Entry point: asmp-registry-mcp" \
  "MCP server module" \
  "Cursor connects to extracted MCP"

create_issue 21 3 "pip install asmp-registry + CLI serve" S "Items 19, 20" \
  "\`reference\`" \
  "- pyproject.toml scripts: serve, mcp\n- Local pip install first" \
  "Working CLI" \
  "pip install -e . && asmp-registry serve → :7700 live"

create_issue 22 3 "Director-daemon imports package" M "Item 21" \
  "\`aic-director-daemon\`" \
  "- Replace local registry/ with asmp-registry dependency\n- Verify production Mac" \
  "director-daemon PR" \
  "No duplicated engine code" \
  "external-repo"

create_issue 23 3 "Update spec repo CONTRIBUTING" S "Item 17" \
  "\`agent-service-manifest-protocol\`" \
  "- Link reference repo\n- Issue templates" \
  "CONTRIBUTING.md PR" \
  "Links resolve; no planned language"

create_issue 24 3 "Update docs quickstart" S "Item 21" \
  "\`agentservicemanifest.io\`" \
  "- Replace coming soon with real install\n- Add troubleshooting" \
  "quickstart.mdx PR" \
  "New user can follow docs verbatim"

create_issue 25 4 "examples org repo — 46 manifests" M "Item 21" \
  "\`examples\` (new), \`~/.asmp/services/\`" \
  "- Copy and sanitize manifests\n- README per example" \
  "Public examples repo" \
  "No secrets or private hostnames leaked"

create_issue 26 4 "Service manifest JSON Schema" M "Item 25" \
  "\`agent-service-manifest-protocol/schema/\`" \
  "- Infer from 46 real files\n- asmp-service-manifest-v0.1.schema.json" \
  "JSON Schema + generation script" \
  ">90% of manifests validate without modification"

create_issue 27 4 "Host profile JSON Schema" S "Item 25" \
  "\`agent-service-manifest-protocol/schema/\`" \
  "- Schema from real host.yaml\n- Document required vs optional" \
  "asmp-host-profile-v0.1.schema.json" \
  "Production host.yaml validates"

create_issue 28 4 "Validate on POST /services" M "Items 26, 27, 19" \
  "\`reference\`" \
  "- jsonschema validation before write\n- 400 with field-level errors" \
  "Server validation middleware" \
  "Invalid manifest rejected with actionable errors"

create_issue 29 4 "asmp validate CLI" S "Items 26, 27" \
  "\`reference\`" \
  "- validate manifest.yaml and --host" \
  "CLI subcommand" \
  "Agents validate before POST"

create_issue 30 4 "Schema tests in CI" S "Items 25-27" \
  "\`examples\`, \`reference\`, spec repo" \
  "- CI: all examples validate\n- Fail PR on schema break" \
  "GitHub Actions workflow" \
  "Green CI on main"

create_issue 31 5 "LaunchAgent plist generation (macOS)" L "Item 28" \
  "\`reference\`" \
  "- Template from run, lifecycle, endpoints\n- launchctl load on approve" \
  "provision.launchd module" \
  "POST manifest → plist exists → service startable"

create_issue 32 5 "requires_approval queue" M "Item 28" \
  "\`reference\`" \
  "- Pending dir ~/.asmp/pending/\n- approve CLI and GET /pending" \
  "Approval workflow" \
  "requires_approval: true queues not publishes"

create_issue 33 5 "Port policy enforcement" S "Item 28" \
  "\`reference\`" \
  "- Port bind test + allowed_ports check" \
  "Policy module" \
  "Cannot register occupied or out-of-policy port"

create_issue 34 5 "Health orchestration" M "Item 18" \
  "\`reference\`" \
  "- Background health checks on interval\n- Expose latency in GET responses" \
  "Health scheduler" \
  "Health updates without manual curl"

create_issue 35 5 "Deregister on shutdown (byebye)" M "Item 19" \
  "\`reference\`" \
  "- lifecycle.stop updates state\n- Document deregister pattern" \
  "Docs + optional supervisor hook" \
  "Stopped service shows stopped or unhealthy in registry"

create_issue 36 5 "systemd unit generation (Linux)" M "Item 31" \
  "\`reference\`" \
  "- Parallel to LaunchAgent for Linux hosts" \
  "provision.systemd module" \
  "Linux VM provisions via same manifest"

create_issue 37 6 "Capability URI spec" M "Item 24" \
  "spec repo ADR" \
  "- ADR: cap:domain.action@host_id resolution\n- Magnet-link analogy" \
  "ADR-001-capability-uri.md" \
  "Agents resolve URIs without full manifest"

create_issue 38 6 "Well-known bootstrap spec" M "Item 24" \
  "spec repo ADR + docs" \
  "- ADR: ~/.asmp/host.yaml primary bootstrap\n- Optional /.well-known/asmp for ring 2" \
  "ADR-002 + docs page" \
  "New agent knows which file to read first"

create_issue 39 6 "MCP bridge first cut" L "Items 20, 28" \
  "\`reference\`" \
  "- Expose provides as MCP tool metadata stubs\n- Docstrings from manifest" \
  "mcp_bridge.py module" \
  "MCP tool list includes capability-named tools from registry"

create_issue 40 6 "Registry web UI at :7700" M "Items 19, 34" \
  "\`reference\`" \
  "- Minimal HTML service browser + health filter\n- GET /ui" \
  "Static UI served by registry" \
  "Human can browse registry without curl"

create_issue 41 6 "60-second demo GIF" S "Items 4, 21, 40" \
  "docs site, README" \
  "- Record register → discover in new session\n- Embed in index.mdx" \
  "GIF + embed" \
  "Marketing asset ready for launch"

create_issue 42 6 "Blog post draft" M "Item 41" \
  "\`research\` or blog" \
  "- Pain-first title\n- Problem → aha → demo → pip install\n- Alex persona" \
  "Draft markdown" \
  "Readable by non-author; homelab persona included"

create_issue 43 7 "Python SDK" M "Items 21, 28" \
  "\`sdk-python\` or reference" \
  "- register(), discover(), health() HTTP client" \
  "pip install asmp client" \
  "10-line script registers and discovers"

create_issue 44 7 "Second host deployment" M "Items 21, 36" \
  "VM / homelab / second Mac" \
  "- Fresh install from docs only\n- Document friction" \
  "Second machine + artifacts/second-host.md" \
  "Install without copying Daniel's ~/.asmp"

create_issue 45 7 "POST /services/{name}/mods implementation" M "Item 28" \
  "\`reference\`" \
  "- Mod attach validation requires ⊆ provides\n- Update mods[] state" \
  "Mod endpoints live" \
  "Compliance mod attaches in test fixture"

create_issue 46 7 "Omni reads ASMP spike" M "Items 11, 21" \
  "\`reeves-omni\` / EidosOmni" \
  "- Spike: indexer lists ASMP services as sources\n- Document Eidos map integration" \
  "Spike doc + optional PR" \
  "Clear answer: Omni consumes ASMP for what exists" \
  "external-repo"

create_issue 47 7 "Analog ADR in spec repo (top 7)" S "Item 8" \
  "spec planning/adrs/" \
  "- Consolidate 007-analog-study into ADR-003" \
  "ADR-003-protocol-analogs.md" \
  "Future debates reference ADR not re-research"

create_issue 48 7 "Mintlify deploy + DNS" S "Item 24" \
  "\`agentservicemanifest.io\`, \`asmp-infra\`" \
  "- Connect Mintlify\n- DNS agentservicemanifest.io" \
  "Live docs site" \
  "https://agentservicemanifest.io loads"

create_issue 49 7 "Knox hooks on register" L "Items 32, 45" \
  "Knox, reference" \
  "- regulated sensitivity forces approval\n- Audit log on register/attach" \
  "Policy integration + minimal hook" \
  "data.sensitivity: regulated cannot auto-publish" \
  "external-repo"

create_issue 50 7 "External adopter + steering committee charter" M "Items 44, 48" \
  "GOVERNANCE.md, outreach" \
  "- Support one external homelab builder\n- Draft 3-person steering charter" \
  "Named adopter + charter" \
  "Second human uses ASMP without Daniel editing manifests"

echo "Done. Issue list:"
gh issue list --repo "$REPO" --limit 60 --json number,title,milestone --jq '.[] | "#\(.number) [\(.milestone.title // "none")] \(.title)"'