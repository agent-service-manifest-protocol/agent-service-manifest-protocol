# Changelog

Durable, cross-system record of changes to the ASMP reference implementation
(`scripts/asmp-serve.py` + `scripts/asmp`). Every machine bootstraps these
files from `main`, so this file is the shared history of what each machine is
running. Newest first.

## [Unreleased] — Concurrent registry reads (threaded + cached)

Bootstrap `:7700` used to re-parse every `~/.asmp/services/*.asmp.yaml` on
**every** GET and serve them on a single-threaded `HTTPServer` (listen backlog
5). Concurrent agent/tool fan-out serialized (~50ms × N) and hard bursts reset
connections.

### Changed
- **In-memory service/host index** with mtime signature invalidation. Warm
  lookups stay in process; disk is re-read when a manifest is written, a file
  changes, or `POST /reload` runs.
- **`ThreadingHTTPServer`** so concurrent GETs overlap.
- **Listen backlog 128** (class-level `request_queue_size`) so agent fan-out is
  not dropped at accept.

### Contract
- Warm sequential reads should be sub-millisecond to low-single-digit ms on a
  laptop, not “parse all YAML every time.”
- Concurrent `/health` (dozens of parallel clients) must complete with **zero**
  connection failures and wall time clearly better than serial × N.

### Tests
- `tests/test_asmp_serve_cache.py` — warm cache, write invalidation, external
  file mtime, concurrent health, source guards.

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
