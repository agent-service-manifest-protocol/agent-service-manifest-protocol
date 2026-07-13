# Changelog

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


Durable, cross-system record of changes to the ASMP reference implementation
(`scripts/asmp-serve.py` + `scripts/asmp`). Every machine bootstraps these
files from `main`, so this file is the shared history of what each machine is
running. Newest first.

## [Unreleased] — Agent-speed registry (cache, rank, context)

Root-cause fixes after agents spent multi-seconds per `health`/`find` and got
full catalog dumps for free-text queries.

### Fixed (latency)
- **In-process registry cache** with fingerprint invalidation (count + mtime +
  size). Reloading ~90 YAML files was ~1.8s per request; warm hits are ms.
- **Threaded server** (`ThreadingHTTPServer`) so concurrent agent calls do not
  serialize behind each other.
- **Compact JSON** responses (no `indent=2`) — smaller payloads.
- **CLI hot path** no longer runs `git fetch` / network update checks on
  `health`/`find`/`get`/`list`/`caps`/`context`/`route`/`ambient`.

### Fixed (discovery quality)
- **`GET /services?q=` actually filters and ranks** (was ignored → 93-service
  dumps). Default `limit=10` for free-text find; `compact=true` for cards.
- **`asmp find --query`** passes compact+limit; client-side rank fallback if an
  older server still returns the full catalog. `--all` / `--limit` supported.
- **`GET /context`** + **`asmp context --prompt`** for compact agent bootstrap.
- **`asmp route --query/--capability`** CLI parity with MCP `asmp_route`.
- **Honest `/health`**: reports `local`/`federated`, `health_probe: not_run`,
  cache hit stats — no longer pretends `healthy: 0` is a real probe result.
- **Ambient triggers** expanded for finance/dally/hermes/tally/plaid/tokut.

### Registered
- **`dally`** — local Plaid/sync daemon surface (`reeves3.dally.cli` + sqlite).
- **`hermes`** — session store + `hermes sessions` / resume commands.
- **`reeves-tally`** aliases/examples for finance routing.

## [Unreleased] — Federate via conduit

- **Conduit as federation transport.** A peer may name a conduit `machine_id`
  (`conduit: mac-mini-01`) instead of a raw `ssh:` target. The hub then reaches
  it via `conduit run --target <id>` — delegating fleet reach/auth (user,
  endpoint, host-key handling) to conduit, the layer that owns it, instead of
  hardcoding SSH endpoints in `host.yaml`. `federation.conduit_bin` points at
  the conduit CLI; raw `ssh:` peers still work.

## [Unreleased] — Host-aware registry + cross-system discovery

The bootstrap registry was single-host: every service was implicitly local,
keyed by bare name, with no notion of other machines. This makes ASMP
fleet-aware while keeping the per-request, file-backed design.

### Added
- **Host discovery.** `GET /hosts` and `asmp hosts` report every machine ASMP
  knows about — the local host, hosts that have federated services in, and
  machines merely *declared* reachable in a service's `infra.machines`
  (e.g. conduit). `host_aliases` collapses alternate names for one box.
- **Cross-system federation.** `POST /federate` and a background loop pull peer
  registries over SSH (peers are localhost-bound, so SSH rather than exposing
  `:7700`). Configured in `host.yaml`:
  ```yaml
  federation:
    peers:
      - { host: daniels-mac-mini, ssh: mac-mini-01 }
    host_aliases: { mac-mini-01: daniels-mac-mini }
  ```
- **Composite `name@host` keying.** Federated services are namespaced by host
  so they never clobber a local service of the same name (`conduit` exists on
  every machine). Local services keep their bare name.
- **Durable host history.** Each federation cycle appends the host roster to
  `~/.asmp/host-history.jsonl`; read via `GET /hosts/history?host=&limit=` and
  `asmp host-history`.

### Changed
- `GET /services?host=<h>` filters by host; entries now carry a `host` field.
- `load_services` / `write_manifest` / announce key by `name@host`.

### Topology
- Hub-and-spoke: the **mac-mini** is the hub (holds `federation.peers` and the
  full fleet view); the laptop and cyprus are spokes. Full mesh is a later step
  (add `peers` to each `host.yaml`).
