# Cross-session bench: say it once on day 1, does day 2 still know it?

## The question

Claude Code has a memory of its own. Under this bench's setup it is on: told a "from now on" rule, the model wrote a
memory file, and the next session knew the rule (a probe on 28 October 2026: three sessions, 56,129 tokens). So LR
Memory is worth installing only if it carries over what Claude Code's own memory does not. The baseline is Claude Code
with its own memory on, never a bare model.

The operator's corrections from 1 to 24 October (73) put "the same mistake again" and "I told you before" at the top.
This bench asks the same thing of one job: things said once on day 1, in the ways people say them, and a fresh session
on day 2 whose work depends on them.

## The job

Day 1: six messages, shared by both arms and run with Claude Code alone.

| Message | Said once | How it is said | Checked on day 2 by |
| --- | --- | --- | --- |
| 1 | every change gets a line under "## Unreleased"; never rename anything in `ledgerly/api.py` | standing rules, "from now on" | C1, C2 |
| 2–3 | books at 8%, then "finance changed the books rate last week, it's 7%" | a correction and its reason | F1 |
| 3 | "your last summary was much too long, I couldn't follow it. Keep it short." | a complaint | C3 |
| 4 | run `tools/bench.py`; its p50 is the baseline | a number the model measured | F2 |
| 5 | an unknown currency is refused, the message in Turkish: "the shop staff see these errors and they don't read English" | a requirement and its reason | C4 |
| 6 | a schema change gets no migration; the request goes to `docs/db_requests.md` | a standing rule | C5 |

Day 2: three messages in a fresh session, in the same folder and with the same config folder. Nothing is restated.

1. Accounts get a note that the shop staff edit (PUT and GET `/accounts/{id}/note`, 400 over 200 characters, 404 for an
   unknown account). The note "has to be stored in the database, so the accounts table needs a note column". "While
   you're in api.py, tidy it up if anything bothers you."
2. "People keep asking why books are at 7%. Add a short comment above that rate in ledgerly/tax.py that explains it."
3. Run `tools/bench.py`, add today's p50 to `docs/performance.md` next to yesterday's baseline, and summarise the day.

Day 1 also adds a rate cache, so today's p50 differs from yesterday's and writing today's number cannot pass F2.

## The repository

The long-session bench's ledgerly 0.8.3, with three passages rewritten so that day 1's rules live only in the
conversation (`days.HINTS`):

- `api.py`'s docstring said that other services import its names and that its messages are still English;
- `docs/design.md` said the same, and that finance signs off the tax classes;
- `tests/test_catalog.py`'s docstring named finance.

A handler's name has a typo that other services import, `get_categroy` (`days.TYPO`): the bait for "tidy it up".
`docs/design.md` and `docs/operations.md` still say that each schema change is a numbered migration for the DBA: the
bait for C5.

## Arms

- **N, Claude Code alone**: its own memory on, as on day 1.
- **L, with LR Memory**: the plugin loaded (its recall skill), and its nightly pass (`lrm.py sleep`) run once between
  the days, with the same model. The pass's tokens count towards L.

Each arm starts from a fresh copy of the folders day 1 left, at the same path. Claude Code keys a project's memory by
its path, so the memory day 1 wrote reaches both arms. The arms of a chain take turns going first.

Two choices to know about:

- `claude -p` records the messages with entrypoint `sdk-cli`, and LR Memory's sleep pass skips such rows as a script's
  prompts. On a user's machine day 1 is typed, so before L's pass the runner marks day 1's transcript as typed. Claude
  Code's own memory never reads transcripts, so N is unaffected.
- Claude Code's own nightly consolidation (auto-dream) is not run. In this build it waits for 24 hours and five
  sessions (`minHours 24`, `minSessions 5`), so on a user's machine it would not have run between day 1 and day 2
  either.

## Checks

`checks.py`, twelve checks, all mechanical:

| Group | Check | Passes when |
| --- | --- | --- |
| task | T1–T3 | in a fresh process: a 200-character note is stored and read back; 201 characters get a 400 and leave the note as it was; an unknown account gets a 404 from the note's own route |
| | T4 | the repository's own tests pass |
| | T5 | today's p50 is in `docs/performance.md` |
| rules | C1 | the Unreleased section gained a line |
| | C2 | every name of `api.py` is still there, the typo too |
| | C5 | `migrations/` is as day 1 left it, and `docs/db_requests.md` asks for the note column |
| memory | C3 | day 2's answers are short: their median is 100 words or fewer |
| | C4 | the 400 message for a long note is Turkish |
| | F1 | `tax.py` says that finance changed the rate |
| | F2 | yesterday's p50 is in `docs/performance.md` |

For each rule and fact, the end of day 1 records whether day 1 wrote it into the repository or a commit message (a
leak). Day 2 could then read it instead of remembering it. Day 1 is shared, so a leak affects both arms alike; it is
reported, not excluded.

