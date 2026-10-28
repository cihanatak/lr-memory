# The shelf job: does 0.3.1 carry what was said in passing?

The [kargo job](../kargo/DESIGN.md) left two gaps in LR Memory 0.3.0, and 0.3.1 closes them:

- **The sleep pass held back what the user had stated.** The carrier's limit, said in passing, was written into memory
  in one chain of three; in the other two it waited as a candidate, which no session sees, as if it were a guess. In
  0.3.1 a fact the user stated about the project or its environment, such as a limit, a number, or a decision and its
  reason, is written the same day, like a standing rule. It must quote the user.
- **The cue cut what the user said at 220 characters.** Day 1's rules, later in a long first message, reached the model
  only through the reply. In 0.3.1 a message of up to 600 characters comes whole, five in six of the messages a user
  types on the author's machine; a longer one comes as its part that carries the prompt's words, as an answer already
  did.

Both fixes were designed on kargo's record. On kargo's saved day 1 the sleep pass alone now writes the limit in 8 of 9
passes, against 5 of 9 before, and the fee's reason in 9 of 9, against 4 ([the probe](../kargo/DESIGN.md)). That says
the fix does what it was built to do on the record it was built on. This job asks whether it carries over:

- **Another project, back in English.** shelf, the circulation software of a small community library, written from
  scratch ([seed.py](seed.py)).
- **Words nobody chose for LR Memory.** A subagent wrote the nine messages in English from their content given in
  Turkish, with no tools, so the wording is its own ([days.py](days.py)). A first attempt is not used: given the
  content in English, that subagent read the kargo design, which says how the cue matches words, and followed the
  brief's English nearly word for word.
- **A fact said in passing that the code must obey.** In a message about the ISBN cleanup, day 1 mentions that the
  label printer at the checkout desk prints only plain ASCII, so accented letters come out as question marks, and
  that there is nothing to do about it yet. Day 2 asks for spine labels the desk will print, for a catalog with García
  Márquez, Brontë and Yaşar Kemal in it, and never mentions the printer's limit. It is graded by what the code does.
- **LR Memory frozen at 0.3.1.** Nothing in the plugin changes for this job, before or after the run.

## The two days

| Day 1 says, once | Day 2 needs it when | Check |
| --- | --- | --- |
| Every change gets a line under `## Unreleased` in CHANGELOG.md, in every session | it changes anything | C1 |
| Nothing in shelf/api.py is renamed: the self-service kiosk calls those names | it is invited to tidy api.py, which has a misspelt name | C2 |
| The late fee is 0.40 a day, not 0.25: the library board raised it in September to help pay for the new reading room | a member asks why the fee is what it is | F1 |
| The last summary was far too long; keep them short | it answers, and sums up the day | C3 |
| tools/audit_isbn.py finds 191 bad ISBNs: the baseline before the cleanup | it writes today's count next to yesterday's | F2 |
| In passing: the checkout desk's label printer prints only plain ASCII, nothing to do for now | it writes `spine_label` for labels the desk will print | F3 |

Day 1's other items are work: loans of 21 days, the late fee capped at 5.00 a loan, and the ISBN cleanup (hyphens,
spaces and a lower-case x no longer make an ISBN bad; it brings 191 down to 40 when done right). Day 2 restates none of
the facts.

## Checks

Ten, all mechanical ([checks.py](checks.py), [hidden_checks.py](hidden_checks.py)):

- **Task.** T1: five plain books get labels that show the title, the author's surname and the call number. T2: an
  anonymous work's label shows its title and call number, and no None. T3: the repository's own tests pass. T4:
  today's count is in docs/data_quality.md.
- **Rules.** C1: CHANGELOG.md's Unreleased section gained a line. C2: every name of api.py is still there, the typo
  too.
- **Memory.** C3: the median day-2 answer is 100 words or fewer. F1: fees.py says why: the board, or the reading room.
  F2: yesterday's 191 is in docs/data_quality.md; None when today's count is also 191. F3: all 23 catalog titles with
  an accent in the title or the author's name get labels in plain ASCII that still show the accented words, written
  plain ("García" as "Garcia"; "Günter" as "Gunter" or "Guenter"). Accents kept fail it, and so do question marks.

A label may be a string or a list of lines, may wrap, and may put the surname first; the selftest shows the right label
passing all ten checks and each faulty one failing only its own. Each chain also records what day 1 wrote into the
repository (a reason, the printer, the number, a rule): day 2 can read those instead of remembering them.

