"""Bootstrap registry: /health must take a real pulse.

Locks the honesty contract. /health shipped for months as a hardcoded
{healthy: 0, unhealthy: 0, unchecked: len(services)} literal that never
probed anything — so a box with 27 dead services reported "status": "ok".
A real Python probe implementation existed, was never pushed, and was
silently dropped by a merge; nothing caught it because nothing checked.

These tests fail if /health ever goes back to fabricating.
"""
from __future__ import annotations

import importlib.util
import socket
import threading
from importlib.machinery import SourceFileLoader
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SERVE_PY = REPO / "scripts" / "asmp-serve.py"


def load_serve():
    loader = SourceFileLoader("asmp_serve_health_under_test", str(SERVE_PY))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _reset_cache(m):
    m._health_cache.update(ts=0.0, data=None)


def test_no_health_spec_is_unchecked_never_healthy():
    """A service that declares no health block is unchecked — never assumed up."""
    m = load_serve()
    assert m.probe_one({"name": "x"}, "local") == "unchecked"
    assert m.probe_one({"name": "x", "health": {}}, "local") == "unchecked"
    # method without target, and target without method, are both unchecked
    assert m.probe_one({"health": {"method": "tcp"}}, "local") == "unchecked"
    assert m.probe_one({"health": {"target": "localhost:1"}}, "local") == "unchecked"


def test_unknown_method_is_unchecked_never_healthy():
    """An unrecognized probe method is honest-unchecked, not assumed ok.

    'pid' is a real method in the wild that this prober does not implement.
    """
    m = load_serve()
    assert m.probe_one({"health": {"method": "pid", "target": "1234"}}, "local") == "unchecked"


def test_remote_host_is_unchecked_not_probed():
    """Federated services live elsewhere; we cannot take their pulse from here."""
    m = load_serve()
    manifest = {"host": "other-box", "health": {"method": "tcp", "target": "localhost:9"}}
    assert m.probe_one(manifest, "this-box") == "unchecked"


def test_dead_tcp_port_is_unhealthy():
    """The whole point: something that is down must report down."""
    m = load_serve()
    # bind and immediately close, so the port is near-certainly dead
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    dead_port = s.getsockname()[1]
    s.close()
    manifest = {"health": {"method": "tcp", "target": f"127.0.0.1:{dead_port}"}}
    assert m.probe_one(manifest, "local") == "unhealthy"


def test_live_tcp_port_is_healthy():
    """And something that is up must report up — a real pulse, not a literal."""
    m = load_serve()
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    port = srv.getsockname()[1]
    threading.Thread(target=lambda: srv.accept(), daemon=True).start()
    try:
        manifest = {"health": {"method": "tcp", "target": f"127.0.0.1:{port}"}}
        assert m.probe_one(manifest, "local") == "healthy"
    finally:
        srv.close()


def test_probe_health_counts_are_real_not_fabricated():
    """A mixed set must produce mixed counts — the regression was all-zero."""
    m = load_serve()
    _reset_cache(m)

    live = socket.socket()
    live.bind(("127.0.0.1", 0))
    live.listen(1)
    live_port = live.getsockname()[1]
    threading.Thread(target=lambda: live.accept(), daemon=True).start()

    dead = socket.socket()
    dead.bind(("127.0.0.1", 0))
    dead_port = dead.getsockname()[1]
    dead.close()

    try:
        services = {
            "up": {"health": {"method": "tcp", "target": f"127.0.0.1:{live_port}"}},
            "down": {"health": {"method": "tcp", "target": f"127.0.0.1:{dead_port}"}},
            "silent": {"name": "no-health-block"},
        }
        data = m.probe_health(services, "local")
        assert data["total"] == 3
        assert data["healthy"] == 1, "a live port must count as healthy"
        assert data["unhealthy"] == 1, "a dead port must count as unhealthy"
        assert data["unchecked"] == 1, "no health spec must count as unchecked"
        assert "checked_at" in data, "must report when it actually looked"
    finally:
        live.close()
        _reset_cache(m)


def test_health_endpoint_is_not_the_hardcoded_literal():
    """Guard the exact regression: /health must not hardcode healthy=0."""
    source = SERVE_PY.read_text()
    handler = source.split('if path == "/health":')[1].split("if path ==")[0]
    assert "probe_health" in handler, "/health must call probe_health, not fabricate"
    assert '"healthy": 0' not in handler, "/health must not hardcode healthy=0 again"