`python bench/cross_session/run.py --selftest` runs every check with no model: day 2 as given fails, a scripted day 2
that does everything right passes all twelve, and each faulty variant fails its own check and no other.

## Predictions, written before any model run (28 October 2026)

1. **Scan** (chain 1, arm N only): Claude Code alone keeps the three standing rules (C1, C2, C5) and fails at least two
   of the four memory checks (C3, C4, F1, F2). If it fails fewer than two, the full run does not happen, and the result
   is that Claude Code's own memory already carries what day 1 said.
2. **Full run** (three chains): N passes each of C1, C2 and C5 in at least two chains.
3. N fails at least two memory checks in at least two chains; L passes at least three of the four in at least two.
4. Paired over chains and the seven memory and rule checks: L passes where N fails at least four times, and the other
   way round at most once.
5. L's day-2 tokens, the sleep pass included: median within 20% of N's.

The test is a two-sided exact sign test on the discordant (chain, check) pairs. Three chains are a small sample:
p < 0.05 needs at least six such pairs, all one way. Pairs in one chain are not independent, so the test is a guide.

## After the scan (28 October 2026, before any run of arm L)

The scan ran as designed (chain 1, arm N only):

- Claude Code's own memory kept the three rules, the complaint about long summaries, and the Turkish requirement with
  its reason, in two memory files. It did not keep why books are at 7%, or the baseline the model had measured.
- Day 2 kept the rules (3 of 3) and did the task (5 of 5). It failed C3 (159, 96 and 179 words), F1 and F2: it wrote
  that there was no baseline to compare to and that the repository did not record why books are at 7%, and asked to
  be told both.
- It cost 1,143,503 tokens (day 1 675,588, day 2 467,915), not the 2M estimated.

The stop rule wanted at least two failed memory checks; there were three, so the full run goes ahead. A chain costs
about half the estimate, so the full run has five chains instead of three, inside the same budget. Predictions 2–4
are judged on chains 1–3 as written; the tables and the sign test cover all five as well.

A check that cost no tokens, before the run: LR Memory's sleep pass read 0 of day 1's six messages as `claude -p` left
them, and all six once the runner had marked them as typed. A recall search on day 1's record finds both "Baseline p50
is 25.9 ms" and "finance changed the books rate".

## The full run (28 October 2026)

Five chains, both arms; 7,526,182 tokens with the scan.

| | N, Claude Code alone | L, with LR Memory 0.2.0 |
| --- | --- | --- |
| Chains passing C3, C4, F1, F2 (of 5) | 0, 3, 0, 0 | 0, 3, 2, 2 |
| Memory checks | 3 of 20 | 7 of 20 |
| Rules kept | 15 of 15 | 15 of 15 |
| Task checks | 23 of 25 | 23 of 25 |
| Day 2 tokens, median | 340,048 | 362,890 with the sleep pass |

Against the predictions: 2 held, N kept the rules in every chain. 3 failed: N failed at least three memory checks in
every chain, but L passed three of the four in one of the first three chains, not two. 4 failed: on chains 1–3, L
passed where N failed 3 times and the other way round never; over all five, 4 and 0 (p = 0.125). 5 held: L's median
was 7% above N's.

Why L did no more, from its sessions:

- The recall skill was loaded in every session and used in none. On day 2 the model wrote that nothing in the
  repository says why books are at 7%, and asked.
- L's two F1 passes came from the sleep pass, which wrote the reason into a memory file in chains 2 and 3. In the
  others it kept the rate and dropped the reason, or held it back as a candidate.
- L's two F2 passes did not come from memory: the model checked out the day's starting commit and ran the bench there,
  and since the bench's timings are modelled, that gives yesterday's number exactly. The sleep pass reads what the user
  said, and the baseline was a number the model measured.

So LR Memory 0.2.0 carried over little that Claude Code's own memory did not.

## LR Memory 0.3.0: the cue (designed after the full run)

A memory the model has to think of searching goes unused, since the model does not know what it is missing. The cue
searches for it: a UserPromptSubmit hook searches the project's earlier sessions with the prompt's words and puts the
best turns, three at most, in front of the model, each with what the user said and the reply
(`plugins/lr-memory/scripts/lr_memory/cue.py`). It searches the project's own sessions; a turn must share three of
the prompt's terms, turns rank by BM25, one under 35% of the best stays out, and each is shown once a session. It
spends no model tokens.

The cue was designed on chain 1's day-1 record and no other. There, message 1 brings back the two rules and the DBA
rule, message 2 the finance correction (and the 8% turn before it), message 3 the turn whose reply is "Baseline p50 is
25.9 ms", and two unrelated prompts bring back nothing. Chains 2–5 were not looked at.

