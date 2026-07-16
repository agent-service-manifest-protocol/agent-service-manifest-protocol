# Changelog

Durable, cross-system record of changes to ASMP. Every machine bootstraps
`scripts/asmp-serve.py` + `scripts/asmp` from `main`, so this file is the
shared history of what each machine is running. Newest first.

Two implementation lines are tracked here:

- **`X.Y.Z`** — the Python reference implementation in this repo
  (`scripts/` = registry server + bootstrap, `bin/` = CLI).
- **`X.Y.Z-go`** — the native Go rewrite of the agent hot path, developed
  on the fleet. Its source is not yet vendored into this repo.

## [0.4.1] — 2026-07-16 — Correct the 0.4.0 changelog

No code change. `v0.4.0` was tagged with a changelog that described features
this repo does not contain.

One of the `[Unreleased]` tranches rolled into 0.4.0 was describing the **Go
engine**, not the Python reference implementation: ranked `GET /services?q=`,
`GET /context`, honest `/health` (probe state + cache stats), `asmp route`, and
`asmp context`. None of those exist in any Python server here — `health_probe`
and `/context` are absent from `scripts/asmp-serve.py`, `bin/asmp-serve.py`,
and the installed copy alike. They were filed under a Python release purely
because they sat beneath an `[Unreleased]` heading.

The 0.4.0 entry below is now restricted to claims verified present in the
tagged code, with the Go-only work named as such under "Not in this release".
`v0.4.0` is left standing rather than re-tagged: the false entry is part of
this repo's history, and superseding it is more honest than erasing it.

**Lesson:** a changelog heading is not evidence. Verify each claim against the
artifact before tagging — the check is `grep` for the symbol, not "the tests
pass" or "the CLI prints the right version". Neither of those can detect a
changelog describing a different codebase.

## [0.4.0] — 2026-07-16 — Host-aware registry, conduit federation, warm cache

First tagged release of the **Python reference implementation** since `0.2.0`.
Rolls up the host-awareness, federation, and registry-cache work that had been
sitting under stacked `[Unreleased]` headings. Numbered `0.4.0` rather than
`0.3.0` to avoid colliding with the concurrent `0.3.x-go` line.

Every bullet below was verified present in this tag's `scripts/asmp-serve.py`
and `scripts/asmp`. Work that exists only in the Go engine is listed under the
`-go` entries, not here.

### Added — host-aware registry and cross-system discovery
- **Host discovery.** `GET /hosts`, `GET /hosts/history`, and `asmp hosts` /
  `asmp host-history` report every machine ASMP knows about: the local host,
  hosts that federated services in, and machines merely *declared* reachable in
  a service's `infra.machines`. `host_aliases` collapses alternate names for
  one box.
- **Cross-system federation.** `POST /federate` plus a background loop pull peer
  registries over SSH (peers are localhost-bound, so SSH rather than exposing
  `:7700`). Configured under `federation.peers` in `host.yaml`.
- **Conduit as federation transport.** A peer may name a conduit `machine_id`
  (`conduit: mac-mini-01`) instead of a raw `ssh:` target; the hub reaches it via
  conduit, delegating fleet reach/auth to the layer that owns it rather than
  hardcoding SSH endpoints. `federation.conduit_bin` points at the conduit CLI;
  raw `ssh:` peers still work.
- **Composite `name@host` keying.** Federated services are namespaced by host so
  they never clobber a local service of the same name (`conduit` exists on every
  machine). Local services keep their bare name.
- **Durable host history.** Each federation cycle appends the host roster to
  `~/.asmp/host-history.jsonl`.
- **`asmp register` / `asmp announce`** for manifest registration.

### Fixed — registry latency
- **In-process registry cache** with fingerprint invalidation (count + mtime +
  size). Reloading ~90 YAML files was ~1.8s per request; warm hits are ms.
- **`ThreadingHTTPServer`** so concurrent agent calls overlap instead of
  serializing behind each other.
- **Listen backlog 128** (class-level `request_queue_size`); the default of 5
  reset connections under agent fan-out.

### Changed
- `GET /services?host=<h>` filters by host; entries now carry a `host` field.
- `load_services` / `write_manifest` / announce key by `name@host`.

### Topology
- Hub-and-spoke: the **mac-mini** is the hub (holds `federation.peers` and the
  full fleet view); the laptop and cyprus are spokes. Full mesh is a later step.

### Not in this release
Ranked `GET /services?q=`, `GET /context`, honest `/health` (probe state + cache
stats), and `asmp route` / `asmp context` are **Go-engine features** — see the
`-go` entries. They are not present in the Python reference implementation and
were previously mis-filed against it.


## [0.3.2-go] — Federation, models, scan, MCP

- **Federation**: correct `conduit run --target X -- cmd`; expanded PATH +
  `CONDUIT_PYTHON` for LaunchAgent; stdout-only JSON with first-`[` extract;
  CLI `asmp federate` runs **in-process** (launchd-spawned server was SIGKILLing
  conduit children).
- **Models**: `/models`, `/models/recommend`, `/models/health`, `/models/verify`
  + `asmp models …` in Go.
- **Scan**: `POST /discover/scan` + `asmp scan` (in-process).
- **MCP**: `asmp-mcp.py` uses Go CLI; compact session context; tools for
  context/hosts/todos; route via Go ranker. Discovery todo `asmp-mcp-tool`
  marked resolved (enable MCP in client still required — Grok has `mcps=false`).
- LaunchAgent PATH/HOME for serve + conduit children.


## [0.3.1-go] — Hardening pass

- Fix compact cards (nested Manifest maps broke provides/commands).
- Rank thresholds + no positive_example blob pollution.
- API: /hosts, /hosts/history, POST register/announce/federate.
- CLI: hosts, host-history, register, announce, todo, todos, federate.
- Federation loop with 12s peer timeouts + batch cache invalidate.


## [0.3.0-go] — Native Go registry + CLI

- **Go rewrite** of the agent hot path: `asmp serve`, `health`, `find`, `get`,
  `list`, `caps`, `context`, `route`, `reload`, `host`, `version`.
- Source: `~/.asmp/go/` — single binary `~/.asmp/bin/asmp`.
- Python CLI preserved as `~/.asmp/bin/asmp-py` for ambient/oracle/models/doctor/sync;
  unknown subcommands fall through automatically.
- LaunchAgent `io.agentservicemanifest.registry` now runs `asmp serve` (Go).
- Health JSON includes `"engine":"go"`. Warm HTTP health typically **&lt;5–50ms**;
  CLI process start is milliseconds vs multi-second Python.
