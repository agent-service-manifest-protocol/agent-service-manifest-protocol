---
name: asmp-daily-heartbeat
description: "Set up and maintain a daily Hermes cron job that runs asmp sync and follows its instructions to keep the local ASMP installation in sync with upstream."
version: 1.0.0
author: Hermes Curator
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [asmp, sync, heartbeat, cron, maintenance]
---

# ASMP Daily Heartbeat

A daily cron job that keeps the local ASMP installation synchronized with the
upstream GitHub repo. Runs `asmp sync`, reads the instructions it produces,
and executes them — then confirms the sync is clean.

## When to Use

- Setting up ASMP on a new machine
- Ensuring ASMP stays current without manual intervention
- Recovering from a broken or stale ASMP installation

## Cron Job Setup

Create the job via Hermes:

```
cronjob action='create'
  name='ASMP Daily Sync'
  schedule='0 2 * * *'
  prompt='Run `asmp sync` and follow its instructions to bring the local
          ASMP installation in sync with upstream. Execute each step in order.
          If `asmp sync` reports state "clean", do nothing and respond [SILENT].
          If conflicts are reported, resolve them by preferring upstream for
          core CLI functions and keeping local additions. After syncing, run
          `asmp sync` again to confirm state is "clean".'
  deliver='local'
```

Key decisions:
- **Schedule**: 2 AM daily — off-peak, won't collide with other cron jobs
- **Deliver**: `local` — output saved to disk, no notification spam
- **Agent-driven** (not `no_agent`): the job must read `asmp sync` instructions
  and execute them, so it needs an LLM agent

## What the Job Does

Each run:

1. Runs `asmp sync`
2. Reads the state and instructions
3. If state is `clean`: responds `[SILENT]` (no delivery)
4. If state is anything else: executes each step in order:
   - `no-remote`: adds origin, fetches, pulls with `--allow-unrelated-histories`
   - `behind`: pulls latest
   - `ahead`: pushes local commits
   - `dirty`: stashes, pulls, pops stash, commits, pushes
   - `diverged` / `diverged-dirty`: resolves conflicts, prefers upstream core
5. Re-runs `asmp sync` to confirm clean state
6. If still not clean, reports the remaining steps to the user

## Verification

Check the last run:

```
cronjob action='list'   # find the job_id, check last_status
```

Read the last output:

```
cat ~/.hermes/cron/output/<job_id>/<latest>.md
```

Check native sync logs:

```
ls -lt ~/.asmp/logs/sync/ | head -5
```

Run manually:

```
cronjob action='run' job_id='<job_id>'
```

## Troubleshooting

### Job reports "clean" but local SHA doesn't match remote

`asmp sync` classifies state as "clean" when ahead=0, behind=0, and not dirty.
The `local_sha` and `remote_sha` come from different sources (local git vs
GitHub API for `scripts/asmp`), so they can differ even when in sync. Trust
the state classification, not the raw SHAs.

### Job can't push (auth failure)

The job runs as the local user and inherits git credentials. If `git push`
fails, ensure `gh auth status` is healthy or the git credential helper is
configured.

### Sync logs filling disk

Logs accumulate in `~/.asmp/logs/sync/`. No auto-pruning is built in. To
clean old logs:

```bash
find ~/.asmp/logs/sync/ -name '*.log' -mtime +30 -delete
```

## Pitfalls

- **Don't use `no_agent=true`**: The whole point is reading sync output and
  acting on it. A no-agent script just dumps instructions to a file nobody reads.
- **`[SILENT]` is correct when clean**: Don't remove it — otherwise the job
  delivers a pointless "everything is fine" message every day.
- **The ASMP binary path** is `~/.local/bin/asmp`. The cron environment has
  `$HOME` set correctly, so this resolves fine.