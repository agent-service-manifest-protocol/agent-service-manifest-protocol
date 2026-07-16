#!/usr/bin/env python3
"""Minimal ASMP registry server — reads ~/.asmp/services/*.asmp.yaml, serves :7700.

Standalone bootstrap until `pip install asmp-registry` ships.
Includes scan/reload/announce parity with aic-director-daemon registry.
Spec: https://agentservicemanifest.io/spec/registration-api
"""
from __future__ import annotations

import json
import logging
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qs, urlparse

import yaml

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("asmp.serve")

ASMP_DIR = Path.home() / ".asmp"
SERVICES_DIR = ASMP_DIR / "services"
HOST_FILE = ASMP_DIR / "host.yaml"
HISTORY_FILE = ASMP_DIR / "host-history.jsonl"
PORT = 7700

# In-memory index. Every request used to re-parse all ~/.asmp/services/*.yaml.
# Cache by directory mtime signature; invalidate on write. ThreadingHTTPServer
# serves concurrent readers; RLock guards refresh/write.
_cache_lock = threading.RLock()
_host_cache: Optional[dict] = None
_host_mtime_ns: Optional[int] = None
_services_cache: Optional[dict[str, dict]] = None
_services_sig: Optional[tuple] = None


def host_name(host: dict) -> str:
    """This machine's canonical name."""
    return host.get("host_id") or host.get("hostname") or "localhost"


def entry_key(manifest: dict, local: str) -> str:
    """Registry key. Local services keep their bare name; remote (federated)
    services are namespaced name@host so they never clobber a local service of
    the same name (e.g. conduit exists on every machine)."""
    name = manifest.get("name", "")
    h = manifest.get("host") or local
    return name if h == local else f"{name}@{h}"

MANIFEST_NAMES = ("asmp.yaml", "infra/asmp.yaml")
DEFAULT_SCAN_ROOTS = ["~/repos-personal", "~/repos-aic", "~/repos-eidos-agi"]


def _host_file_mtime_ns() -> Optional[int]:
    try:
        return HOST_FILE.stat().st_mtime_ns if HOST_FILE.exists() else None
    except OSError:
        return None


def _services_signature() -> tuple:
    """Cheap fingerprint of the services directory — names, sizes, mtimes."""
    if not SERVICES_DIR.exists():
        return (0, ())
    try:
        dir_mtime = SERVICES_DIR.stat().st_mtime_ns
    except OSError:
        dir_mtime = 0
    files: list[tuple[str, int, int]] = []
    try:
        for path in SERVICES_DIR.glob("*.asmp.yaml"):
            try:
                st = path.stat()
                files.append((path.name, st.st_mtime_ns, st.st_size))
            except OSError:
                continue
    except OSError:
        return (dir_mtime, ())
    files.sort()
    return (dir_mtime, tuple(files))


def invalidate_caches() -> None:
    """Drop cached host + services. Next load rebuilds from disk."""
    global _host_cache, _host_mtime_ns, _services_cache, _services_sig
    with _cache_lock:
        _host_cache = None
        _host_mtime_ns = None
        _services_cache = None
        _services_sig = None


def load_host(*, force: bool = False) -> dict:
    global _host_cache, _host_mtime_ns
    with _cache_lock:
        mtime = _host_file_mtime_ns()
        if (
            not force
            and _host_cache is not None
            and _host_mtime_ns == mtime
        ):
            return dict(_host_cache)
        if HOST_FILE.exists():
            with HOST_FILE.open() as f:
                data = yaml.safe_load(f) or {}
        else:
            data = {
                "host_id": "unknown",
                "registry": {"path": str(SERVICES_DIR), "api": f"http://127.0.0.1:{PORT}"},
            }
        _host_cache = data
        _host_mtime_ns = mtime
        return dict(data)


def _load_services_from_disk(local: str) -> dict[str, dict]:
    services: dict[str, dict] = {}
    if not SERVICES_DIR.exists():
        return services
    for path in sorted(SERVICES_DIR.glob("*.asmp.yaml")):
        try:
            with path.open() as f:
                manifest = yaml.safe_load(f) or {}
            if not manifest.get("name"):
                manifest["name"] = path.stem.replace(".asmp", "").split("@")[0]
            manifest.setdefault("host", local)
            services[entry_key(manifest, local)] = manifest
        except Exception as e:
            log.warning("Skipping %s: %s", path, e)
    return services


