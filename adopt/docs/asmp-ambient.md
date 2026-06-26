# ASMP Ambient MVP

ASMP Ambient is a tiny lifecycle-context shim for agent hosts.

It helps an agent remember one thing at the right moment:

> Before guessing tools, ports, repos, owners, or service boundaries, ask the ASMP registry.

It is not memory, not a catalog dump, and not a hidden decision-maker. It emits a small routing compass that points back to ASMP manifests and the local registry.

Ambient also tells agents that **Eidos Oracle** exists. Oracle is not ASMP and
does not replace deterministic routing. It is the Eidos mission-contract layer to
call when ASMP routing alone is ambiguous, cross-role, high-stakes, or
low-confidence:

```bash
scripts/asmp oracle "who should answer this and what evidence counts?"
```

Oracle plans; specialists execute; humans approve risky action.

## MVP Command

```bash
scripts/asmp ambient --event SessionStart
scripts/asmp ambient --event UserPromptSubmit --prompt "which service owns browser validation?"
scripts/asmp ambient --event SubagentStart --parent-used-asmp
```

Use JSON for host adapters:

```bash
scripts/asmp --json ambient --event UserPromptSubmit --prompt "wire this MCP service into ASMP"
```

## Events

`SessionStart` emits a static ASMP orientation card. It does not query the whole registry.

`UserPromptSubmit` emits nothing for ordinary prompts. For service-discovery prompts, it queries the local registry and returns up to three redacted candidate service cards.

`SubagentStart` emits a smaller contract card only when the parent task used ASMP or the subagent scope is clearly service/routing related.

## Caps

- `SessionStart`: 1.5 KB
- `UserPromptSubmit`: 2 KB
- `SubagentStart`: 1 KB
- Total ASMP Ambient context: 2.5 KB
- Candidate services: 3
- Candidate summary: 180 characters

If the payload cannot fit, Ambient degrades by dropping low-value detail. If it still cannot fit, it injects nothing and explains why.

## Privacy

Ambient redacts secret-like material before emitting context:

- bearer tokens
- API keys
- password/secret/token env values
- credential-bearing URLs
- sensitive manifest keys such as `auth`, `cookie`, `credential`, `private`, `password`, `secret`, or `token`

Ambient must never emit raw manifests, private content, raw database rows, customer data, or credential-bearing URLs.

## Off Switch

Disable Ambient for a shell/session:

```bash
ASMP_AMBIENT=off scripts/asmp ambient --event SessionStart
```

Disable Ambient in a prompt:

```text
do not use ASMP
```

The user override wins.

## Host Integration Shape

Agent hosts should call the command at lifecycle boundaries and inject the returned `context` only when `injected` is true.

The host should prefer JSON mode:

```json
{
  "event": "UserPromptSubmit",
  "injected": true,
  "reason": "ok",
  "bytes": 812,
  "candidates": [],
  "context": "<asmp-context-shim hidden=\"true\" version=\"0.1\">..."
}
```

## Host Adapter Contract

Host adapters are optional consumers of Ambient. Codex, Eidos CLI, Cerebro, and
other agent hosts may call Ambient, but none of them is the canonical home of
ASMP, Ambient, or Eidos Oracle.

The adapter contract is:

- call Ambient at host lifecycle boundaries;
- inject only the bounded `context` returned by JSON mode;
- treat Eidos Oracle as advisory mission-contract help, never as an executor;
- keep specialist agents and human approvers as the authority for scoped or
  risky work.

Canonical flow:

```text
ASMP registry/router -> Ambient hint -> Eidos Oracle mission contract
  -> specialist role -> human approval when risk requires it
```

## Tests

```bash
python3 -m pytest tests/test_asmp_ambient.py -q
scripts/asmp --json ambient --event SessionStart
scripts/asmp --json ambient --event UserPromptSubmit --prompt "which service owns browser validation?"
```
