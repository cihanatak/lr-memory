---
name: panel
description: Shows the mind panel, one local page for LR Memory, COL and scnc built from the user's own logs, transcripts and memory files. Use when the user asks to see the mind panel, the dashboard of the memory and checking layer, or "zihin paneli", "paneli aç", "show the mind panel".
---

# Mind panel

Run this:

```
sh "${CLAUDE_PLUGIN_ROOT}/scripts/run.sh" --open
```

It prints the path of the page it wrote (by default `~/.claude/mind/panel.html`) and opens it. Tell the user that
path. The first run reads every transcript and can take minutes; later runs read only what changed.

Options: `--lang en|tr`, `--config FILE`, `--scorecard FILE`, `--no-transcripts`, `--json` (print the data instead),
`--serve PORT` (a page on 127.0.0.1 that refreshes every minute; stop it when done).

Do not describe numbers the page does not show. A metric marked missing, not measured or blind is exactly that.
