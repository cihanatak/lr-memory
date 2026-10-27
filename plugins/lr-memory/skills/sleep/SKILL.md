---
name: sleep
description: Run LR Memory's sleep pass now. It reads what the user said in each project since the last pass, writes their standing rules and corrections as memory files that every later session loads, and lets lessons drawn from what happened wait until a later pass backs them with new evidence. It costs model tokens (one claude -p call per project with new messages), so it runs only when the user invokes it.
disable-model-invocation: true
---

# Sleep

Run the pass, then relay its report:

```bash
sh "${CLAUDE_PLUGIN_ROOT}/scripts/run.sh" sleep
```

- Give the call a timeout of 600000 ms. Each project with new messages takes one model call, usually under a minute.
- Pass on what the user asked for:
  - `--dry-run` shows what would be written and writes nothing.
  - `--hours 48` reads further back than the last pass.
  - `--project <name>` limits the pass to one project. The name is its folder under `~/.claude/projects`, or the end of it, such as `my-app`.
- Tell the user briefly, in their language:
  - what was written to memory, and why;
  - which lessons wait as candidates;
  - what was rejected;
  - the cost in tokens.

  The report is saved, and its path is on its last line.
- If the report says the claude command is not signed in, pass on what it says to do. Sleep starts its own `claude`, which cannot use this session's login.
- Do not edit memory files yourself in this step. The pass has written what held up, and the rest is in the report.
