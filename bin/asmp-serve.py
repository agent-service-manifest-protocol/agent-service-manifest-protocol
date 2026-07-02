#!/usr/bin/env python3
"""Minimal ASMP registry server — reads ~/.asmp/services/*.asmp.yaml, serves :7700.

Standalone bootstrap until `pip install asmp-registry` ships.
Includes scan/reload/announce parity with aic-director-daemon registry.
Spec: https://agentservicemanifest.io/spec/registration-api
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import subprocess
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
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


def load_host() -> dict:
    if HOST_FILE.exists():
        with HOST_FILE.open() as f:
            return yaml.safe_load(f) or {}
    return {
        "host_id": "unknown",
        "registry": {"path": str(SERVICES_DIR), "api": f"http://127.0.0.1:{PORT}"},
    }


def load_services(local: Optional[str] = None) -> dict[str, dict]:
    if local is None:
        local = host_name(load_host())
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


def write_manifest(manifest: dict, local: Optional[str] = None) -> Path:
    if local is None:
        local = host_name(load_host())
    manifest.setdefault("host", local)
    SERVICES_DIR.mkdir(parents=True, exist_ok=True)
    path = SERVICES_DIR / f"{entry_key(manifest, local)}.asmp.yaml"
    with path.open("w") as f:
        yaml.safe_dump(manifest, f, default_flow_style=False, sort_keys=False)
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
    if data.get("kind") not in ("service", "tool", "mcp-server", "ai-model"):
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


# ── AI model registry: secret digests, routing, health ─────────────

def compute_secret_digest(env_var: str) -> Optional[str]:
    """Digest of the *current* env value, never the raw secret. Recomputed on
    every request so a rotated/absent key surfaces immediately as unverified."""
    val = os.environ.get(env_var)
    if not val:
        return None
    return "sha256:" + hashlib.sha256(f"{env_var}:{val}".encode()).hexdigest()


def verify_model_secret(manifest: dict) -> dict:
    """Re-derive the secret digest from os.environ and compare to the manifest.
    Models with no `secret` block need no key and count as verified."""
    secret = manifest.get("secret") or {}
    env_var = secret.get("env_var")
    expected = secret.get("digest")
    if not env_var:
        return {"env_var": None, "required": False, "verified": True, "reason": "no secret required"}
    actual = compute_secret_digest(env_var)
    if actual is None:
        return {"env_var": env_var, "required": True, "verified": False, "reason": "env var not set"}
    if not expected:
        return {"env_var": env_var, "required": True, "verified": False, "reason": "no digest in manifest"}
    verified = actual == expected
    return {
        "env_var": env_var,
        "required": True,
        "verified": verified,
        "reason": "digest match" if verified else "digest mismatch",
    }


def model_summary(manifest: dict) -> dict:
    model = manifest.get("model") or {}
    pricing = manifest.get("pricing") or {}
    caps = manifest.get("capabilities") or {}
    secret = verify_model_secret(manifest)
    return {
        "name": manifest.get("name"),
        "description": manifest.get("description", ""),
        "provider": model.get("provider"),
        "model_id": model.get("model_id"),
        "base_url": model.get("base_url"),
        "context_window": model.get("context_window"),
        "max_output_tokens": model.get("max_output_tokens"),
        "provides": caps.get("provides", []),
        "strengths": caps.get("strengths", []),
        "weaknesses": caps.get("weaknesses", []),
        "pricing": {
            "input_per_1m": pricing.get("input_per_1m"),
            "output_per_1m": pricing.get("output_per_1m"),
            "tier": pricing.get("tier"),
            "quota_monthly_tokens": pricing.get("quota_monthly_tokens"),
        },
        "secret_env_var": secret["env_var"],
        "secret_required": secret["required"],
        "secret_verified": secret["verified"],
        "status": manifest.get("status"),
        "host": manifest.get("host"),
    }


def ai_models(services: dict) -> list[dict]:
    return [m for m in services.values() if m.get("kind") == "ai-model"]


def model_cost(manifest: dict) -> float:
    """Comparable cost per 1M tokens — the pricier of input/output."""
    pricing = manifest.get("pricing") or {}
    return max(float(pricing.get("input_per_1m") or 0.0), float(pricing.get("output_per_1m") or 0.0))


def recommend_models(services: dict, task: Optional[str], budget: Optional[float]) -> dict:
    matches = []
    for m in ai_models(services):
        provides = (m.get("capabilities") or {}).get("provides") or []
        if task and task not in provides:
            continue
        if not verify_model_secret(m)["verified"]:
            continue
        cost = model_cost(m)
        if budget is not None and cost > budget:
            continue
        summary = model_summary(m)
        summary["cost_per_1m"] = cost
        matches.append((cost, summary))
    matches.sort(key=lambda item: (item[0], item[1].get("name") or ""))
    ranked = [summary for _cost, summary in matches]
    return {
        "task": task,
        "budget": budget,
        "count": len(ranked),
        "recommended": ranked[0] if ranked else None,
        "models": ranked,
    }


def _parse_duration(val, default: float) -> float:
    if val is None:
        return default
    s = str(val).strip().lower()
    try:
        if s.endswith("ms"):
            return float(s[:-2]) / 1000.0
        if s.endswith("s"):
            return float(s[:-1])
        if s.endswith("m"):
            return float(s[:-1]) * 60.0
        return float(s)
    except ValueError:
        return default


def check_models_health(services: dict) -> list[dict]:
    results = []
    for m in ai_models(services):
        health = m.get("health") or {}
        target = health.get("target")
        entry = {"name": m.get("name"), "target": target, "healthy": False, "status": None, "error": None}
        if not target:
            entry["error"] = "no health target"
            results.append(entry)
            continue
        timeout = _parse_duration(health.get("timeout"), 10.0)
        try:
            req = urllib.request.Request(target, method="GET", headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                entry["status"] = resp.status
                entry["healthy"] = resp.status < 500
        except urllib.error.HTTPError as e:
            # An auth/not-found response still proves the endpoint is reachable.
            entry["status"] = e.code
            entry["healthy"] = e.code < 500
        except Exception as e:  # noqa: BLE001 — network/DNS/timeout all mean unreachable
            entry["error"] = str(e)
        results.append(entry)
    return results


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
            self._json({
                "status": "ok",
                "host": host.get("host_id", host.get("hostname", "unknown")),
                "total": len(services),
                "healthy": 0,
                "unhealthy": 0,
                "unchecked": len(services),
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

        if path == "/models":
            self._json([model_summary(m) for m in ai_models(services)])
            return

        if path == "/models/recommend":
            task = qs.get("task", [None])[0]
            budget_raw = qs.get("budget", [None])[0]
            budget = None
            if budget_raw not in (None, ""):
                try:
                    budget = float(budget_raw)
                except ValueError:
                    self._json({"error": f"invalid budget: {budget_raw}"}, 400)
                    return
            self._json(recommend_models(services, task, budget))
            return

        if path == "/models/health":
            self._json(check_models_health(services))
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
            services = load_services()
            self._json({"message": "Registry reloaded", "total": len(services)})
            return

        if path == "/models/verify":
            services = load_services()
            results = []
            for m in ai_models(services):
                results.append({"name": m.get("name"), **verify_model_secret(m)})
            verified = sum(1 for r in results if r["verified"])
            self._json({
                "total": len(results),
                "verified": verified,
                "unverified": len(results) - verified,
                "results": results,
            })
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
    server = HTTPServer(("127.0.0.1", PORT), Handler)
    log.info("ASMP registry on http://127.0.0.1:%s (%s services)", PORT, len(load_services()))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()