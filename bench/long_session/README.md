# The long-session bench

LR Memory's README made two claims about long sessions:
- a smaller auto-compact window makes each turn cheaper;
- the working note makes the extra compactions safe.

This bench tests both on one scripted job of ten messages. It also asks whether the record helps the session that comes the next day. [DESIGN.md](DESIGN.md) is the plan as written before any run, predictions included.

## The job

**The repository.** `ledgerly` is a small bookkeeping library for a chain of shops; `repo.py` writes it from fixed seeds. It has:
- 13 modules and about 2.6k lines of code and tests (483 tests);
- a design document and migrations;
- a timing tool that models production;
- a nightly import log of 2.6k lines.

**The messages.** The user ships version 0.9 in ten messages (`script.py`), sent one at a time, each when the previous turn has ended:
1. The rules and an eight-item list; start with item 1. The rules hold for the whole session:
   - never touch `migrations/`;
   - one commit per item, with the prefix `ledgerly 0.9:`;
   - new error messages in Turkish, with the old English ones left alone;
   - no renames in `api.py`.
2. Item 2: books at a reduced VAT rate of 8%.
3. A correction: books are at 7%, because finance changed the rate. Then item 3, a CSV export with `;` and a header row.
4. Run the timing tool and keep its p50 as the day's baseline. Then item 4: rates cached per day, unknown currencies refused.
5. Item 5: find and fix the cause of the duplicate entries in the import log.
6. Item 6: a monthly summary per account, run against the staging database `ledgerly_stg_2`. The docs name a different one.
7. Revert item 3 and keep everything else.
8. Item 7: `GET /accounts/{id}/balance`.
9. Item 8, the changelog; then the timing tool again, compared with the morning's baseline.
10. Wrap up: each item with its commit, and anything left undone.

Each message after the first leans on something said earlier: a rule, a number, a correction or a commit. That is what a compaction can lose.

## The arms

| Arm | Auto-compact window | LR Memory |
| --- | --- | --- |
| A | 1M, never reached in this job | no |
| B | 100k | no |
| C | 100k | `--plugin-dir plugins/lr-memory` |

**Shared by all three:**
- Sonnet 5.5 with its 1M context, through `claude -p` and Claude Code 2.1.308.
- Bash, Read, Edit, Write, Glob, Grep, the task tools and the Skill tool. No web, no MCP, no subagents.
- A fresh copy of the repository, an empty config folder, `--setting-sources project` and a git identity of its own.

**Two details:**
- Claude Code compacts well before the window. At 100k it compacted at about 67k.
- In arm C, LR Memory's background passes are off. Its sleep pass would start a `claude -p` of its own, outside the run's count.

## Grading

There are 16 checks, all mechanical. The items, R3, R4 and F4 run in a fresh process (`hidden.py`) and call the code the way another service would. They check what the code does, not how it was built.

| Check | Passes when |
| --- | --- |
| I1 | invoice totals round half-even: 10.125 to 10.12 and 10.135 to 10.14 |
| I2 | books are at 7%, and no other rate moved |
| I3 | the export is back to its old format, and a commit in the history had the `;` export with a header |
| I4 | rates are fetched once per day and currency, and an unknown code raises |
| I5 | a batch that times out after three rows and is read again stores each of its five rows once |
| I6 | the monthly summary totals the month's entries per account |
| I7 | the balance endpoint answers the account and its balance with two decimals |
| I8 | the changelog has a 0.9 section with at least four entries |
| R1 | nothing under `migrations/` changed, in any commit or on disk |
| R2 | at least eight commits carry the prefix, and every other commit is a revert |
| R3 | the new error messages are Turkish (at least one exists), and the old English ones are unchanged |
| R4 | every name other services import from `api.py` is still there |
| F1 | the answer to message 9 gives the morning's baseline, 25.9 ms |
| F2 | the answer to message 10 names at least seven item commits by hash |
| F3 | that answer says item 3 was reverted |
| F4 | the reports run against `ledgerly_stg_2` |

**The next session.** After each long run, two fresh sessions get three questions about it: one with LR Memory and one without. Each runs in its own copy of the run's config folder and repository. The questions:
- What was the baseline p50? Graded by the number.
- Why did books end up at 7%? Only the user said it: finance changed the rate. Graded by the word "finance".
- Which commit reverted the CSV change? Graded by its hash.

LR Memory adds no note when a session starts. What it gives the next session is the recall skill, a search over the transcripts in the config folder.

**Measured, not graded:**
- tokens by kind;
- model calls and compactions;
- the peak context and the context right after each compaction;
- files read again after a compaction.

A compaction's own model call is not in the session's usage, so it is counted as the context it read plus the context it left.

**The selftest:** `python bench/long_session/run.py --selftest` checks every grader with no model:
- the job as given fails 14 of the 16 checks;
- a scripted session that does everything right passes all 16;
- four faulty variants each fail only their own check: one keeps the 8% rate, one adds a migration, one gives a wrong baseline and one never reverts.

CI runs it on every push (`tests/test_long_session.py`).

## Run it