def load_services(local: Optional[str] = None, *, force: bool = False) -> dict[str, dict]:
    """Return the service index. Cached; rebuilds when any manifest mtime changes."""
    global _services_cache, _services_sig
    if local is None:
        local = host_name(load_host())
    with _cache_lock:
        sig = _services_signature()
        if (
            not force
            and _services_cache is not None
            and _services_sig == sig
        ):
            return dict(_services_cache)
        services = _load_services_from_disk(local)
        _services_cache = services
        _services_sig = sig
        return dict(services)


_PROBE_TIMEOUT = 4
_health_cache: dict = {"ts": 0.0, "data": None}
_HEALTH_TTL = 15  # ponytail: cheap-and-repeatable — don't re-probe on every poll


def probe_one(manifest: dict, local: str) -> str:
    """Real vital for one service -> healthy|degraded|unhealthy|unchecked.
    Never fabricates: no health spec or a remote host we can't reach -> unchecked."""
    # only probe services that live on this machine; remote/federated are unreachable here
    if manifest.get("host") and manifest["host"] != local:
        return "unchecked"
    h = manifest.get("health") or {}
    method, target = h.get("method"), h.get("target", "")
    if not method or not target:
        return "unchecked"
    try:
        if method == "http":
            try:
                with urllib.request.urlopen(urllib.request.Request(target, method="GET"), timeout=_PROBE_TIMEOUT):
                    return "healthy"
            except urllib.error.HTTPError:
                return "healthy"  # server answered (even 4xx) == it's up
        if method == "tcp":
            host, port = target.rsplit(":", 1)
            with socket.create_connection((host, int(port)), timeout=_PROBE_TIMEOUT):
                return "healthy"
        if method == "launchctl":
            r = subprocess.run(["launchctl", "list", target], capture_output=True, text=True, timeout=_PROBE_TIMEOUT)
            if r.returncode != 0:
                return "unhealthy"
            pid = next((l.split("=")[1].strip().rstrip(";").strip()
                        for l in r.stdout.splitlines() if '"PID"' in l), None)
            return "healthy" if pid and pid != "0" else "degraded"
        return "unchecked"  # unknown method -> honest unchecked, never assumed ok
    except Exception:
        return "unhealthy"


def probe_health(services: dict, local: str) -> dict:
    """Parallel real-vitals sweep with a short TTL cache. Replaces the old
    hardcoded {healthy:0, unchecked:N} that never took a pulse."""
    now = time.time()
    if _health_cache["data"] and now - _health_cache["ts"] < _HEALTH_TTL:
        return _health_cache["data"]
    manifests = list(services.values())
    with ThreadPoolExecutor(max_workers=16) as ex:
        statuses = list(ex.map(lambda m: probe_one(m, local), manifests))
    counts = {"healthy": 0, "degraded": 0, "unhealthy": 0, "unchecked": 0}
    for s in statuses:
        counts[s] = counts.get(s, 0) + 1
    data = {"total": len(manifests), "checked_at": datetime.now(timezone.utc).isoformat(), **counts}
    _health_cache.update(ts=now, data=data)
    return data


def write_manifest(manifest: dict, local: Optional[str] = None) -> Path:
    if local is None:
        local = host_name(load_host())
    manifest.setdefault("host", local)
    SERVICES_DIR.mkdir(parents=True, exist_ok=True)
    path = SERVICES_DIR / f"{entry_key(manifest, local)}.asmp.yaml"
    with _cache_lock:
        with path.open("w") as f:
            yaml.safe_dump(manifest, f, default_flow_style=False, sort_keys=False)
        global _services_cache, _services_sig
        _services_cache = None
        _services_sig = None
    return path


def get_scan_paths(host: dict) -> list[Path]:
    discovery = host.get("discovery") or {}
    raw_paths = discovery.get("scan_paths") or DEFAULT_SCAN_ROOTS
    paths = []
    for item in raw_paths:
        p = Path(str(item)).expanduser()
        if p.exists():
            paths.append(p)
    return paths