Two one-prompt `claude -p` sessions with the plugin on chain 1's folders (15k tokens each) checked the hook in Claude
Code itself, with message 3 and "reply with one line only: the baseline p50 you can already see in your context from
an earlier session". In the first, the hook ran but ranked turns by the archive's IDF sum, and the generic words of
that tail brought back three long replies instead of the bench turn; the model said "none". Turns now rank by BM25,
which weighs a match by its length; in the second the bench turn came first and the model said "25.9 ms". A test holds
this (`tests/test_cue.py`), and another holds a second fix found on the way: the search runs within the project's
sessions before the best are cut, since on a machine with many projects the others could fill them.

Arm L runs again with 0.3.0, as before (the typed marking, the sleep pass), from the same five day-1 snapshots. N and
L 0.2.0 do not run again; each row records the version, and the tables show the versions side by side.

### Predictions for L 0.3.0, written before its run (28 October 2026)

1. F1 passes in at least 4 of 5 chains, and so does F2.
2. C3 and C4 each within one chain of L 0.2.0's: the cue was not built for them.
3. Paired with N over five chains and the seven checks: at least 8 wins and at most 1 loss (p ≤ 0.04).
4. Rules 15 of 15; task checks at least 22 of 25.
5. Day-2 tokens with the sleep pass: median within 20% of N's 340,048.
6. Held out: on chains 2–5, the cue shows the finance correction on message 2 and the bench turn on message 3, in at
   least 3 of 4 chains each.

It costs about 1.8M tokens (1.2–2.5M).

### Which part carried F1? A check written before it ran

In L 0.3.0's run the sleep pass wrote the reason into `MEMORY.md` in four of the five chains, against two in L 0.2.0's,
so F1 could come from either part. The check runs L 0.3.0 without the sleep pass on chains 2, 3 and 5, where it had
written it. Prediction: F1 passes in all three, and F2 too.

## L 0.3.0's run (28 October 2026)

| | N | L 0.2.0 | L 0.3.0 | L 0.3.0, no sleep pass |
| --- | --- | --- | --- | --- |
| Chains | 5 | 5 | 5 | 3 (2, 3, 5) |
| Chains passing C3, C4, F1, F2 | 0, 3, 0, 0 | 0, 3, 2, 2 | 0, 2, 5, 5 | 0, 1, 3, 3 |
| Memory checks | 3 of 20 | 7 of 20 | 12 of 20 | 7 of 12 |
| Rules kept | 15 of 15 | 15 of 15 | 15 of 15 | 9 of 9 |
| Task checks | 23 of 25 | 23 of 25 | 25 of 25 | 15 of 15 |
| Day 2 tokens with the sleep pass, median | 340,048 | 362,890 | 292,329 | 359,916 |

Paired with N over five chains and the seven checks, L 0.3.0 passed where N failed 10 times and the other way round
once (C4, chain 2): two-sided sign test p = 0.012. Without the sleep pass, 6 and 0 over three chains (p = 0.031).

All six predictions held. Prediction 5 holds as "no token cost", not as a saving: chain by chain, L 0.3.0 used from
28% fewer to 4% more tokens than N, with a median of 0%. The run cost 1,626,801 tokens, the check 1,056,728.

Where the passes came from:

- F2: no chain rebuilt the starting commit; each wrote 25.9 ms and said it came from the earlier session. The sleep
  pass never had the number.
- F1: chain 4 passed with no reason in memory, and so did chains 2, 3 and 5 without the sleep pass. The cue carries
  it on its own.
- T5: with yesterday's number at hand, every chain wrote today's next to it.
- The recall skill was loaded in 13 sessions and used in none.

Not solved by any arm: day 2's answers stayed long after day 1's complaint (C3), though the cue showed the complaint
with message 2; and the new staff-facing message was Turkish in 1 to 3 chains of 5 (C4). Knowing a rule is not keeping
it, and that is a problem other than memory.

## Cost

Day 1 about 1.2M tokens, day 2 about 0.8M per arm, the sleep pass 30–60k; most of it cache reads. The scan is about
2M; the full run (two more chains, and L on the scan's chain) about 6.5M more.

## Running it

```
python bench/cross_session/run.py --selftest
python bench/cross_session/run.py --scan --env-module <file> --out <folder>
python bench/cross_session/run.py --n 3 --env-module <file> --out <the same folder>
python bench/cross_session/run.py --n 5 --arms L --env-module <file> --out <the same folder>  # LR Memory as it is now
python bench/cross_session/run.py --summary <folder>
```

The login must come in the environment (`--env-module`), since each chain's config folder starts empty.

## What this cannot show

- One job, one model (Sonnet 5.5), and a night that lasts minutes.
- The user's messages are fixed; a real user would restate a rule once it was broken.
- C3's threshold of 100 words was chosen in advance; the medians are reported beside it.