```bash
python bench/long_session/run.py --selftest
python bench/long_session/run.py --pilot --env-module <file>
python bench/long_session/run.py --n 3 --env-module <file>
python bench/long_session/run.py --summary <results folder>
```

**Before you run it:**
- Each run starts from an empty config folder, so the login must come in the environment. Pass `--env-module`: a file with `claude_bin()` and `child_env()`, as in the surprise-reflex bench.
- This spends real tokens through your login: a full run is a few million, most of them cache reads.
- `--keep` keeps each run's folder.

## Results

**The runs:**
- 28 October 2026, Claude Code 2.1.308, Sonnet 5.5 with its 1M context.
- Three runs per arm, each followed by two next sessions.
- 28.7M tokens in all:
  - 3.4M for the pilot;
  - 25.3M for the main runs, of which 1.0M went to the next sessions.

| | A: 1M window | B: 100k | C: 100k, LR Memory |
| --- | --- | --- | --- |
| Checks passed | 16 of 16 in every run | 16 of 16 in every run | 16 of 16 in every run |
| Tokens per run (median) | 3,262,503 | 2,351,895 | 2,386,656 |
| Tokens, all 3 runs | 9,745,000 | 7,404,190 | 7,136,355 |
| Fewer tokens than A, all 3 runs | | 24% | 27% |
| Model calls per run (median) | 50 | 48 | 56 |
| Compactions per run | 0, 0, 0 | 1, 2, 1 | 2, 1, 1 |
| Peak context (median) | 95,600 | 66,894 | 66,644 |
| Context right after a compaction | | 23–28k | 25–31k |
| Files read again after a compaction | | 0 | 0 |
| Cache reads, share of tokens | 97% | 91% | 91% |
| Time per run (median) | 271 s | 305 s | 305 s |

**The next session.** There were 9 sessions with LR Memory and 9 without. Each pair asked about the same long run.

| | With LR Memory | Without |
| --- | --- | --- |
| The morning's baseline p50 | 9 of 9 | 1 of 9 |
| Why books are at 7% | 9 of 9 | 0 of 9 |
| The commit that reverted the CSV change | 9 of 9 | 9 of 9 |
| Tokens per session (median) | 49,371 | 48,728 |

**What it says:**
- **A smaller window saved about a quarter of the tokens and lost nothing.**
  - B and C used 24% and 27% fewer tokens than A.
  - All six small-window runs used fewer tokens than every 1M run (by rank, p ≈ 0.02).
  - Each of the six passed all 16 checks after one or two compactions, including the rules and facts from early messages.
  - No file was read again after a compaction.
- **The working note made no measurable difference here.**
  - Over the three runs, C used 3.6% fewer tokens than B (1.5% more by median), and both passed every check.
  - Claude Code's own summary was enough for this job. So the claim that the note makes compactions safe is neither supported nor refuted.
- **The search carried the session over to the next day.**
  - Every session with LR Memory called the recall skill first and answered all three questions. It cost about as much as a session without it: 49,371 tokens against 48,728 by median.
  - Without LR Memory, the next session found the revert in git every time.
  - It could not tell the baseline in 8 of 9 sessions, and said so. In all 9 it said the repository does not record why books are at 7%. None made an answer up.
  - The ninth rebuilt the baseline itself: it checked out the commit before item 4 and ran the timing tool again.
  - LR Memory came out ahead in every pair (sign test, p ≈ 0.004).
- **Against the predictions in DESIGN.md:**
  - **Tokens:** the prediction was 25–45% fewer. B used 24% fewer and C 27% fewer by the totals; by median, 28% and 27%. That is the low end.
  - **Tokens, C against B:** within ±10%, as predicted.
  - **Quality:** A at least as good as B, and C − B between −1 and +2. Both held, at the ceiling.
  - **Next session with LR Memory:** 3 of 3, as predicted.
  - **Next session without LR Memory:** 2 of 3 was predicted, but it was 1 of 3 in 8 of 9 sessions. The baseline was lost, not only the reason.
  - **Length:** the job was about half as long as planned.
    - A peaked at 84–103k over about 50 calls; the plan was 200–250k over 80.
    - B and C compacted once or twice; the plan was 3–5 times.
    - The cost was 28.7M tokens against the 85M planned.

## What this does not show

- It is one synthetic job and one model, with three runs per arm, written by the plugin's author.
- **The job was easy.** Every run passed every check, so a difference in quality could not show. A harder job, a weaker model or more compactions per run could separate B from C.
- **The sessions were short.** A peaked at about 95k tokens of context, while the author's own sessions run at a median of 504k per call.
  - The saving from a smaller window grows with the length of the session. The replay of the author's month in DESIGN.md gives 52% at a 400k window.
  - That replay counts no redone work and no lost quality.
- **The setup was light.** The first call here was 14k tokens; the author's is 79k. At 100k, Claude Code compacts at about 67k, so a heavy setup leaves little room under a small window.
- **The next session's questions favour the search.** Two of them ask what the user said: a number and a reason. The search finds that and git does not. The revert, which git keeps, was found either way.
