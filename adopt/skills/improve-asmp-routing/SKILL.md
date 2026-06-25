---
name: improve-asmp-routing
description: >
  Use when improving ASMP natural-language discovery, owner selection, routing
  boundaries, manifest examples, /ask responses, or policy files after a real
  agent misroutes a task.
---

# Improve ASMP Routing

Use this skill when ASMP finds plausible services but chooses the wrong owner,
when a user says the registry should know where a task belongs, or when a real
workflow teaches a new decision boundary.

## What We Learned

ASMP should not try to be the brain. It should be the host-level service
interconnect and discovery substrate:

- manifests describe services and expose evidence;
- retrieval finds candidates;
- local policy resolves close ownership boundaries;
- memory/wiki systems keep broader lessons and narrative context.

The pattern came from a Greenmark/Cerebro experiment where simple retrieval
confused adjacent services:

- Cerebro app shipment vs DD5 data shipment;
- data operating health vs data publication;
- general Cerebro routing vs Cerebro design;
- browser proof vs independent QA mission;
- scorecard model work vs data-plane health;
- email workflows vs data operating checks.

The fix was not a giant prompt. The fix was better manifests plus a small
external boundary policy.

## Evidence That Motivated The Pattern

In the Greenmark testbed, a local ASMP registry combined keyword, BM25-style
lexical search, a cheap dense-like signal, and reciprocal rank fusion. Top-3
retrieval was usually strong, but top-1 could be wrong when service names shared
terms such as "Cerebro", "ship", "data", "proof", or "scorecard".

Adding these helped:

- `owns`
- `supports`
- `aliases`
- `anti_routes`
- `positive_examples`
- `negative_examples`
- `when_not_to_use`

Adding an external routing policy helped more. The `/ask` response became useful
only when it returned not just ranked services, but:

- `owner`
- `confidence`
- `runner_up`
- `rule_hits`
- `alternates`
- evidence docs or manifest evidence

Do not overclaim generated evaluations. A 500-question synthetic corpus is a
smoke test. Real quality comes from a small, human-written boundary corpus and
production misroute corrections.

## Routing Model

Use this model:

1. Search registered manifests.
2. Rank candidates with whatever methods the host supports.
3. Prefer `owns` over `supports`; prefer both over generic `provides`.
4. Use aliases and positive examples as evidence.
5. Use anti-routes and negative examples as penalties and handoff hints.
6. If top candidates are close, apply an external boundary policy.
7. Return owner, confidence, runner-up, rule hits, and alternates.
8. If confidence remains low, abstain or ask for clarification rather than
   pretending certainty.

## Boundary Policy Shape

Keep local judgment outside the lean manifest:

```yaml
asmp_policy: "0.1"
name: routing-policy
defaults:
  boundary_win_bonus: 0.12
  boundary_margin: 0.04
  high_confidence_margin: 0.08
boundaries:
  - name: application release vs data publication
    services: [app-shipper, data-shipper]
    phrases:
      app-shipper:
        - deploy app
        - production release
      data-shipper:
        - publish data
        - publication batch
        - warehouse parity
```

Policy files are host or organization assets. They are allowed to be local,
opinionated, and learned over time.

## What To Change

When fixing a misroute, prefer this order:

1. Add or correct `owns`, `supports`, and aliases in the service manifest.
2. Add positive and negative examples with handoffs.
3. Add a boundary rule only if two services are repeatedly confused.
4. Add a human-written eval case for the exact boundary.
5. Regenerate/search the index.
6. Re-run smoke tests and the boundary eval.

Avoid adding vague words that match everything, such as "system", "data",
"agent", or a product name by itself. Multi-word phrases are safer.

## Anti-Patterns

Avoid:

- hiding learned corrections in chat history;
- turning ASMP into a business-domain ontology;
- stuffing all local policy into every service manifest;
- trusting top-1 retrieval without evidence;
- treating anti-routes as semantic opposites;
- optimizing only against generated questions;
- returning a confident owner without a runner-up and reason.

## Test Checklist

For a routing improvement, prove:

- the service manifests still parse;
- `/ask` returns an `owner` and `confidence`;
- the corrected query picks the intended owner;
- the runner-up is sensible;
- rule hits explain the boundary when policy was used;
- known adjacent boundaries did not regress;
- generated smoke tests pass;
- a small hand-written boundary eval passes.

## Closeout

Report:

- the misroute or gap observed;
- the manifest or policy change made;
- before/after owner and confidence;
- eval results;
- any remaining low-confidence boundaries.