def find_source_manifests(scan_paths: list[Path]) -> list[Path]:
    found: dict[str, Path] = {}
    for root in scan_paths:
        if not root.is_dir():
            continue
        for rel in MANIFEST_NAMES:
            for path in root.glob(f"*/{rel}"):
                if path.is_file():
                    found[str(path.resolve())] = path
    return sorted(found.values(), key=lambda p: str(p))


def parse_source_manifest(path: Path) -> Optional[dict]:
    try:
        with path.open() as f:
            data = yaml.safe_load(f)
    except Exception as e:
        log.warning("Failed to read %s: %s", path, e)
        return None
    if not isinstance(data, dict):
        return None
    if data.get("asmp") != "0.1":
        return None
    if data.get("kind") not in ("service", "tool", "mcp-server"):
        return None
    if not data.get("name"):
        return None
    provides = (data.get("capabilities") or {}).get("provides") or []
    if not provides:
        return None
    return data


def sync_from_sources(host: dict) -> dict:
    services = load_services()
    paths = find_source_manifests(get_scan_paths(host))
    now = datetime.now(timezone.utc).isoformat()
    seen_names: set[str] = set()
    stats = {"scanned": 0, "registered": 0, "updated": 0, "skipped": 0, "stale": 0}

    for path in paths:
        manifest = parse_source_manifest(path)
        if not manifest:
            stats["skipped"] += 1
            continue
        stats["scanned"] += 1
        name = manifest["name"]
        seen_names.add(name)
        source = str(path.resolve())
        existing = services.get(name)
        generation = 1
        if existing:
            generation = int(existing.get("generation") or 0) + 1
        merged = {
            **manifest,
            "source": source,
            "last_seen": now,
            "generation": generation,
            "sync": "scan",
            "status": "registered",
        }
        if existing and existing.get("source") == source:
            stats["updated"] += 1
        else:
            stats["registered"] += 1
        write_manifest(merged)
        services[name] = merged

    stale_after = int((host.get("discovery") or {}).get("stale_after", 900))
    now_dt = datetime.now(timezone.utc)
    for name, manifest in list(services.items()):
        if manifest.get("sync") != "scan":
            continue
        source = manifest.get("source")
        if name in seen_names and source and Path(source).exists():
            last_seen = manifest.get("last_seen")
            if last_seen:
                try:
                    seen_at = datetime.fromisoformat(last_seen.replace("Z", "+00:00"))
                    if (now_dt - seen_at).total_seconds() <= stale_after:
                        continue
                except ValueError:
                    pass
        if manifest.get("status") == "stale":
            stats["stale"] += 1
            continue
        manifest["status"] = "stale"
        write_manifest(manifest)
        stats["stale"] += 1

    return stats


def announce_manifest(manifest: dict, host: dict) -> tuple[bool, dict | str]:
    name = manifest.get("name")
    if not name:
        return False, "name required"
    local = host_name(host)
    manifest.setdefault("host", local)
    key = entry_key(manifest, local)
    services = load_services(local)
    now = datetime.now(timezone.utc).isoformat()
    generation = 1
    if key in services:
        generation = int(services[key].get("generation") or 0) + 1
    merged = {
        **manifest,
        "generation": generation,
        "last_seen": now,
        "sync": "announce",
        "status": "registered",
    }
    write_manifest(merged, local)
    api = (host.get("registry") or {}).get("api", f"http://127.0.0.1:{PORT}")
    return True, {
        "name": name,
        "host": merged["host"],
        "generation": generation,
        "status": "registered",
        "index_url": f"{api.rstrip('/')}/services/{key}",
    }


# ── Host discovery + cross-system federation ───────────────────────

