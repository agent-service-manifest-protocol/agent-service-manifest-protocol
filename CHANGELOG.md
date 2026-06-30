# Changelog

Durable, cross-system record of changes to the ASMP reference implementation
(`scripts/asmp-serve.py` + `scripts/asmp`). Every machine bootstraps these
files from `main`, so this file is the shared history of what each machine is
running. Newest first.

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
