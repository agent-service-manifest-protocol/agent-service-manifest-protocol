#!/usr/bin/env python3
"""Minimal ASMP registry server — reads ~/.asmp/services/*.asmp.yaml, serves :7700.

Standalone bootstrap until `pip install asmp-registry` ships.
Includes scan/reload/announce parity with aic-director-daemon registry.
Spec: https://agentservicemanifest.io/spec/registration-api
"""
from __future__ import annotations

import json
import logging
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
PORT = 7700

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


def load_services() -> dict[str, dict]:
    services: dict[str, dict] = {}
    if not SERVICES_DIR.exists():
        return services
    for path in sorted(SERVICES_DIR.glob("*.asmp.yaml")):
        try:
            with path.open() as f:
                manifest = yaml.safe_load(f) or {}
            name = manifest.get("name") or path.stem.replace(".asmp", "")
            services[name] = manifest
        except Exception as e:
            log.warning("Skipping %s: %s", path, e)
    return services


def write_manifest(manifest: dict) -> Path:
    SERVICES_DIR.mkdir(parents=True, exist_ok=True)
    name = manifest["name"]
    path = SERVICES_DIR / f"{name}.asmp.yaml"
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
    services = load_services()
    now = datetime.now(timezone.utc).isoformat()
    generation = 1
    if name in services:
        generation = int(services[name].get("generation") or 0) + 1
    merged = {
        **manifest,
        "generation": generation,
        "last_seen": now,
        "sync": "announce",
        "status": "registered",
    }
    write_manifest(merged)
    api = (host.get("registry") or {}).get("api", f"http://127.0.0.1:{PORT}")
    return True, {
        "name": name,
        "generation": generation,
        "status": "registered",
        "index_url": f"{api.rstrip('/')}/services/{name}",
    }


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

        if path == "/services":
            self._json([{"name": n, **{k: v for k, v in m.items() if k != "name"}} for n, m in services.items()])
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

        if path == "/reload":
            services = load_services()
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


def main():
    SERVICES_DIR.mkdir(parents=True, exist_ok=True)
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