def known_hosts(host: dict) -> dict:
    """Every host ASMP knows about: this machine, hosts that have federated
    services in, and machines merely declared reachable in a service's
    infra.machines (e.g. conduit). host_aliases collapses alternate names."""
    local = host_name(host)
    aliases = (host.get("federation") or {}).get("host_aliases") or {}
    hosts: dict[str, dict] = {}

    def canon(n: str) -> str:
        return aliases.get(n, n)

    def ensure(n: str) -> dict:
        n = canon(n)
        return hosts.setdefault(n, {
            "host": n, "services": 0, "declared_only": True, "self": n == local,
        })

    ensure(local)["declared_only"] = False
    for m in load_services(local).values():
        h = ensure(m.get("host", local))
        h["declared_only"] = False
        h["services"] += 1
        for mc in ((m.get("infra") or {}).get("machines") or []):
            ensure(mc)
    return {"local": local, "hosts": sorted(hosts.values(), key=lambda x: x["host"])}


def snapshot_hosts(host: dict) -> dict:
    """Append the current host roster to the durable history log (one JSON
    line per host per snapshot)."""
    snap = known_hosts(host)
    ts = datetime.now(timezone.utc).isoformat()
    try:
        HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        with HISTORY_FILE.open("a") as f:
            for h in snap["hosts"]:
                f.write(json.dumps({"ts": ts, **h}) + "\n")
    except Exception as e:
        log.warning("host history write failed: %s", e)
    return snap


def host_history(host_filter: Optional[str] = None, limit: int = 200) -> list[dict]:
    if not HISTORY_FILE.exists():
        return []
    rows = []
    with HISTORY_FILE.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if host_filter and r.get("host") != host_filter:
                continue
            rows.append(r)
    return rows[-limit:]


def _peer_fetch_cmd(peer: dict, fed: dict) -> Optional[list[str]]:
    """Command that prints a peer's /services JSON. Prefers conduit — the fleet's
    reach/auth layer (it owns each machine's user+endpoint+host-key handling) —
    when the peer names a conduit `machine_id`; falls back to a raw ssh target."""
    fetch = "curl -s --max-time 5 http://127.0.0.1:7700/services"
    if peer.get("conduit"):
        conduit_bin = str(Path(fed.get("conduit_bin") or "conduit").expanduser())
        return [conduit_bin, "run", "--target", peer["conduit"], "sh", "-c", fetch]
    if peer.get("ssh"):
        return ["ssh", "-o", "ConnectTimeout=8", "-o", "BatchMode=yes",
                "-o", "StrictHostKeyChecking=accept-new", peer["ssh"], fetch]
    return None


