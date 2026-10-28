# Long-session bench: design

Status: this is the design as written before any run, predictions included. What changed while it was built is listed at the end, and the results are in README.md.

## The question

LR Memory's README says a smaller auto-compact window makes each turn cheaper, and that the working note makes the extra compactions safe. This bench tests both halves on one long, scripted job:
- How many tokens does the smaller window save?
- What does it cost in quality, and does the note win that back?

A second phase asks whether the record helps the next session.

## What the author's own sessions say

These figures come from a read-only pass over 30 days of transcripts (28 September – 28 October 2026). It made no model calls.

- 32 long sessions, 32,789 model calls, 17.0 billion tokens; 96% of the calls were Opus 5.5.
- Context per call: median 504k. 82% of all tokens went to calls above 400k.
- Before 26 October, compactions came at a median of 968k (the 1M window). After the window was set to 400k, they came at a median of 373k.
- Right after a compaction, the context was 106k (median). The first call of a session was already 79k: the system prompt, tools, skills and memory index. That base is re-read on every call, about 15% of all tokens.
- **Replay:** the same calls under a smaller window, assuming:
  - the context grows by the same steps;
  - a compaction reads the context once and writes 10k tokens;
  - the context then drops to 106k;
  - no work is redone after a compaction.

  Result: a 400k window saves 52% of the tokens and a 200k window saves 70%. A 100k window is impossible here, because the context after a compaction is already above it.
- **Claude Code's own summary** already has sections for all user messages, files and code, and pending tasks; its median length is 18k characters. Between two compactions there were a median of 5 user messages (2 after the window was lowered). The note keeps the last 8 word for word. For the note to matter, it has to add something the summary drops.

The replay is an upper bound: it counts no redone work and no lost quality. The bench measures those.

## Arms

Same model, tools, repository and messages. Only the window and the plugin differ.

| Arm | Window | LR Memory |
| --- | --- | --- |
| A | `--autocompact 1M`, never reached in this job | no |
| B | `--autocompact W` | no |
| C | `--autocompact W` | `--plugin-dir plugins/lr-memory` |

**W is fixed after the pilot.** The aim is for the context right after a compaction to be a third to a half of W, as in the author's sessions at 200–400k. The expected value is 100k, Claude Code's smallest.

**Settings shared by all arms:**
- Model: `claude-sonnet-5-5[1m]`.
- Tools: Bash, Read, Edit, Write, Glob, Grep and the task list. No web, no MCP, no subagents.
- Each run gets a fresh copy of the repository, a fresh `CLAUDE_CONFIG_DIR` and `--setting-sources project`.
- Session persistence stays on, because the note is made from the transcript.
- The user's messages go in through `--input-format stream-json`. Each is sent when the previous turn ends.

## The job: "ledgerly 0.9"

**The repository** is synthetic:
- a small bookkeeping library, about 12 modules and 4–6k lines, with tests;
- a design document;
- an import log of about 3k lines;
- `tools/bench.py`, which prints a deterministic timing figure;
- `migrations/`.

**The messages.** There are ten, fixed in advance; they never react to what the model did.
1. The rules and an eight-item release list; start with item 1. The rules:
   - never edit `migrations/`, it is applied in production;
   - one commit per item, with the message `ledgerly 0.9: <item>`;
   - user-facing error messages in Turkish;
   - no renames in `ledgerly/api.py`.
2. Item 2: a reduced 8% rate for books.
3. A correction: finance changed the books rate to 7%. Then item 3.
4. Before item 4, run `tools/bench.py` and report the p50; it is the baseline.
5. Item 5: the import log shows duplicate entries; find out why and fix it.
6. Item 6. The staging database for reports is `ledgerly_stg_2`, not the one the docs name.
7. Product changed its mind on item 3: revert its commit, keep everything else.
8. Item 7.
9. Item 8, then run `tools/bench.py` again: the p50 now against the baseline.
10. Wrap up: each item with its commit, and anything left undone.

In arm A the context should reach 200–250k over about 80 calls. Arms B and C should compact 3–5 times.

## Grading

Everything is graded mechanically after the session. There are 16 checks.

**Items:**
- hidden tests, run in a fresh process, for items 1, 2 (at 7%), 4, 5, 6 and 7;
- item 3 reverted, with the other items intact;
- the changelog (item 8).

