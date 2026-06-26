from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from importlib.machinery import SourceFileLoader


REPO = Path(__file__).resolve().parents[1]
ASMP_CLI = REPO / "scripts" / "asmp"


def load_asmp():
    loader = SourceFileLoader("asmp_cli", str(ASMP_CLI))
    spec = importlib.util.spec_from_loader("asmp_cli", loader)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_json(asmp, *args: str) -> dict:
    import contextlib
    import io

    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        rc = asmp.main(["--json", *args])
    assert rc == 0
    return json.loads(out.getvalue())


def test_session_start_emits_small_context_without_registry_call(monkeypatch):
    asmp = load_asmp()

    def fail_request(*_args, **_kwargs):
        raise AssertionError("SessionStart should not query the full registry")

    monkeypatch.setattr(asmp, "request", fail_request)
    data = run_json(asmp, "ambient", "--event", "SessionStart")

    assert data["injected"] is True
    assert data["bytes"] <= asmp.AMBIENT_EVENT_CAPS["SessionStart"]
    assert "ASMP-aware local service discovery" in data["context"]
    assert "raw manifests" in data["context"]


def test_user_prompt_submit_ignores_unrelated_prompt(monkeypatch):
    asmp = load_asmp()
    monkeypatch.setattr(asmp, "request", lambda *_args, **_kwargs: [])

    data = run_json(asmp, "ambient", "--event", "UserPromptSubmit", "--prompt", "refactor this loop")

    assert data["injected"] is False
    assert data["reason"] == "prompt_not_asmp_relevant"


def test_user_override_disables_ambient(monkeypatch):
    asmp = load_asmp()
    monkeypatch.setenv("ASMP_AMBIENT", "off")

    data = run_json(asmp, "ambient", "--event", "SessionStart")

    assert data["injected"] is False
    assert "ASMP_AMBIENT" in data["reason"]


def test_prompt_override_disables_ambient(monkeypatch):
    asmp = load_asmp()
    monkeypatch.setattr(asmp, "request", lambda *_args, **_kwargs: [])

    data = run_json(
        asmp,
        "ambient",
        "--event",
        "UserPromptSubmit",
        "--prompt",
        "do not use ASMP, just answer",
    )

    assert data["injected"] is False
    assert data["reason"].startswith("user override")


def test_fake_registry_candidates_are_ranked_and_redacted(monkeypatch):
    asmp = load_asmp()
    services = [
        {
            "name": "browser-proof",
            "description": "Runs Browserbase proof safely",
            "capabilities": {"provides": ["browser.validation"]},
            "endpoints": [{"url": "http://user:secret@127.0.0.1:9000/run?token=abc123"}],
            "status": "registered",
        },
        {
            "name": "data-shipper",
            "description": "Ships data publication batches",
            "capabilities": {"provides": ["data.shipment"]},
        },
    ]
    monkeypatch.setattr(asmp, "request", lambda *_args, **_kwargs: services)

    data = run_json(
        asmp,
        "ambient",
        "--event",
        "UserPromptSubmit",
        "--prompt",
        "Which local service owns browser validation?",
    )

    assert data["injected"] is True
    assert data["candidates"][0]["name"] == "browser-proof"
    assert "user:secret" not in data["context"]
    assert "abc123" not in data["context"]
    assert "[REDACTED]" in data["context"]


def test_subagent_requires_relevant_scope_or_parent_flag(monkeypatch):
    asmp = load_asmp()
    monkeypatch.setattr(asmp, "request", lambda *_args, **_kwargs: [])

    skipped = run_json(asmp, "ambient", "--event", "SubagentStart", "--subagent-scope", "edit css")
    injected = run_json(asmp, "ambient", "--event", "SubagentStart", "--parent-used-asmp")

    assert skipped["injected"] is False
    assert skipped["reason"] == "subagent_scope_not_asmp_relevant"
    assert injected["injected"] is True
    assert injected["bytes"] <= asmp.AMBIENT_EVENT_CAPS["SubagentStart"]


def test_max_bytes_too_small_injects_nothing(monkeypatch):
    asmp = load_asmp()
    monkeypatch.setattr(asmp, "request", lambda *_args, **_kwargs: [])

    data = run_json(asmp, "ambient", "--event", "SessionStart", "--max-bytes", "20")

    assert data["injected"] is False
    assert data["reason"] == "max_bytes_too_small"


def test_eidos_oracle_contract_works_without_registry():
    asmp = load_asmp()

    data = run_json(asmp, "oracle", "--no-registry", "who should prove whether this SSO setup is safe?")

    assert data["product"] == "Eidos Oracle"
    assert data["purpose"] == "Eidos deliberative mission-contract layer powered by ASMP"
    assert data["should_invoke_oracle"] is True
    assert "approval_boundaries" in data
    assert "do not execute the mission from Oracle" in data["approval_boundaries"]
    assert data["evidence_required"]


def test_eidos_oracle_uses_asmp_candidates(monkeypatch):
    asmp = load_asmp()
    services = [
        {
            "name": "identity-admin",
            "description": "Owns Microsoft Entra and SSO setup",
            "capabilities": {"provides": ["identity.sso", "microsoft.entra"]},
            "status": "registered",
        },
        {
            "name": "security-review",
            "description": "Reviews credential risk and least privilege",
            "capabilities": {"provides": ["security.risk", "credential.review"]},
            "status": "registered",
        },
    ]
    monkeypatch.setattr(asmp, "request", lambda *_args, **_kwargs: services)

    data = run_json(asmp, "oracle", "should we approve this Microsoft SSO credential risk?")

    assert data["product"] == "Eidos Oracle"
    assert data["registry_state"] == "registry_ok"
    assert data["should_invoke_oracle"] is True
    assert data["primary_owner"] == "security-review"
    assert {candidate["name"] for candidate in data["candidate_services"]} >= {
        "identity-admin",
        "security-review",
    }
    roles = {role["role"] for role in data["role_hypotheses"]}
    assert "it" in roles
    assert "security" in roles
    assert "finance" not in roles


def test_eidos_oracle_adapts_to_greenmark_scope_for_books_question(monkeypatch):
    asmp = load_asmp()
    services = [
        {
            "name": "greenmark-penny",
            "description": "Owns Greenmark accounting intelligence and book-backed vendor inference",
            "capabilities": {
                "provides": [
                    "greenmark.accounting.answer",
                    "greenmark.accounting.ap-vendor-investigation",
                ]
            },
            "status": "registered",
        },
        {
            "name": "greenmark-cypher",
            "description": "Owns Greenmark IT operations, MSP routing, and provenance-backed admin paths",
            "capabilities": {
                "provides": [
                    "greenmark.it.operations",
                    "greenmark.it.msp-routing",
                ]
            },
            "status": "registered",
        },
    ]
    monkeypatch.setattr(asmp, "request", lambda *_args, **_kwargs: services)

    data = run_json(asmp, "oracle", "what do the books imply about this IT vendor?")

    assert data["product"] == "Eidos Oracle"
    assert data["registry_state"] == "registry_ok"
    assert data["primary_owner"] == "greenmark-penny"
    assert [role["role"] for role in data["role_hypotheses"][:2]] == ["finance", "it"]
    assert data["supporting_roles"] == ["it"]
    assert {candidate["name"] for candidate in data["candidate_services"]} >= {
        "greenmark-penny",
        "greenmark-cypher",
    }