def sync_peers(host: dict) -> dict:
    """Pull each configured peer's registry and write its services locally,
    stamped with the peer's canonical host. Peers are localhost-bound, so we
    reach them via conduit (preferred) or raw SSH.

    O(n) in services: write_manifest directly rather than announce_manifest,
    which would reload the whole registry per service (O(n^2) — chokes the
    single-threaded server on a real fleet)."""
    fed = host.get("federation") or {}
    peers = fed.get("peers") or []
    local = host_name(host)
    stats = {"peers": 0, "synced": 0, "errors": 0}
    for peer in peers:
        label = peer.get("host")
        cmd = _peer_fetch_cmd(peer, fed)
        if not label or not cmd:
            continue
        stats["peers"] += 1
        try:
            out = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30,
            )
            if out.returncode != 0:
                raise RuntimeError(out.stderr.strip() or f"reach exit {out.returncode}")
            data = json.loads(out.stdout)
            services = data if isinstance(data, list) else data.get("services", [])
        except Exception as e:
            log.warning("peer %s (%s) unreachable: %s",
                        label, peer.get("conduit") or peer.get("ssh"), e)
            stats["errors"] += 1
            continue
        now = datetime.now(timezone.utc).isoformat()
        for m in services:
            if not isinstance(m, dict) or m.get("asmp") != "0.1" or not m.get("name"):
                continue
            # Only the peer's OWN services — skip what it federated from elsewhere,
            # so transitive entries don't bloat/mis-attribute (mesh-safe).
            if m.get("sync") == "federate":
                continue
            write_manifest({**m, "host": label, "sync": "federate", "last_seen": now}, local)
            stats["synced"] += 1
        log.info("federated %d services from %s", stats["synced"], label)
    return stats


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def _json(self, data, status: int = 200):
        body = json.dumps(data, default=str, indent=2).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> Optional[dict]:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return None
        return json.loads(self.rfile.read(length))

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        qs = parse_qs(parsed.query)
        services = load_services()
        host = load_host()

        if path == "/health":
            local = host_name(host)
            vitals = probe_health(services, local)
            status = "ok" if vitals["unhealthy"] == 0 else "degraded"
            self._json({
                "status": status,
                "host": host.get("host_id", host.get("hostname", "unknown")),
                **vitals,
            })
            return

        if path == "/host":
            self._json(host)
            return

        if path == "/hosts":
            self._json(known_hosts(host))
            return

        if path == "/hosts/history":
            self._json({"history": host_history(
                qs.get("host", [None])[0], int(qs.get("limit", ["200"])[0]))})
            return

        if path == "/services":
            host_filter = qs.get("host", [None])[0]
            out = []
            for m in services.values():
                if host_filter and m.get("host") != host_filter:
                    continue
                out.append({"name": m.get("name"), **{k: v for k, v in m.items() if k != "name"}})
            self._json(out)
            return

        if path.startswith("/services/") and path.count("/") == 2:
            name = path.split("/")[2]
            if name not in services:
                self._json({"error": f"Service '{name}' not found"}, 404)
                return
            self._json(services[name])
            return

        if path == "/capabilities":
            cap = qs.get("provides", [None])[0]
            if not cap:
                all_caps = set()
                for m in services.values():
                    all_caps.update(m.get("capabilities", {}).get("provides", []))
                self._json({"capabilities": sorted(all_caps)})
                return
            matches = []
            for m in services.values():
                provides = m.get("capabilities", {}).get("provides", [])
                if cap in provides:
                    matches.append({
                        "name": m.get("name"),
                        "description": m.get("description", ""),
                        "provides": provides,
                        "endpoints": m.get("endpoints", []),
                        "repo": m.get("infra", {}).get("repo") or m.get("repo"),
                        "source": m.get("source"),
                        "status": m.get("status"),
                    })
            self._json(matches)
            return

        self._json({"error": "Not found"}, 404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        host = load_host()

        if path == "/discover/scan":
            self._json(sync_from_sources(host))
            return

        if path == "/federate":
            self._json(sync_peers(host))
            return

        if path == "/reload":
            invalidate_caches()
            services = load_services(force=True)
            self._json({"message": "Registry reloaded", "total": len(services)})
            return

        if path == "/services/announce":
            body = self._read_body()
            if not body:
                self._json({"error": "Request body required"}, 400)
                return
            ok, result = announce_manifest(body, host)
            if ok:
                self._json(result, 201)
            else:
                self._json({"error": result}, 400)
            return

        if path == "/services":
            body = self._read_body()
            if not body:
                self._json({"error": "Empty body"}, 400)
                return
            name = body.get("name")
            if not name:
                self._json({"error": "name required"}, 400)
                return
            out = write_manifest(body)
            log.info("Registered %s", name)
            self._json({"ok": True, "name": name, "path": str(out)}, 201)
            return

        self._json({"error": "Not found"}, 404)


def _federation_loop(interval: float = 300.0):
    """Background: pull peers + snapshot host roster. Only runs if peers set."""
    while True:
        try:
            host = load_host()
            sync_peers(host)
            snapshot_hosts(host)
        except Exception as e:
            log.warning("federation cycle failed: %s", e)
        time.sleep(interval)


def main():
    SERVICES_DIR.mkdir(parents=True, exist_ok=True)
    host = load_host()
    if (host.get("federation") or {}).get("peers"):
        threading.Thread(target=_federation_loop, daemon=True, name="asmp-federate").start()
        log.info("Federation enabled: %d peer(s)", len((host["federation"]["peers"])))
    # Threading so concurrent agent/tool lookups overlap. Cache keeps each
    # thread from re-parsing every YAML on every request. request_queue_size
    # must be on the class (bind happens in __init__); default 5 drops fan-out.
    class _Server(ThreadingHTTPServer):
        daemon_threads = True
        allow_reuse_address = True
        request_queue_size = 128

    server = _Server(("127.0.0.1", PORT), Handler)
    log.info(
        "ASMP registry on http://127.0.0.1:%s (%s services, threaded+cached)",
        PORT,
        len(load_services()),
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()