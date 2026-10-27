---
name: report
description: Shows COL's record from its local logs - how many finished turns the claim check looked at, flagged and blocked, and whether the blocks turned out right; how the measurable predictions turned out (held, missed, which way the misses went, what still waits for a result); and what the key scan stopped before a commit or a push. Use when the user asks for COL's report, record or calibration, how good the predictions have been, whether COL is doing anything useful, or what it has blocked, for example "COL report", "how calibrated are your predictions", "COL raporu", "öngörüler nasıl gidiyor".
---

# COL report

Run this and show the user what it prints:

```bash
sh "${CLAUDE_PLUGIN_ROOT}/scripts/run.sh" report
```

It covers the last 30 days; add `--days 7` for the last week. The report reads COL's own logs on this machine and
asks no model.

Answer in the user's language and keep it short: the numbers first, then the recent misses if there are any. Do not
edit or delete the logs.