**Rules:**
- `migrations/` untouched in every commit;
- one commit per item, with the prefix;
- two error paths that answer in Turkish;
- every public name in `api.py` still importable.

**Facts:**
- the staging database name in the reports config;
- the baseline p50 in the answer to message 9;
- at least 7 of 8 items mapped to the right commit in the answer to message 10;
- item 3 named as reverted.

**Process** (measured, not graded):
- tokens by kind, model calls, compactions;
- the calls and tokens in the ten calls after each compaction;
- files read again after a compaction.

**Selftest:** `--selftest` checks every grader with no model. A scripted perfect run passes all 16 checks. Each faulty variant fails exactly its own check:
- one that keeps the 8% rate;
- one that touches a migration;
- one that reports a wrong baseline;
- one that skips the revert.

## Phase 2: the next session

After each long run, a fresh session in the same config asks three questions about the last session:
- What was the baseline p50? The record has it; checking out the old commit and rerunning the bench recomputes it.
- Why did the books rate change? Only the record has this.
- Which commit reverted the CSV change? The repository has this.

Each question session runs twice, with LR Memory and without. It is graded on the three answers and the tokens spent.

## Runs and cost

| Step | What it settles | Tokens |
| --- | --- | --- |
| Pilot: messages 1–5, once in B and once in C | Compaction happens under `-p`; the note lands; the context after a compaction; calls per message; W | ~5M |
| Main: 3 runs per arm | the results | A ~10M a run; B and C ~6–7M a run with the redone work; ~75M in all |
| Phase 2: 18 short sessions | recall across sessions | ~4M |

**In all:** about 85M tokens, likely between 60M and 110M; about 95% of them cache reads. Running one job per arm at a time, the main runs take about 1.5–2 hours.

**Stop rule:** if the pilot puts the estimate off by more than half, stop and report before the main runs.

## Predictions, written before any run

- **Tokens:** B and C use 25–45% fewer than A. C is within ±10% of B.
- **Quality:** A scores at least as well as B. C minus B lies between −1 and +2 checks per run, out of 16. A gain is not predicted: Claude Code's own summary already keeps the user's messages.
- **Phase 2:** with LR Memory, 3 of 3 answers right; without it, 2 of 3. The reason for the rate change is in no file.

## What this cannot show

- It is one synthetic job and one model, with three runs per arm, written by the plugin's author.
- **A light setup:** the bench starts from about 8k tokens of context. The author's own sessions start from 79k, and that heavy setup is covered only by the replay, which counts no redone work.
- Real users react to what the model does. The script does not.

## What changed while building (28 October, before the main runs)

- **The repository is smaller than planned:**
  - 13 modules, about 2.6k lines of code and tests (483 tests);
  - an import log of 2.6k lines (281 KB) with 14 duplicate entries.
- **Tools:** TodoWrite does not exist under `-p` in Claude Code 2.1.308. Every arm gets TaskCreate, TaskUpdate, TaskList and TaskGet instead, plus the Skill tool.
- **Arm C:** LR Memory runs with its background passes off (`LR_MEMORY_NO_SPAWN=1`). Its sleep pass would start a `claude -p` of its own, outside the run's count. The note and the search work as usual.
- **Phase 2:**
  - LR Memory adds nothing at a fresh start. What it gives the next session is the recall skill, a search over the transcripts in the config folder.
  - Each next session runs in its own copy of the run's config folder and repository.
- **The grader is stricter in three places:**
  - I1 checks two totals: 10.125 must round to 10.12 and 10.135 to 10.14. Half-down rounding and truncation therefore fail too.
  - I2 also checks that the other rates did not move.
  - R3 also checks that the old English messages were left alone.
- **The selftest:** the job as given fails 14 of the 16 checks.
- **The pilot** ran arms B and C on messages 1–5, once each.
  - Claude Code compacts well before the window. At `--autocompact 100k`, both runs compacted at 67k and dropped to 23k and 28k.
  - W stays 100k. The context after a compaction is about a quarter of the window, or two-fifths of the point where it compacts.
  - The pilot took 3.4M tokens and about 4 minutes a run, and both runs passed the 7 checks that messages 1–5 can reach.
  - The note landed after C's compaction.
  - The projection for the main runs and next sessions was 44M tokens, 0.55 of the design's 79M. That is inside the stop rule, so the main runs went ahead.
