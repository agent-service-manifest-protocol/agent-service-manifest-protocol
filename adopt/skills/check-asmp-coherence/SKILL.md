---
name: check-asmp-coherence
description: >
  Audit ASMP coherence across host runtime, three repos, live website, and
  adopt layer. Use before ship-asmp, after large edits, or when Daniel asks
  if ASMP is in sync.
---

# Check ASMP coherence

Read-only gate. Fix issues via `sync-asmp-repos`, then re-run.

## Quick gate

```bash
cd ~/repos-personal/agent-service-manifest-protocol
./adopt/scripts/asmp-coherence-check.sh
```

## Manual checks

### Host runtime

```bash
asmp litmus
asmp scan
asmp find --capability asmp.marketing
```

### Local repos clean?

```bash
for r in aic-director-daemon agent-service-manifest-protocol agentservicemanifest.io; do
  echo "=== $r ===" && git -C ~/repos-personal/$r status --short
done
```

### Live site vs local marketing story

Live `/` must show human story, not technical grep demo:

```bash
curl -sL https://asmp.eidosagi.com/ | rg -c "Inbox helper|phone book"
curl -sL https://asmp.eidosagi.com/ | rg -c "inbox-triage|grep -r"
```

Pass: first > 0, second = 0 (or only in "skip" contrast lines).

### Live docs match shipped spec

```bash
curl -sL https://asmp.eidosagi.com/docs/spec/ship-with-software | rg -c "asmp.yaml"
curl -sL https://asmp.eidosagi.com/docs/guides/cli | rg -c "asmp litmus"
```

### Bootstrap raw URLs resolve

```bash
curl -fsSL -o /dev/null -w "%{http_code}\n" \
  https://raw.githubusercontent.com/agent-service-manifest-protocol/agent-service-manifest-protocol/main/scripts/bootstrap-asmp.sh
curl -fsSL -o /dev/null -w "%{http_code}\n" \
  https://raw.githubusercontent.com/agent-service-manifest-protocol/agent-service-manifest-protocol/main/scripts/asmp
```

Both must return `200`.

### API parity (runtime vs bootstrap server)

Endpoints only in full runtime (`aic-director-daemon`):

- `POST /discover/scan`
- `POST /services/announce`
- `POST /reload`

`asmp-serve.py` must implement the same set for bootstrap parity.

## Coherence dimensions

| Dimension | Question |
|-----------|----------|
| **Runtime** | Does `:7700` respond and scan find shipped manifests? |
| **Repos** | Do API, CLI, docs, and skills agree? |
| **Live** | Does `asmp.eidosagi.com` match what git `main` built? |
| **Adopt** | Are INSTALL + RELEASE indexes complete? |
| **Surfaces** | Is `discover-agent-tools` green for P0 tools? |

## On failure

| Failure | Delegate to |
|---------|-------------|
| Litmus fail | `install-asmp-host` |
| API/docs mismatch | `sync-asmp-repos` |
| Live site stale | `deploy-asmp-site` |
| Marketing technical | `polish-asmp-marketing` |
| Docs gaps | `polish-asmp-docs` |

## Litmus

`asmp-coherence-check.sh` exits 0.