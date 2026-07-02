#!/usr/bin/env python3
"""Run Grok as a bounded read-only second-opinion helper.

This wrapper exists so Codex can call Grok without hanging on interactive
permission prompts or OAuth device-login flows. It intentionally restricts
Grok to read/search/list tools and returns structured JSON on auth blockers.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


GROK = Path("/Users/dshanklin/.local/bin/grok")
DEFAULT_CWD = Path("/Users/dshanklin")
DEFAULT_TIMEOUT = 90


def _combined(proc: subprocess.CompletedProcess[str]) -> str:
    return "\n".join(part for part in [proc.stdout.strip(), proc.stderr.strip()] if part)


def _to_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _auth_required(text: str) -> bool:
    needles = [
        "Waiting for authorization",
        "To sign in, open this URL",
        "token expired",
        "re-authentication required",
        "No auth credentials",
        "invalid_grant",
    ]
    return any(needle in text for needle in needles)


def _json(status: str, **payload: Any) -> int:
    print(json.dumps({"status": status, **payload}, indent=2, sort_keys=True))
    return 0 if status == "ok" else 1


def run(prompt: str, cwd: Path, timeout: int) -> int:
    if not GROK.exists():
        return _json("missing_grok", binary=str(GROK))

    cmd = [
        str(GROK),
        "-p",
        prompt,
        "--cwd",
        str(cwd),
        "--no-alt-screen",
        "--output-format",
        "json",
        "--max-turns",
        "3",
        "--disallowed-tools",
        "Shell,Write,Agent",
        "--disable-web-search",
        "--debug-file",
        "/Users/dshanklin/.asmp/grok-second-opinion-debug.log",
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        text = "\n".join(part for part in [_to_text(exc.stdout), _to_text(exc.stderr)] if part)
        if _auth_required(text):
            return _json(
                "auth_required",
                message="Grok needs interactive re-authentication; do not retry headlessly.",
                binary=str(GROK),
                reauth_command="/Users/dshanklin/.local/bin/grok login --device-auth",
            )
        return _json("timeout", message=f"Timed out after {timeout}s", output=text[-4000:])

    text = _combined(proc)
    if _auth_required(text):
        return _json(
            "auth_required",
            message="Grok needs interactive re-authentication; do not retry headlessly.",
            returncode=proc.returncode,
            reauth_command="/Users/dshanklin/.local/bin/grok login --device-auth",
            output=text[-4000:],
        )

    parsed: Any = None
    if proc.stdout.strip():
        try:
            parsed = json.loads(proc.stdout)
        except json.JSONDecodeError:
            parsed = None

    if proc.returncode != 0:
        return _json("error", returncode=proc.returncode, output=text[-4000:])

    return _json(
        "ok",
        returncode=proc.returncode,
        response=parsed if parsed is not None else proc.stdout.strip(),
        stderr=proc.stderr.strip(),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run bounded read-only Grok second-opinion prompt")
    parser.add_argument("prompt", nargs="?", help="Prompt text. If omitted, reads stdin.")
    parser.add_argument("--cwd", default=str(DEFAULT_CWD), help="Working directory for Grok.")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="Timeout in seconds.")
    args = parser.parse_args()

    prompt = args.prompt if args.prompt is not None else sys.stdin.read()
    prompt = prompt.strip()
    if not prompt:
        return _json("usage_error", message="prompt is required")
    return run(prompt, Path(args.cwd).expanduser(), args.timeout)


if __name__ == "__main__":
    raise SystemExit(main())