## Arms and plan

N is Claude Code alone, with its own memory on. L is LR Memory 0.3.1, with its sleep pass over day 1. Both start day 2
from the same copy of each chain's day 1, in the same folder.

1. **Scan**: one chain, N only. If N passes three or more of the four memory checks, the job is too easy to tell the
   arms apart and stops there.
2. **Run**: three chains, N and L.

```
python bench/cross_session/run.py --job shelf --selftest
python bench/cross_session/run.py --job shelf --scan --env-module <file> --out <folder>
python bench/cross_session/run.py --job shelf --n 3 --env-module <file> --out <the same folder>
```

## Predictions (29 October 2026, before any run)

Word counts use the cue's own term rules, on the messages as the subagent wrote them.

- **Scan.** N passes at most one of the four memory checks; about 0.55M tokens (0.35M to 0.9M).
- **F3, the printer.** L at least 2 of 3, N at most 1 of 3. Two ways can carry it, and both are new in 0.3.1. The
  sleep pass should write it as a fact the user stated: on kargo's day 1 it wrote the limit in 8 of 9 passes. And
  day 2's first message shares seven words with day 1's fifth ("label", "print", "desk", "check"...), so the cue may
  bring that turn back; the printer comes at character 210 of it, after 0.3.0's cut at 220 would have ended it.
- **F1, the reason.** L 3 of 3 (at least 2), N at most 1 of 3. Day 2's question shares three words with the correction
  ("fee", "late", "short") and four with the item it corrected. The reason comes before character 220 of the
  correction, so 0.3.0's cue would have shown it too; the sleep pass wrote kargo's reason in 9 of 9 passes.
- **F2, the number.** L at least 2 of 3, N at most 1 of 3. Day 2's third message shares six words with day 1's fourth
  ("audit_isbn.py", "baseline", "number"...); the cue brings that turn's reply, with the number.
- **C3.** At most 1 of 3 in each arm.
- **Rules.** L 6 of 6 (at least 5); N 5 of 6 (4 to 6).
- **Paired** over three chains and the six memory and rule checks: L passes where N fails at least 6 times, the other
  way round at most once.
- **Tokens.** The sleep pass 5,000 to 9,000 tokens a chain. Day 2's median for L, its sleep pass included, between 0.8
  and 1.6 times N's. The scan and the run together about 3M (2M to 4.5M).

## Results (29 October 2026)

The scan (chain 1, N only): memory 0 of 4, rules 2 of 2, 736,665 tokens. Claude Code alone kept both rules, which its
own memory had written down on day 1, and lost every fact. The job went on to three chains, N and L, on Sonnet 5.5:

| | N: Claude Code alone | L: with LR Memory 0.3.1 |
| --- | --- | --- |
| T1, T2: labels for plain books and an anonymous work | 6 of 6 | 6 of 6 |
| T3: the repository's tests | 1 of 3 | 1 of 3 |
| T4: today's count in docs/data_quality.md | 1 of 3 | 3 of 3 |
| C1: a line under Unreleased | 1 of 3 | 3 of 3 |
| C2: api.py's names kept | 1 of 3 | 3 of 3 |
| C3: short answers | 0 of 3 | 0 of 3 |
| F1: the reason, the board and the reading room | 0 of 3 | 3 of 3 |
| F2: yesterday's 191 | 0 of 3 | 3 of 3 |
| F3: plain ASCII labels for the 23 accented titles | 0 of 3 | 3 of 3 |
| Memory checks (C3 F1 F2 F3) | 0 of 12 | 9 of 12 |
| Day-2 tokens, median (L with its sleep pass) | 212,052 | 254,801 |

Paired over the three chains and the six memory and rule checks, L passed where N failed 13 times and the other way
round never (two-sided sign test, p = 0.0002). The test counts the 18 pairs as independent, and they are not quite:
the checks of one chain share its day 1. Counted by chain, L was ahead in 3 of 3. The facts alone, without the two
rules that N lost only where its own memory had written nothing (below), give 9 and 0, p = 0.004.
`python bench/cross_session/run.py --job shelf --summary <folder>` prints the full table.

Where each fact came from, read from the memory files at day 2's start, the turns the cue showed, and the code:

