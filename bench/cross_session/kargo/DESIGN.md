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

## Results (29 October 2026)

The scan (chain 1, N only): memory 0 of 4, rules 1 of 2, 547,764 tokens. Claude Code's own memory wrote nothing on that
chain's day 1, so day 2 lost the changelog rule too. The job went on to three chains, N and L, on Sonnet 5.5:

| | N: Claude Code alone | L: with LR Memory 0.3.0 |
| --- | --- | --- |
| T1-T3: bulk labels, no orders, the repository's tests | 9 of 9 | 9 of 9 |
| T4: today's count in docs/veri_kalitesi.md | 0 of 3 | 3 of 3 |
| C1: a line under Yayımlanmamış | 2 of 3 | 3 of 3 |
| C2: api.py's names kept | 3 of 3 | 3 of 3 |
| C3: short answers | 1 of 3 | 0 of 3 |
| F1: the reason, a fuel surcharge | 1 of 3 | 3 of 3 |
| F2: yesterday's 218 | 0 of 3 | 3 of 3 |
| F3: 150 orders within 60 a minute | 0 of 3 | 1 of 3 |
| Memory checks (C3 F1 F2 F3) | 2 of 12 | 7 of 12 |
| Day-2 tokens, median (L with its sleep pass) | 222,538 | 313,512 |

Paired over the three chains and the six memory and rule checks, L passed where N failed 7 times and the other way
round once (two-sided sign test, p = 0.070). Pooled with the first job's four held-out chains (8 and 1), that is 15 and
2, p = 0.002. `python bench/cross_session/run.py --job kargo --summary <folder>` prints the full table.

Where each fact came from, read from the memory files at day 2's start, the turns the cue showed, and the code:

- **F2.** No memory file held 218 in any chain. The cue brought day 1's fourth turn and its reply in all three. Claude
  Code alone ran the tool, found no trace of yesterday's number, and wrote nothing into the file in all three chains:
  "Uydurma bir referans yazmak istemedim." T4 fails with it.
- **F1.** The cue brought day 1's correction in all three chains. In chain 1 it was the only source. In chains 2 and 3
  the sleep pass had also written the reason into memory. Alone, Claude Code asked for the reason in chain 1 and wrote
  a comment without it in chain 2. Its one pass is chain 3, where day 1 had written the reason into the repository.
- **F3.** The cue never brought day 1's fifth turn, as predicted. LR Memory's sleep pass wrote the limit into memory in
  chain 2 ("Toplu veya döngüyle Turna Kargo çağrısı yazarken istek hızını sınırla ve 429'u ele al"), and that chain's
  bulk job paced itself: 150 labels, no 429. In chains 1 and 3 the sleep pass held the limit back as a candidate, which
  no session sees ("bir çıkarım olduğu için aday olarak bekliyor"), although the user had stated it. Those bulk jobs
  failed at the 61st order, like all three of N's. In chain 1, day 1 had answered "dakikada 60 istek sınırını not
  aldım" and written it nowhere.
- **C1.** In chain 1, N added no changelog line. L's sleep pass had written the rule, and the cue brought day 1's first
  turn.
- **C3.** The sleep pass wrote "keep summaries short" into memory in all three chains, and the cue brought the
  complaint. L's answers stayed long: a median of 126 words, against N's 103.

What the cue put in front of the model, from chain 1's day-2 transcript: before the first prompt, day 1's first two
turns; before the second, the correction ("...yeni tarifeye geçti ve yakıt ek ücreti ekledi..."); before the third,
the measuring turn and its reply ("640 siparişten 218'inin adresi sorunlu"). The first turn's rules reached the model
through its reply ("kargocu/api.py'ye dokunmadım, oradaki hiçbir ad değişmedi"): the cue shows the first 220
characters of what the user said, and the rules came later in that message.

Tokens. L spent more on day 2: chain by chain 94%, 19% and 18% more, its sleep pass (about 5,300 tokens) included. That
is not the cue's overhead. Claude Code alone did less: in all three chains it wrote no file and asked for yesterday's
number, and in chain 1 it asked for the reason as well; L did all of it. The turns those questions cost the user are not
measured here. The whole job, scan included, took 3.02M tokens.

Predictions that held: the scan's memory checks (0 of 4); F1 (L 3, N 1); F2 (L 3, N 0); F3 (the cue never brought it,
and L and N within one chain, 1 and 0); paired wins and losses (7 and 1); the total (3.02M). Those that missed: the
rules in N (5 of 6, not 6 of 6); C3 in N (1 of 3, not 0); day-2 tokens within 25% (L 18% to 94% more); the scan's
tokens (0.55M, not about 1.0M).

What it says:

- **The cue carries over.** In a new project and a new language, with messages written by a subagent that was not told
  how the cue matches words, it brought the measured number in 3 of 3 chains and the reason in 3 of 3. Claude Code
  alone wrote the number in none, and the reason only where day 1 had put it in the repository.
- **It does not carry a fact said in passing.** A limit mentioned inside a message about something else shares no
  words with the later task that needs it. Carrying it is the sleep pass's job, and the sleep pass did it in 1 of 3
  chains; in the other two it held back what the user had stated as if it were a guess. That is the next fix, and it
  will need a third job to show.
- **A known rule is still not kept.** Short answers failed in both jobs and every arm.

## After the run: the sleep pass fixed, on this job's day 1 (29 October 2026)

LR Memory 0.3.1 gives the sleep pass a third basis besides a directive and a lesson: a fact the user stated about the
project or its environment, such as a limit, a number, or a decision and its reason, even in passing. Like a directive,
it must quote the user and is written the same day. What follows from it for the work goes in its How to apply line and
no longer makes it an inference that waits. The fix was designed on this job's record, so this job cannot show that it
works; [the third job](../shelf/DESIGN.md) is for that.

What it does here, with the sleep pass alone: three passes per chain on each chain's saved day 1, nothing else run
([sleep_probe.py](../sleep_probe.py)).

| Of 9 passes | 0.3.0 | 0.3.1 |
| --- | --- | --- |
| The API's limit written into memory | 5 | 8 |
| The limit held back as a candidate | 2 | 0 |
| The fuel surcharge, the fee's reason, written into memory | 4 | 9 |
| Memory files written per pass, median | 3 | 4 |
| Tokens, all 9 passes | 45,808 | 56,348 |

`python bench/cross_session/sleep_probe.py --job kargo --results <run folder> --out <folder> --runs 3 --env-module
<file> --plugins <0.3.0 folder>,<0.3.1 folder>`
