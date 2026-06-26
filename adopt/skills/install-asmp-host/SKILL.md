---
name: install-asmp-host
description: >
  Bootstrap ASMP host layout and registry on this machine (~/.asmp/, :7700).
  Use when host.yaml is missing, registry health fails, or install-asmp router
  sends you here first.
---

# Install ASMP host

## Prefer director-daemon (this Mac)

If `com.aicholdings.director-daemon` LaunchAgent exists and `:7700` responds with service counts, the full registry is already running. Only bootstrap if health fails.

```bash
curl -s http://127.0.0.1:7700/health | python3 -m json.tool
launchctl list | rg director-daemon
```

## Bootstrap fallback

```bash
curl -fsSL https://raw.githubusercontent.com/agent-service-manifest-protocol/agent-service-manifest-protocol/main/scripts/bootstrap-asmp.sh | bash
```

Creates `~/.asmp/host.yaml`, `~/.asmp/services/`, installs `~/.asmp/bin/asmp-serve.py`, starts `:7700`.

## Litmus

```bash
curl -s http://127.0.0.1:7700/health
curl -s http://127.0.0.1:7700/services | python3 -c "import sys,json; print(len(json.load(sys.stdin)), 'services')"
```

## Next

Registry alone is not enough. Return to `use-asmp` and run `discover-agent-tools` to wire MCP surfaces.