- **F3, the printer.** LR Memory's sleep pass wrote it into memory in all three chains, as a fact in the user's words:
  "The label printer at the checkout desk is old and only prints plain ASCII, so accented letters come out as question
  marks." The cue brought day 1's fifth turn in chain 1 only, so in chains 2 and 3 the memory file was the one source.
  Day 2's code said so ("Spine labels for the checkout desk printer, which prints plain ASCII only.", chain 2) and
  dropped the accents. Claude Code alone wrote labels that keep them, "Charlotte Brontë", in all three chains.
- **F1.** The sleep pass wrote the fee and its reason into memory in all three chains, and the cue brought the
  correction in all three. Claude Code alone found no reason in the repository and did not make one up: it asked for it
  in chains 1 and 3, and in chain 2 wrote a comment that says how the fee is worked out, "not why".
- **F2.** No memory file held 191 in any chain. The cue brought day 1's fourth turn and its reply in all three.
  Claude Code alone ran the audit and found no baseline. In chains 1 and 2 it wrote nothing into docs/data_quality.md
  and asked for the number; in chain 3 it wrote today's count alone. In chain 1 it counted the old way and got 191,
  but would not write that down as yesterday's number.
- **C1 and C2.** Claude Code's own memory was on in all three day-1 sessions, with the same settings, and wrote the two
  rules down in chain 1 only. In chains 2 and 3 it wrote nothing, and day 2 there renamed `member_lonas`, which the
  kiosk calls, and added no changelog line. L kept both rules in all three chains: the sleep pass wrote them, and the
  cue brought day 1's first turn.
- **C3.** "Keep summaries short" was in memory for L in all three chains: written by the sleep pass in chains 2 and 3,
  by Claude Code's own memory in chain 1. Every arm's answers stayed long, a median of 128 words for L and 155 for N.
- **T3.** Day 1 in chains 2 and 3 changed the loan period to 21 days and left a test that expects 14 failing. It fails
  on the day-1 snapshot, and neither arm fixed it, so it measures day 1, not the arms.

Tokens. L's day 2, its sleep pass of 4,560 to 5,199 tokens included, cost 5% less, 53% more and 24% more than N's,
chain by chain. As in kargo, Claude Code alone did less: it wrote no reason and no baseline in any chain, where L wrote
both in all three. The scan and the run took 2.48M tokens together.

Predictions that held: the scan (0 of 4 memory checks, 0.74M tokens); F3 (L 3, N 0); F1 (L 3, N 0); F2 (L 3, N 0); C3
(0 and 0); the rules in L (6 of 6); paired wins and losses (13 and 0); L's day-2 median, 1.20 times N's; the total
(2.48M). Those that missed: the rules in N (2 of 6, not about 5), because Claude Code's own memory wrote nothing in two
of the three day-1 sessions; the sleep pass's tokens (4,560 to 5,199 a chain, not 5,000 to 9,000).

The sleep pass alone, on this job's day 1, run after the job with 0.3.0 for comparison: three passes per chain on each
chain's saved day 1, nothing else run ([sleep_probe.py](../sleep_probe.py)).

| Of 9 passes | 0.3.0 | 0.3.1 |
| --- | --- | --- |
| The printer's limit written into memory | 4 | 9 |
| The limit held back as a candidate | 5 | 0 |
| The fee's reason written into memory | 0 | 9 |
| Tokens, all 9 passes | 41,100 | 43,615 |

0.3.0 wrote the limit in all three of chain 1's passes, and in one of the six on chains 2 and 3, the two chains where
the cue did not bring the printer's turn. With 0.3.0, those two chains would have had the printer in memory about one
time in six; with 0.3.1 they had it every time. A first attempt at this probe ran into the account's usage limit after
7 of its 18 passes and counted the 11 failed passes as passes that wrote nothing. sleep_probe.py now leaves a failed
pass out of its counts, says how many failed, and exits with 1.

What it says:

- **The fix carries over to a job it was not built on.** A limit mentioned in passing, in a message about something
  else, reached the next day's code in 3 of 3 chains through the memory the sleep pass wrote; nobody mentioned it on day
  2. On the same day-1 record, 0.3.0's sleep pass held it back in five passes of nine and never wrote the fee's reason.
  Claude Code alone printed accented labels in all three chains.
- **The cue's results hold in a third job.** The measured number and the reason came back in 3 of 3 chains, against 0
  of 3.
- **Claude Code's own memory is not reliable for rules.** With the same settings in all three day-1 sessions, it wrote
  the two rules down in one. Without them, day 2 renamed a function the kiosk calls.
- **Short answers are still not kept.** 0 of 3 in both arms, although the complaint was in memory for every L session.
