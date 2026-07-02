#!/usr/bin/env python3
"""ASMP MCP server.

Tiny dependency-free stdio MCP wrapper around the local `asmp` CLI.
The CLI remains the source of truth; this server only gives Codex a first-class
tool surface for the same registry operations.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ASMP = os.environ.get("ASMP_CLI", "/Users/dshanklin/.local/bin/asmp")
ASMP_DIR = Path.home() / ".asmp"
SERVICES_DIR = ASMP_DIR / "services"
CACHE_FILE = ASMP_DIR / "session-cache.json"
CACHE_TTL_SECONDS = int(os.environ.get("ASMP_CACHE_TTL_SECONDS", "300"))
TIMEOUT_SECONDS = 60


TOOLS: list[dict[str, Any]] = [
    {
        "name": "asmp_health",
        "description": "Return local ASMP registry health.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "asmp_host",
        "description": "Return the ASMP host profile.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "asmp_list_services",
        "description": "List registered ASMP services.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "asmp_session_context",
        "description": "Return cached ASMP health, capabilities, and service list for session bootstrap. Refreshes only when stale, forced, or manifests changed.",
        "inputSchema": {
            "type": "object",
            "properties": {"refresh": {"type": "boolean"}},
            "additionalProperties": False,
        },
    },
    {
        "name": "asmp_route",
        "description": "Route a task to likely ASMP services from cached service metadata without repeated registry calls.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "capability": {"type": "string"},
                "refresh": {"type": "boolean"},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "asmp_get_service",
        "description": "Get one ASMP service manifest by name.",
        "inputSchema": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
            "additionalProperties": False,
        },
    },
    {
        "name": "asmp_find_services",
        "description": "Find ASMP services by text query and/or provided capability.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "capability": {"type": "string"},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "asmp_capabilities",
        "description": "List all capabilities or services that provide one capability.",
        "inputSchema": {
            "type": "object",
            "properties": {"provides": {"type": "string"}},
            "additionalProperties": False,
        },
    },
    {
        "name": "asmp_scan",
        "description": "Scan configured roots for shipped asmp.yaml manifests and update the registry.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "asmp_register_manifest",
        "description": "Register a local ASMP manifest YAML file with the local registry.",
        "inputSchema": {
            "type": "object",
            "properties": {"manifest_path": {"type": "string"}},
            "required": ["manifest_path"],
            "additionalProperties": False,
        },
    },
    {
        "name": "asmp_todo",
        "description": "Record a discovery note for a real agent/service that is not discoverable in ASMP yet.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "note": {"type": "string"},
                "repo": {"type": "string"},
                "hint": {"type": "string"},
                "found_by": {"type": "string"},
            },
            "required": ["name"],
            "additionalProperties": False,
        },
    },
    {
        "name": "asmp_cli",
        "description": "Run an ASMP CLI subcommand. Pass args without the leading `asmp`; prefer read-only commands and `--json` output.",
        "inputSchema": {
            "type": "object",
            "properties": {"args": {"type": "array", "items": {"type": "string"}}},
            "required": ["args"],
            "additionalProperties": False,
        },
    },
]


def _run(args: list[str], json_mode: bool = True) -> dict[str, Any]:
    if not Path(ASMP).exists():
        return {"ok": False, "error": f"asmp CLI not found at {ASMP}"}
    cmd = [ASMP]
    if json_mode and "--json" not in args:
        cmd.append("--json")
    cmd.extend(args)
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"timed out running: {' '.join(cmd)}"}
    stdout = proc.stdout.strip()
    stderr = proc.stderr.strip()
    payload: Any = stdout
    if stdout:
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError:
            payload = stdout
    return {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "command": cmd,
        "stdout": payload,
        "stderr": stderr,
    }


def _manifest_fingerprint() -> dict[str, Any]:
    files = sorted(SERVICES_DIR.glob("*.asmp.yaml"))
    latest_mtime = 0.0
    total_size = 0
    names: list[str] = []
    for path in files:
        try:
            stat = path.stat()
        except OSError:
            continue
        latest_mtime = max(latest_mtime, stat.st_mtime)
        total_size += stat.st_size
        names.append(path.name)
    return {
        "count": len(names),
        "latest_mtime": latest_mtime,
        "total_size": total_size,
        "names": names,
    }


def _read_cache() -> dict[str, Any] | None:
    try:
        return json.loads(CACHE_FILE.read_text())
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def _cache_is_fresh(cache: dict[str, Any], fingerprint: dict[str, Any]) -> bool:
    generated_at = cache.get("generated_at")
    if not isinstance(generated_at, (int, float)):
        return False
    if time.time() - float(generated_at) > CACHE_TTL_SECONDS:
        return False
    return cache.get("fingerprint") == fingerprint


def _build_session_context() -> dict[str, Any]:
    health = _run(["health"])
    capabilities = _run(["caps"])
    services = _run(["list"])
    context = {
        "generated_at": time.time(),
        "ttl_seconds": CACHE_TTL_SECONDS,
        "fingerprint": _manifest_fingerprint(),
        "health": health.get("stdout"),
        "capabilities": capabilities.get("stdout"),
        "services": services.get("stdout"),
        "commands": {
            "health": health.get("command"),
            "capabilities": capabilities.get("command"),
            "services": services.get("command"),
        },
    }
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(json.dumps(context, indent=2, sort_keys=True) + "\n")
    return context


def _session_context(refresh: bool = False) -> dict[str, Any]:
    fingerprint = _manifest_fingerprint()
    cache = _read_cache()
    if not refresh and cache and _cache_is_fresh(cache, fingerprint):
        return {**cache, "cache": "hit"}
    context = _build_session_context()
    return {**context, "cache": "refresh"}


def _service_matches(service: dict[str, Any], query: str, capability: str) -> bool:
    provides = (service.get("capabilities") or {}).get("provides") or []
    if capability and capability not in provides:
        return False
    if not query:
        return True
    haystack = " ".join(
        str(part)
        for part in [
            service.get("name", ""),
            service.get("description", ""),
            " ".join(str(item) for item in provides),
            service.get("kind", ""),
        ]
    ).lower()
    return query.lower() in haystack


def _route(arguments: dict[str, Any]) -> dict[str, Any]:
    query = arguments.get("query")
    capability = arguments.get("capability")
    refresh = bool(arguments.get("refresh"))
    query = query.strip() if isinstance(query, str) else ""
    capability = capability.strip() if isinstance(capability, str) else ""
    context = _session_context(refresh=refresh)
    services = context.get("services") or []
    if not isinstance(services, list):
        services = []
    matches = [
        service
        for service in services
        if isinstance(service, dict) and _service_matches(service, query, capability)
    ]
    return {
        "cache": context.get("cache"),
        "query": query or None,
        "capability": capability or None,
        "matches": matches,
        "selected": matches[0] if len(matches) == 1 else None,
        "policy": "Use selected when exactly one service matches; otherwise inspect names/descriptions and call asmp_get_service only for the chosen service.",
    }


def _required_string(arguments: dict[str, Any], key: str) -> str:
    value = arguments.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} is required")
    return value.strip()


def call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name == "asmp_health":
        return _run(["health"])
    if name == "asmp_host":
        return _run(["host"])
    if name == "asmp_list_services":
        return _run(["list"])
    if name == "asmp_session_context":
        return _session_context(refresh=bool(arguments.get("refresh")))
    if name == "asmp_route":
        return _route(arguments)
    if name == "asmp_get_service":
        return _run(["get", _required_string(arguments, "name")])
    if name == "asmp_find_services":
        args = ["find"]
        query = arguments.get("query")
        capability = arguments.get("capability")
        if isinstance(query, str) and query.strip():
            args.extend(["--query", query.strip()])
        if isinstance(capability, str) and capability.strip():
            args.extend(["--capability", capability.strip()])
        return _run(args)
    if name == "asmp_capabilities":
        args = ["caps"]
        provides = arguments.get("provides")
        if isinstance(provides, str) and provides.strip():
            args.extend(["--provides", provides.strip()])
        return _run(args)
    if name == "asmp_scan":
        return _run(["scan"])
    if name == "asmp_register_manifest":
        manifest_path = Path(_required_string(arguments, "manifest_path")).expanduser()
        return _run(["register", str(manifest_path)])
    if name == "asmp_todo":
        args = ["todo", _required_string(arguments, "name")]
        for arg_name, cli_name in [
            ("note", "--note"),
            ("repo", "--repo"),
            ("hint", "--hint"),
            ("found_by", "--found-by"),
        ]:
            value = arguments.get(arg_name)
            if isinstance(value, str) and value.strip():
                args.extend([cli_name, value.strip()])
        return _run(args, json_mode=False)
    if name == "asmp_cli":
        raw_args = arguments.get("args")
        if not isinstance(raw_args, list) or not all(isinstance(item, str) for item in raw_args):
            raise ValueError("args must be a list of strings")
        return _run(raw_args, json_mode=False)
    raise ValueError(f"unknown tool: {name}")


def respond(req: dict[str, Any], result: Any = None, error: Any = None) -> None:
    payload: dict[str, Any] = {"jsonrpc": "2.0", "id": req.get("id")}
    if error is not None:
        payload["error"] = error
    else:
        payload["result"] = result
    sys.stdout.write(json.dumps(payload) + "\n")
    sys.stdout.flush()


def main() -> None:
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError as exc:
            respond({"id": None}, error={"code": -32700, "message": str(exc)})
            continue
        method = req.get("method")
        if method == "initialize":
            respond(
                req,
                {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "asmp", "version": "0.1.0"},
                },
            )
        elif method == "notifications/initialized":
            continue
        elif method == "tools/list":
            respond(req, {"tools": TOOLS})
        elif method == "tools/call":
            params = req.get("params", {})
            try:
                payload = call_tool(params.get("name", ""), params.get("arguments", {}) or {})
                respond(req, {"content": [{"type": "text", "text": json.dumps(payload, indent=2)}]})
            except Exception as exc:
                respond(req, error={"code": -32603, "message": str(exc)})
        else:
            respond(req, error={"code": -32601, "message": f"method not found: {method}"})


if __name__ == "__main__":
    main()
