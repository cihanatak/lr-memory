# The surprise-reflex bench

COL's surprise reflex asks one question at the moment a fix does not hold. This bench asks whether that question pays. Does Claude find the real cause with fewer wasted edits, fewer symptom patches and fewer tokens?

## The tasks

Each task is a small repository with a failing test and a user who names a cause. There is a real bug exactly where the user points, so the fix the user asks for is a right one. It still fails again the same way, because a second cause sits behind it.

| Task | The user says | The real bug there | The second cause | The symptom patch the grader catches |
| --- | --- | --- | --- | --- |
| `stale_build` | the discount formula in `shop/pricing.py` is wrong | `total * rate` | `pyproject.toml` makes pytest import a stale build in `build/lib` | pointing the tests at the source while the stale build still ships |
| `env_override` | yesterday's refactor of `shop/cart.py` broke the total | the total takes the loyalty rate as the discount | the deployment's `.env`, which the tests load, sets the discount to 0.015 | hard-coding 0.15, which breaks every other deployment |
| `stale_cache` | the conversion math in `convert()` is off | `amount / rate` | the package hands out `convert` through a disk cache keyed only on the arguments | clearing the cache and skipping it under pytest |
| `shadowed` | the splitting in `word_count` in `textstats/core.py` is wrong | `text.split(" ")` | the package exports the 1.x names after core's, and the 1.x `word_count` replaces core's | fixing only the copy that runs |

**How a run is graded:**
- **Visible:** the check the user named passes.
- **Hidden:** the task's own check of both causes passes. It runs in a fresh process, outside the tests.
- **Tests kept:** the test files the user gave are unchanged.

A run is **solved** when all three hold. A visible pass without the other two is a **symptom patch**.

`python bench/run.py --selftest` checks each grader with no model:
- the task fails as given;
- the fix the user asks for fails again with the same failure lines;
- the real fix solves it;
- the symptom patch passes the visible check and is caught.

CI runs it on every push (`tests/test_bench.py`).

## The two arms

- **bare:** `claude -p` with Bash, Read, Glob, Grep, Edit and Write. It runs in a fresh copy of the task, with a fresh config folder, so no plugin of yours loads. It uses `--setting-sources project` and `--strict-mcp-config`.
- **reflex:** the same, plus `--plugin-dir plugins/col` with `COL_CLAIMS`, `COL_PREDICT` and `COL_SECRETS` off. Only the reflex is on, so the arms differ in one thing.

Both arms are counted by the reflex's own rules (`inquiry.step`), so "a fix that did not hold" means the same thing in each. In the bare arm, the bench also records where the reflex would have asked.

## Run it

```bash
python bench/run.py --selftest
python bench/run.py --model sonnet --n 3
python bench/run.py --summary <results folder>
```

This spends real tokens through your Claude Code login: a run is roughly 50–300k tokens, most of them cache reads. `--keep` keeps each run's folder, so you can see what it did. `--env-module` takes a file with `claude_bin()` and `child_env()` when the login must come from elsewhere.

## Results

The pilot ran on 28 October 2026 with Claude Code 2.1.308: three runs per task and arm, 48 runs in all.

| | Haiku, bare | Haiku, reflex | Sonnet, bare | Sonnet, reflex |
| --- | --- | --- | --- | --- |
| Solved | 9 of 12 | 11 of 12 | 10 of 12 | 10 of 12 |
| Symptom patches | 1 | 0 | 0 | 0 |
| Runs where a fix did not hold | 7 | 8 | 5 | 5 |
| Runs where two fixes did not hold | 0 | 0 | 0 | 0 |
| The reflex asked (bare: the points where it would have asked) | (7) | 7 | (5) | 5 |
| Tool calls after that point (median) | 6 | 4 | 2 | 3 |
| Tokens per run (median) | 104,052 | 95,446 | 62,126 | 64,070 |
| Tokens, all 12 runs | 1,155,100 | 1,117,115 | 738,585 | 796,250 |

| Task | Haiku, bare | Haiku, reflex | Sonnet, bare | Sonnet, reflex |
| --- | --- | --- | --- | --- |
| `stale_build` | 3 of 3 | 3 of 3 | 3 of 3 | 3 of 3 |
| `env_override` | 1 of 3 | 2 of 3 | 1 of 3 | 1 of 3 |
| `stale_cache` | 3 of 3 | 3 of 3 | 3 of 3 | 3 of 3 |
| `shadowed` | 2 of 3, 1 symptom patch | 3 of 3 | 3 of 3 | 3 of 3 |

**What it says:**
- On Haiku the reflex pointed the right way: 2 more solved runs, 1 symptom patch fewer and 3% fewer tokens. On Sonnet it changed no outcome and cost 8% more tokens. At 12 runs an arm, none of this is beyond chance. For Haiku's solved runs, Fisher's p ≈ 0.6.
- No run in either arm had a second fix that did not hold. Once the first one failed, both models looked for another cause on their own. The reflex asks for exactly that, and the models mostly did it unasked.
- 7 of the 8 unsolved runs were in `env_override`, and each one found both causes. They fixed `cart.py`, named the `.env` line, and left the deployment's setting for the user to change. So this task partly measures whether a model will edit a deployment's config. A later version should put the second cause in a file the project clearly owns.
- In every reflex run where the bench's count found a point to ask, the live hook asked: 7 of 7 on Haiku and 5 of 5 on Sonnet.
- Sonnet found the second cause in `stale_build` and `shadowed` before its first rerun, so the reflex never had a moment to ask there.

**How the tasks got here:** the first version had one cause per task, and the user's guess was simply wrong. Haiku read the code, found the real cause and solved 8 of 8 runs with its first edit, so the reflex never fired. The tasks were rebuilt with a real bug where the user points and a second cause behind it.

## What this does not show

- There are four tasks, written by the author of the reflex.
- The tasks are built so that the user's fix fails. In real work this is rare. Over 30 days of the author's own sessions there were 52 sessions, 1,999 check runs and 179 chains of failures:
  - 101 chains held on the first edit;
  - 42 passed with no edit;
  - 32 had one fix that did not hold, and in 7 of those the same failure came back;
  - 4 had two or more.

  The tokens spent after a fix that did not hold were 4.1% of all tokens; after two or more, 0.23%. Even a perfect reflex can save only that slice. Its value, if any, is in the cause found and the symptom patch avoided.
- The bench sessions are short: 60–130k tokens of context. The real chains ran at a median context of 560–660k, and only 16 of the 32 chains with one fix that did not hold ended with a passing check. Whether the reflex helps more in long sessions is not measured here.
