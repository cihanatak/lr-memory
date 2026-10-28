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
