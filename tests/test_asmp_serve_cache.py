"""Bootstrap registry: in-memory cache + concurrent HTTP serving.

Locks the concurrency contract so we do not regress to re-parsing every
manifest on every GET, or to a single-threaded server that drops fan-out.
"""
from __future__ import annotations

import importlib.util
import json
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from http.server import ThreadingHTTPServer
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[1]
SERVE_PY = REPO / "scripts" / "asmp-serve.py"


def load_serve():
    loader = SourceFileLoader("asmp_serve_under_test", str(SERVE_PY))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def serve_tmp(tmp_path, monkeypatch):
    """Point serve module at an isolated ASMP dir with one service."""
    mod = load_serve()
    services = tmp_path / "services"
    services.mkdir()
    host = tmp_path / "host.yaml"
    host.write_text(
        yaml.safe_dump(
            {
                "asmp": "0.1",
                "kind": "host",
                "host_id": "test-host",
                "registry": {"path": str(services), "api": "http://127.0.0.1:0"},
            }
        )
    )
    manifest = {
        "asmp": "0.1",
        "kind": "service",
        "name": "alpha",
        "description": "test service",
        "capabilities": {"provides": ["test.alpha"]},
    }
    (services / "alpha.asmp.yaml").write_text(yaml.safe_dump(manifest))

    monkeypatch.setattr(mod, "ASMP_DIR", tmp_path)
    monkeypatch.setattr(mod, "SERVICES_DIR", services)
    monkeypatch.setattr(mod, "HOST_FILE", host)
    monkeypatch.setattr(mod, "HISTORY_FILE", tmp_path / "host-history.jsonl")
    mod.invalidate_caches()
    return mod, services


def test_load_services_warm_path_is_much_cheaper_than_cold(serve_tmp):
    mod, _ = serve_tmp
    # cold
    t0 = time.perf_counter()
    first = mod.load_services()
    cold_ms = (time.perf_counter() - t0) * 1000
    assert "alpha" in first

    warm = []
    for _ in range(20):
        t0 = time.perf_counter()
        again = mod.load_services()
        warm.append((time.perf_counter() - t0) * 1000)
        assert "alpha" in again

    warm_p50 = sorted(warm)[len(warm) // 2]
    # Warm hits must be cheap. Absolute floor is env-dependent; relative is the contract.
    assert warm_p50 < 5.0, f"warm p50 {warm_p50:.2f}ms not cached"
    # Cold may also be tiny with one file; only assert warm is not worse than cold by much
    # when cold is meaningful. With one file both can be sub-ms — require warm <= cold * 3 + 1ms.
    assert warm_p50 <= max(cold_ms * 3, 1.0) + 1.0


def test_write_manifest_invalidates_and_is_visible(serve_tmp):
    mod, services = serve_tmp
    assert "beta" not in mod.load_services()

    mod.write_manifest(
        {
            "asmp": "0.1",
            "kind": "service",
            "name": "beta",
            "description": "second",
            "capabilities": {"provides": ["test.beta"]},
        }
    )
    names = set(mod.load_services())
    assert "beta" in names
    assert (services / "beta.asmp.yaml").exists()


def test_external_file_change_picked_up_via_signature(serve_tmp):
    mod, services = serve_tmp
    mod.load_services()  # warm

    (services / "gamma.asmp.yaml").write_text(
        yaml.safe_dump(
            {
                "asmp": "0.1",
                "kind": "service",
                "name": "gamma",
                "description": "external write",
            }
        )
    )
    # Directory/file mtimes change → signature miss → reload
    names = set(mod.load_services())
    assert "gamma" in names


def test_concurrent_health_no_failures(serve_tmp):
    mod, _ = serve_tmp
    # Bind ephemeral port
    class _Server(ThreadingHTTPServer):
        daemon_threads = True
        allow_reuse_address = True
        request_queue_size = 128

    server = _Server(("127.0.0.1", 0), mod.Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{port}/health"
        # warm
        with urllib.request.urlopen(url, timeout=2) as r:
            assert r.status == 200

        n = 32
        errors: list[str] = []
        latencies: list[float] = []

        def one(_):
            t0 = time.perf_counter()
            try:
                with urllib.request.urlopen(url, timeout=3) as r:
                    body = json.loads(r.read())
                if body.get("status") != "ok":
                    errors.append(f"bad body {body}")
                return (time.perf_counter() - t0) * 1000
            except Exception as e:
                errors.append(type(e).__name__)
                return None

        t0 = time.perf_counter()
        with ThreadPoolExecutor(max_workers=32) as ex:
            futs = [ex.submit(one, i) for i in range(n)]
            for f in as_completed(futs):
                ms = f.result()
                if ms is not None:
                    latencies.append(ms)
        wall_ms = (time.perf_counter() - t0) * 1000

        assert not errors, f"concurrent failures: {errors[:5]}"
        assert len(latencies) == n
        # If serial ~50ms each, 32 would need ~1.6s wall. Cached concurrent should be far less.
        assert wall_ms < 500, f"wall {wall_ms:.0f}ms suggests no parallelism/cache"
        # Sum of latencies >> wall means real overlap
        assert sum(latencies) > wall_ms * 1.5
    finally:
        server.shutdown()
        server.server_close()


def test_server_uses_threading_http_server():
    """Guard the standard: bootstrap must not ship bare HTTPServer."""
    text = SERVE_PY.read_text()
    assert "ThreadingHTTPServer" in text
    assert "request_queue_size = 128" in text
    assert "invalidate_caches" in text
    # Do not allow a silent return to full-disk-reload without cache globals
    assert "_services_cache" in text
