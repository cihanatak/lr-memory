# The kargo job: does the cue carry over?

The first job ([../DESIGN.md](../DESIGN.md)) showed LR Memory 0.3.0's cue bringing a reason and a measured number
from day 1 to a fresh day 2, where Claude Code alone lost both in five chains of five. The cue was designed on that
job's first chain. This job asks whether it works where nothing was fitted to it:

- **Another project, another language.** kargocu, the shipping module of a small online shop, written from scratch
  in Turkish ([depo.py](depo.py)). The user writes in Turkish, and the cue answers in Turkish, as it does on a Turkish
  user's machine (`LR_MEMORY_LANG=tr`).
- **Words nobody chose for the cue.** A subagent wrote the nine messages from a list of what each must say, and was
  not told how the cue matches words ([days.py](days.py)). The brief is below.
- **A third kind of fact.** Besides a reason and a number, day 1 mentions in passing, in a message about something
  else, that the carrier's API takes at most 60 requests a minute. Day 2 needs it to write a bulk job that works, and
  never asks for it. It is graded by what the code does, not by what it says.
- **LR Memory frozen at 0.3.0.** Nothing in the plugin changes for this job, before or after the run.

## The two days

| Day 1 says, once | Day 2 needs it when | Check |
| --- | --- | --- |
| Every change gets a line under `## Yayımlanmamış` in CHANGELOG.md, in every session | it changes anything | C1 |
| Nothing in kargocu/api.py is renamed: the mobile app calls those names | it is invited to tidy api.py, which has a misspelt name | C2 |
| The flat same-province fee is 54,90, not 49,90: the carrier moved to a new tariff and added a fuel surcharge | accounting asks why the fee is what it is | F1 |
| The last summary was far too long; keep them short | it answers, and sums up the day | C3 |
| tools/adres_kontrol.py finds 218 problem addresses: the reference before the cleanup | it writes today's count next to yesterday's | F2 |
| In passing: the carrier's API takes at most 60 requests a minute, answers 429 above that, nothing to do for now | it writes `toplu_etiket` for "a few hundred orders in one go" | F3 |

Day 1's other items are work: desi rounds up, the same-province fee, the address cleanup (names match whatever their
case and Turkish letters; it brings 218 down to 63 when done right). Day 2 restates none of the facts.

The subagent's brief gave, for each message, its content in English; for day 2 it added: "The developer does not repeat
anything they said on day 1: no carrier name, no tariff or surcharge, no API limit, no reference number, no rules."

## Checks

Ten, all mechanical ([checks.py](checks.py), [hidden_checks.py](hidden_checks.py)):

- **Task.** T1: five orders give five labels in order, each with its own tracking number, each order registered once.
  T2: no orders, no labels, no call. T3: the repository's own tests pass. T4: today's count is in
  docs/veri_kalitesi.md.
- **Rules.** C1: CHANGELOG.md's Yayımlanmamış section gained a line. C2: every name of api.py is still there, the
  typo too.
- **Memory.** C3: the median day-2 answer is 100 words or fewer. F1: ucret.py says fuel (`yakıt`). F2: yesterday's 218
  is in docs/veri_kalitesi.md; None when today's count is also 218. F3: 150 orders against a carrier that takes 60 a
  minute all get their labels.

F3 runs the repository's own `KargoIstemcisi` against a stand-in for the carrier at the network boundary (urllib's
urlopen), on a stand-in clock, so a limit kept anywhere counts and waiting costs no time. The stand-in takes at most 60
shipments in any 60 seconds and answers 429 above that, with a Retry-After header. Pacing the calls passes, and so does
waiting out each 429; a plain loop fails at the 61st order, and so does a retry that gives up after a few seconds. The
selftest shows all four.

Each chain also records what day 1 wrote into the repository (a reason, the limit, the number, a rule): day 2 can read
those instead of remembering them.

## Arms and plan

N is Claude Code alone, with its own memory on. L is LR Memory 0.3.0 as shipped, with its sleep pass over day 1. Both
start day 2 from the same copy of each chain's day 1, in the same folder.

1. **Scan**: one chain, N only. If N passes three or more of the four memory checks, the job is too easy to tell the
   arms apart and stops there.
2. **Run**: three chains, N and L.

```
python bench/cross_session/run.py --job kargo --selftest
python bench/cross_session/run.py --job kargo --scan --env-module <file> --out <folder>
python bench/cross_session/run.py --job kargo --n 3 --env-module <file> --out <the same folder>
```

## Predictions (29 October 2026, before any run)

- **Scan.** N passes at most one of the four memory checks; it keeps both rules; about 1.0M tokens.
Word counts below use the cue's own term rules, on the messages as the subagent wrote them.

- **F1.** L 3 of 3 (at least 2), N 0 of 3 (at most 1). Day 2's question about the fee shares seven words with day 1's
  correction ("aynı", "il", "ücret", "kısa"...), which gives the reason within its first 220 characters, all the cue
  shows of what the user said.
- **F2.** L at least 2 of 3, N 0 of 3 (at most 1). Day 2's third message shares seven words with day 1's fourth
  ("adres_kontrol.py", "sorunlu", "referans"...); the cue brings that turn's reply, with the number.
- **F3.** The cue is unlikely to bring it. Day 2's first message shares three common words with day 1's fifth
  ("kargo", "arada", "şey") and nine with day 1's first, which will outrank it. And even if that turn came back, the
  220 characters the cue shows of it end at "Turna Kargo'nun API", before the limit. L can still pass from a memory
  file, Claude Code's own or the sleep pass's: L and N within one chain of each other.
- **C3.** 0 of 3 in both arms.
- **Rules.** 6 of 6 in both.
- **Paired** over three chains and the six memory and rule checks: L passes where N fails at least 4 times, the other
  way round at most once.
- **Tokens.** Day 2's median within 25% between the arms; the scan and the run together about 3.5M (2.5M to 5M).
