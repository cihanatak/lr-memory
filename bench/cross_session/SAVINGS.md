# Remember or resume: what LR Memory saves

Claude Code alone has two ways to start the next day. A fresh session with its own memory is cheap and forgets:
that is this bench's arm N. Resuming yesterday's session remembers everything, because every call carries all of
yesterday. The claim to test is that LR Memory gives what a resumed session remembers at what a fresh session costs.
This file finds where the tokens go first, from records that already exist, then sets out the experiment with its
predictions, written before any run, stage 1's result, the long day designed after it, how far its first stage went,
the evening designed after that, with its result, and the two other chains run through it.

## Where the tokens go (no model tokens)

**This bench's records: 11 chains in three jobs.** Day 2 tokens by median. The resumed day 2 is an estimate: day 2's
own calls, each carrying day 1's last context on top of what the session adds.

| Job | Chains | Claude Code alone, fresh | LR Memory, fresh | Day 1's last context | Resumed day 2, estimated |
| --- | --- | --- | --- | --- | --- |
| ledgerly | 5 | 340,048 | 287,401 (0.3.0) | 47,595 | 0.78M (0.61–0.94M), 2.3× fresh |
| kargo | 3 | 222,538 | 308,102 (0.3.0) | 34,009 | 0.45M (0.30–0.55M), 2.0× fresh |
| shelf | 3 | 212,052 | 249,602 (0.3.1) | 24,582 | 0.35M (0.27–0.39M), 1.6× fresh |

- Day 2 made 9 to 15 model calls in every arm. LR Memory adds 1,000 to 1,500 tokens to a fresh session's first call
  (its memory files and the cue), against about 14,000 without it.
- Against a fresh session, LR Memory saved tokens only where Claude Code alone searched for what it had forgotten:
  in ledgerly, 15% fewer by median, with 16 git-history commands against 6 over the five chains. In kargo and shelf
  it spent 38% and 18% more, doing the parts that Claude Code alone skipped or asked about. There, what it adds is
  what is remembered (on shelf, memory checks 9 of 12 against 0 of 12), not tokens.
- A probe resumed shelf chain 1's day 1 the bench's way, with one question (31,336 tokens). Its first call carried
  31,335 tokens of context, against 14,125 for that chain's fresh session, and it answered from yesterday: 0.40 per
  day, raised by the library board for the new reading room.

**A working machine: the author's, 7 days, counts only.**
- 68 sessions, 12,397 model calls and 5.2 billion tokens, sub-agents aside. Cache reads were 98% of all tokens.
- The median call carried 333k tokens of context (90th percentile: 829k). Calls carrying 200k or more took 92% of
  the tokens.
- A fresh session's first call there carries 76k, since the author's setup is heavy. 82% of the tokens were history
  above that.
- Sessions were picked up again 106 times after an hour or more. They carried back a median 447k tokens, and the
  20 calls after each return cost a median 9.2 million.

So Claude Code alone spends most when it keeps yesterday by carrying it. In this bench, day 1 is short and a resume
should cost 1.6 to 2.3 times a fresh session; on the working machine, the context carried back is more than ten times
the bench's.

## The experiment

Arm R joins the cross-session bench: Claude Code alone, with day 2 resuming day 1's session (`claude -p --resume`
with day 1's session), with the same three messages and checks, in the folder that holds its day 1. Claude Code's
own memory is on in every arm. The N and L rows already run are reused. L is 0.3.1 on shelf and 0.3.0 on kargo and
ledgerly.

Measured per chain: the memory checks, the rules and the task checks; day 2's tokens by kind, and its calls. L is
compared with R, paired by chain.

**Stage 1, shelf (3 chains).** Predicted:
- R's day 2 costs 0.27–0.45M tokens per chain (median about 0.35M), at least 1.3 times N's.
- R passes at least L's 9 of 12 memory checks and 6 of 6 rules. With day 1's complaint in its context, it may pass
  C3 where no fresh arm does.
- L uses fewer tokens than R in at least 2 of 3 chains.
- The stage costs about 1.1M tokens (0.8–1.4M).

Stop if R's day 2 costs less than 1.3 times N's: day 1 is then too short to show a saving, and it gets longer
before stage 2. Stop also if L uses more tokens than R in 2 of 3 chains.

**Stage 2, kargo and ledgerly (8 chains).** Predicted:
- R costs about twice N's tokens (1.6–2.5 times).
- L uses fewer tokens than R in at least 7 of 8 chains.
- R passes at least as many memory checks as L in each job.
- About 5.3M tokens (4–7M). Rerunning L with 0.3.1 on these chains, so that every L row is the released version,
  costs about 2.4M more.

**Over all 11 chains.** L uses fewer tokens than R in at least 9, with L's tokens a median 0.6 of R's (0.4–0.85).
The finding to report is how many of R's memory checks L kept, and at what share of R's tokens.

## Stage 1 result (29 October 2026)

Shelf, 3 chains, 1,045,733 tokens. The N and L rows are the ones already run on the same day-1 records; L's tokens
include its nightly pass.

| | N | L 0.3.1 | R |
| --- | --- | --- | --- |
| Memory checks | 0 of 12 | 9 of 12 | 9 of 12 |
| Rules kept | 2 of 6 | 6 of 6 | 6 of 6 |
| Task checks | 8 of 12 | 10 of 12 | 10 of 12 |
| Day 2 tokens, chains 1–3 | 212,052; 166,859; 217,605 | 201,255; 254,801; 270,269 | 562,940; 246,789; 236,004 |
| Model calls | 11, 10, 12 | 10, 12, 13 | 15, 9, 9 |
| First call's context | 14,125; 13,824; 13,824 | 15,443; 15,260; 15,191 | 31,425; 25,001; 23,607 |

Against the predictions:
- R's day 2 cost 0.56M, 0.25M and 0.24M (median 0.25M): none of the three in 0.27–0.45M.
- R cost 2.65, 1.48 and 1.08 times N (median 1.48): at least 1.3 times by median, not in chain 3.
- R passed 9 of 12 memory checks and 6 of 6 rules, as L did. No check came out differently for L and R in any chain.
  Both failed C3: with day 1's complaint in its context, R's answers still had medians of 102 to 130 words.
- L used fewer tokens than R in 1 chain of 3 (L/R 0.36, 1.03 and 1.15), not in at least 2. The stop rule holds, and
  stage 2 does not run.
- The stage cost 1.05M tokens, inside 0.8–1.4M.

Why the resume was cheap: each of its calls carried 10,000 to 17,000 tokens more than a fresh session's (day 1's
last context, less a fresh session's start), as the estimate assumed. But the estimate also assumed it would make as
many calls as a fresh session. In chains 2 and 3, it made 9 calls against 10 to 13 and printed none of the source files
again, since what it read of them on day 1 was still in its context; L's fresh sessions printed them again
(`cat shelf/api.py` and the like). In chain 1, it made 15 calls and cost 2.8 times L.

So on a day this short, Claude Code alone, resuming, remembers what LR Memory remembers, at about the same cost. A
saving against a resume can only show where yesterday is long: on the working machine above, returns carried back a
median 447k tokens, 18 times shelf's day 1. Measuring it needs a day 1 that leaves that much context, with all three
arms run again on it.

## The long day (designed 29 October 2026, before any run)

Each shelf chain's day 1 runs on into an afternoon. The user comes back after lunch, and day 1's own session is
resumed with nine more messages ([shelf/days.py](shelf/days.py)). They build holds (reservations) end to end from a
spec by the library's circulation working group, which the user put into the repository over lunch, together with
the Riverside branch's holds ([shelf/seed.py](shelf/seed.py)): a plan, the core and its tests, returns and renewals, two
limits the front desk set (the hold shelf takes 7 days of pickups; at most 5 holds a member), an import of Riverside's
holds, a count from it, an operation in api.py, a page for the volunteers, and a last run of the tests. A subagent wrote the messages and the spec from their content given in Turkish, with no tools, as for day 1.
Day 2 is unchanged: the same three messages and the same ten checks. LR Memory stays at 0.3.1.

Why this afternoon:
- **It grows the way long sessions grow.** On the working machine, the sessions whose context passed 150k in those 7
  days (12 of them) gained a median 1,800 tokens a call over a median 616 calls; what they carried was mostly shell
  commands and their output, and files written and read. The afternoon is that kind of work, not one large file read
  once.
- **Day 2 needs none of it.** The afternoon repeats none of day 1's facts or rules (the selftest checks the spec and the
  messages against the pattern of each), so on day 2 it is context that a resume carries and does not use, as most of
  yesterday is on the working machine.
- **It is a harder day for LR Memory.** Its nightly pass reads only what the user typed and writes at most six changes
  a pass; on shelf's short day it wrote six in chain 2 and five in chain 3. The afternoon's two limits, stated as facts,
  and what else the user says compete with the morning's facts for those six places, and its turns compete with the
  morning's for the cue, with words that day 2's first message shares ("shelf", "desk"). On the short day, the printer
  reached day 2 in chains 2 and 3 through the memory file alone.
- **Each chain keeps its morning.** Resuming the morning's session, as a user does after lunch, keeps stage 1's three
  mornings, so day 1 costs only the afternoon, and each chain is paired with its own short day.

The nightly pass now reads back to day 1's start (`lrm.py sleep --hours`), for every job. On a user's machine it reads
everything since its last pass; here each arm L starts with no pass behind it, and a first pass reads back one day.
That covered day 1 in every run so far, but not a morning run more than a day before day 2.

**Stage A, chain 2.** `run.py --job shelf --long --chains 2 --arms N`, which runs the afternoon and then N's day 2;
then `--arms L,R`. Predicted:
- The afternoon makes 35 to 80 model calls (median 50) and ends with 100k to 200k tokens of context (median 140k),
  for 2M to 9M tokens (median 4M).
- On day 2, R costs 1.0M to 3.2M tokens (median 1.65M), and N and L 0.2M to 0.45M each, so L/R is 0.07 to 0.4.
- The stage costs about 6.3M tokens (3.5M to 13M).

Stop after the afternoon if its last context is under 100k: it gets longer before anything else runs. Stop after
day 2 if L uses more tokens than R, and find out why first.

**Stage B, chains 1 and 3,** the same way: about 12.6M tokens (7M to 26M). Over the three chains, predicted:
- L uses fewer tokens than R in 3 of 3, with L/R a median 0.2 (0.07 to 0.4).
- Memory checks: R 8 to 9 of 12, L 6 to 9 of 12 (median 7), N 0 to 2 of 12. Rules: R 6 of 6, L 5 to 6 of 6,
  N at most 4 of 6.
- Paired over the chains and the six memory and rule checks, L passes where R fails at most once, and R where L fails
  0 to 4 times (median 2). If LR Memory loses one, it is most likely F3, the printer.

The token side is mostly arithmetic once the afternoon's length is known: each of R's calls carries all of yesterday.
What the run measures is the rest: how many calls each arm makes, and whether LR Memory keeps the morning's facts
through a long afternoon when a resumed session has all of them in its context.

## Stage A result (29 October 2026)

Chain 2's afternoon answered all nine messages in 34 model calls and 1,752,355 tokens. Its last call carried 71,697
tokens of context, against the 100k to 200k predicted, so the stop rule holds: L and R did not run, and the afternoon
gets longer before anything else does. N's day 2 after it cost 196,851 tokens, with 0 of 4 memory checks and 0 of 2
rules, as on the short day. The stage cost 1.95M tokens.

Against the predictions:
- 34 calls, against 35 to 80; 1.75M tokens, against 2M to 9M; N's day 2 at 0.197M, against 0.2M to 0.45M.
- The context grew by about 1,370 tokens a call, from about 25k at the end of the morning: close to the 1,800 of the
  long sessions on the working machine. What fell short is the number of calls, 34 here against a median 616 there.
  The model built the holds, the import, the operation and the page in fewer steps than predicted.

Since every call carries the context before it, a session's tokens grow with the square of its length. At 1,370
tokens a call, an afternoon that ends at 150k takes about 90 calls and 8M tokens. Resuming this afternoon where it
ended and taking it to 150k costs about 6M at the same rate, and about 3M if each call adds 3,000.

**L and R on this afternoon (written 29 October 2026, before the run).** The stop rule said the afternoon gets longer
before anything else runs. L and R run on it anyway, as a cheap early check before a longer afternoon costs 3M to 6M
more: does LR Memory keep the morning's facts and rules through nine more messages? Their tokens add a point between
the short day and a long one. Predicted, on chain 2:
- R's first call carries 71k to 74k tokens of context, and its day 2 costs 0.55M to 1.3M tokens (median 0.75M):
  9 to 15 calls, each carrying all of day 1.
- L costs 0.2M to 0.4M tokens with its nightly pass (median 0.27M), so L/R is 0.15 to 0.7 (median 0.35).
- R passes F1, F2, F3 and both rules, as on the short day. Neither arm passes C3.
- L passes 2 or 3 of F1 to F3 and 1 or 2 of the rules. If it loses one, it is most likely F3, the printer: on the short
  day it reached day 2 through the memory file alone, and the nightly pass, which writes at most six changes, now also
  reads the afternoon's two limits.
- Both runs cost about 1.0M tokens (0.8M to 1.6M).

If L keeps F1 to F3 and both rules, the afternoon gets longer next, designed with its predictions before any run. If
it loses any, what its nightly pass wrote is read first.

**Result.** L kept every morning fact and both rules through the afternoon, at 0.31 of R's tokens.

| Chain 2, after the long afternoon | N | L 0.3.1 | R |
| --- | --- | --- | --- |
| Memory checks | 0 of 4 | 3 of 4 | 3 of 4 |
| Rules kept | 0 of 2 | 2 of 2 | 2 of 2 |
| Task checks | 3 of 4 | 4 of 4 | 4 of 4 |
| Day 2 tokens | 196,851 | 191,618 | 622,146 |
| Model calls | 11 | 9 | 8 |
| First call's context | 13,936 | 15,487 | 74,094 |

Against the predictions:
- R cost 0.62M, inside 0.55M to 1.3M, in 8 calls against 9 to 15; its first call carried 74,094, just above 71k to
  74k. It passed F1 to F3 and both rules.
- L cost 191,618 with its nightly pass, just under 0.2M to 0.4M, and passed F1 to F3 and both rules, the top of what
  was predicted. Its nightly pass read all 15 messages and wrote six files, its limit: the two rules, the short
  summaries, the fee, the printer, and the afternoon's two limits together in one.
- L/R was 0.31, inside 0.15 to 0.7. No check came out differently for L and R; neither passed C3.
- The two runs cost 0.81M tokens, inside 0.8M to 1.6M.

With day 1 about three times as long (a last context of 71,697 against about 24,500), R's day 2 cost 2.5 times what
it cost after the short day (622,146 against 246,789), and L's did not grow (191,618 against 254,801). A resume's
cost follows yesterday's length; a fresh session's does not. Of R's tokens, 98.5% were cache reads, which cost a tenth
of fresh input, and its cache was warm, since day 2 ran within the hour after day 1. A day later, its first call would
write all of day 1 into the cache again.

## The evening (designed 29 October 2026, before any run)

L kept the morning's facts and rules through the afternoon, so day 1 now gets longer, as planned: by an evening after
the afternoon, so that stage A's afternoon and its three day-2 results stay as they are. The user comes back after
dinner, and chain 2's day 1 session, which the afternoon already resumed, is resumed once more, with ten messages
(`EVENING` in [shelf/days.py](shelf/days.py)) and the front desk's log of the day, which the user put into the
repository (`data/desk_log.txt`: 355 lines, 24,008 characters, from `desk_log()` in [shelf/seed.py](shelf/seed.py)).
The desk tried the holds code that day. Its log has loans, returns, renewals and holds, place_hold taking 1.9 to 3.5
seconds seven times, two staff accounts turned away at the limit of 5 holds, two titles asked for that shelf does not
hold, and three crashes when a hold already collected was cancelled. The messages ask, in turn: what went wrong at the
desk, from the log, with no code yet; the crash, with a test first; Riverside is closed on Mondays, so its 7-day pickup
skips them; the whole day's diff, walked through file by file; every Riverside row the import could not match, with
the reason; a report of waiting, ready and expired holds by title, run on Riverside's; no hold limit for staff
accounts; every test by name, and how many; place_hold timed with 5,000 holds; and a last run of the tests, with where
things stand for tomorrow's meeting.

A subagent wrote the messages from their content given in Turkish, with no tools, as before. One sentence was cut from
the fifth: it said some of Riverside's titles are not in the catalog, and none are. `OTHER` in seed.py was meant to put
three such titles into Riverside's file, but all three are in shelf's catalog. This was found while the evening was
written, after chain 2's afternoon had run on that file, so the file stays as it is and every chain reads the same.

Why this evening:
- **It reads more per call.** The afternoon added about 1,370 tokens of context a call. Half of the evening's
  messages have the model read or print something long: the log, a diff of the whole day, every test's name, the
  rows the import could not match, a report over all of Riverside's holds.
- **Day 2 still needs none of it.** The selftest checks the log and the messages against the pattern of each of day
  1's facts and rules, the count of 191 included, and finds none; and a day 2 done right, with the log in the
  repository, still passes all ten checks.
- **It is harder again for LR Memory.** Its nightly pass now reads 25 typed messages, and the evening adds standing
  facts of its own, Riverside's closed Mondays and staff accounts without the hold limit, to compete with the
  morning's for the six changes a pass can write. After the afternoon it wrote all six.

Day 2 is unchanged, and LR Memory stays at 0.3.1. `run.py --job shelf --evening --chains 2 --arms N,L,R`, pointed at
stage A's results folder, finds the afternoon kept there, resumes its session for the evening, keeps what the evening
leaves in a folder of its own, and runs the three day-2 arms from it. A run with a stub in place of `claude` went
through all of it: day 1, the afternoon, the evening, a nightly pass that read 25 messages, and the three day-2 rows.

**Predicted, on chain 2:**
- The evening makes 25 to 60 model calls (median 38) and ends with 110k to 190k tokens of context (median 140k), for
  2.8M to 8M tokens (median 4.2M).
- R's first call on day 2 carries the evening's last context and about 2,400 tokens more. R costs 8 to 10 times that
  first context, as in chain 2 on both earlier days (9.9 and 8.4): 0.9M to 2.0M tokens (median 1.25M).
- N and L cost 0.17M to 0.32M each (median 0.21M), L with its nightly pass, so L/R is 0.08 to 0.35 (median 0.17).
- R passes F1 to F3 and both rules. Neither arm passes C3. L passes 2 or 3 of F1 to F3 and 1 or 2 of the rules; if it
  loses one, it is most likely F3, the printer.
- The stage costs about 5.9M tokens (4M to 10.6M).

Day 2 runs whatever the evening's length: the evening costs more than day 2's three arms together, and each length is
one more point on what a resume costs. Stop after day 2 if L uses more tokens than R or fails a check that R passes,
and read what its nightly pass wrote first. Chains 1 and 3 would each take the afternoon and the evening, about 7.5M
tokens a chain (5M to 14M), and are not part of this stage.

## Evening result (29 October 2026)

The evening answered all ten messages in 28 model calls and 2,837,682 tokens, and its last call carried 121,649 tokens
of context. On day 2 after it, L kept every morning fact and both rules again, at 0.17 of R's tokens. The stage cost
4,843,042 tokens.

| Chain 2, after the evening | N | L 0.3.1 | R |
| --- | --- | --- | --- |
| Memory checks | 1 of 4 | 3 of 4 | 3 of 4 |
| Rules kept | 0 of 2 | 2 of 2 | 2 of 2 |
| Task checks | 4 of 4 | 4 of 4 | 4 of 4 |
| Day 2 tokens | 311,666 | 241,448 | 1,452,246 |
| Model calls | 15 | 11 | 11 |
| First call's context | 13,962 | 15,570 | 125,038 |

Against the predictions:
- The evening made 28 calls, inside 25 to 60, and ended at 121,649, inside 110k to 190k but under the median of 140k;
  its 2.84M tokens are at the bottom of 2.8M to 8M. The context grew by about 1,780 tokens a call, against 1,370 in
  the afternoon and 1,800 on the working machine. What fell short again is the number of calls.
- R cost 1.45M, inside 0.9M to 2.0M, but 11.6 times its first call's context, not 8 to 10: it made 11 calls, against 8
  after the afternoon. It passed F1 to F3 and both rules.
- L cost 241,448 with its nightly pass (7,080 of it), inside 0.17M to 0.32M, and passed F1 to F3 and both rules, the
  top of what was predicted. Its nightly pass read all 25 messages and again wrote six files, its limit. It put the
  evening's two facts, Riverside's closed Mondays and staff accounts without the limit, into the file that held the
  afternoon's two limits, so the morning's facts kept their places.
- L/R was 0.17, the predicted median. No check came out differently for L and R; neither passed C3.
- N cost 311,666, inside 0.17M to 0.32M. Its one memory check, F2, it passed without remembering: it wrote that
  yesterday's number was recorded nowhere, then noted that the same catalog gives 191 bad ISBNs without the cleanup's
  normalization, and the check finds 191 in the file.
- The stage cost 4.84M tokens, inside 4M to 10.6M.

Over the three lengths of chain 2's day 1:

| Day 2 tokens, with day 1 ending at | about 24,500 | 71,697 | 121,649 |
| --- | --- | --- | --- |
| N | 166,859 | 196,851 | 311,666 |
| L 0.3.1, with its nightly pass | 254,801 | 191,618 | 241,448 |
| R | 246,789 | 622,146 | 1,452,246 |
| L/R | 1.03 | 0.31 | 0.17 |

R's day 2 grew 5.9 times from the short day to the evening, while L's stayed between 0.19M and 0.26M, and at every
length L and R passed the same checks. N's grew from 0.17M to 0.31M: a fresh session reads more of a larger
repository. Of R's tokens, 98.9% were cache reads, with a warm cache, as after the afternoon. On the working machine, a
return carries back a median 447k tokens, 3.7 times the evening. All of this is one chain.

**Chains 1 and 3 (written 29 October 2026, before any run).** The same afternoon and evening, then the three day-2
arms: `run.py --job shelf --evening --chains 1,3 --arms N,L,R` in stage 1's results folder, which holds both chains'
mornings. At chain 2's rates, each chain costs about 6.6M tokens. Predicted:
- Each chain's day 1 ends at 90k to 170k tokens of context (median 120k); its afternoon and evening make 45 to 110
  calls together (median 62).
- On day 2, R costs 0.8M to 3M a chain (median 1.4M), L 0.18M to 0.32M with its nightly pass, N 0.2M to 0.4M.
- Over the three chains, L uses fewer tokens than R in 3 of 3, with L/R a median 0.17 (0.08 to 0.35).
- Memory checks: R 8 or 9 of 12, L 7 to 9 of 12 (median 9), N 0 to 3 of 12. Rules: R 6 of 6, L 5 or 6 of 6, N 0 to 2
  of 6. Neither L nor R passes C3.
- Paired over the three chains and the six memory and rule checks, L passes where R fails at most once, and R where
  L fails 0 to 2 times (median 0).
- The two chains cost about 13M tokens (9M to 22M).

Stop a chain if a part of its day 1 leaves a turn unanswered. After day 2, if L uses more tokens than R or fails a
check that R passes, read what its nightly pass wrote first.

## Chains 1 and 3 result (29 October 2026)

Both chains answered every turn of the afternoon and the evening, and the two cost 10,735,371 tokens. Over the three
chains, after the evening:

| After the evening, chains 1–3 | N | L 0.3.1 | R |
| --- | --- | --- | --- |
| Memory checks | 1 of 12 | 9 of 12 | 9 of 12 |
| Rules kept | 2 of 6 | 6 of 6 | 6 of 6 |
| Task checks | 11 of 12 | 12 of 12 | 12 of 12 |
| Day 2 tokens | 216,713; 311,666; 294,088 | 266,531; 241,448; 203,926 | 1,090,033; 1,452,246; 970,057 |
| Model calls | 11, 15, 15 | 11, 11, 9 | 9, 11, 9 |
| First call's context | 14,257; 13,962; 13,964 | 15,612; 15,570; 15,563 | 116,311; 125,038; 103,590 |

Against the predictions:
- Day 1 ended at 114,307 and 102,341 tokens of context, inside 90k to 170k and under the median of 120k. The
  afternoon and the evening made 56 and 55 calls, inside 45 to 110 and under the median of 62.
- R cost 1.09M and 0.97M, inside 0.8M to 3M and under the median of 1.4M. L cost 0.27M and 0.20M with its nightly
  pass, inside 0.18M to 0.32M, and N 0.22M and 0.29M, inside 0.2M to 0.4M.
- L used fewer tokens than R in 3 of 3 chains, with L/R 0.24, 0.17 and 0.21: a median of 0.21, against 0.17
  predicted, inside 0.08 to 0.35.
- Memory checks: L 9 of 12 and R 9 of 12, the top of what was predicted, and N 1 of 12, that one by recomputing
  (above). Rules: L and R 6 of 6, N 2 of 6. Neither L nor R passed C3.
- Paired over the three chains and the six memory and rule checks, L and R never differed, against at most once and
  0 to 2 times predicted. Each passed 12 where N failed, and N none where they failed (two-sided sign test p = 0.0005).
- The two chains cost 10.7M tokens, inside 9M to 22M.

N's two rules in chain 1 came from Claude Code's own memory: on chain 1's morning, the model wrote the two rules and
the complaint about long summaries into its memory folder, as in stage 1. LR Memory's nightly pass, which writes to
the same folder, found them there in that chain, updated the summaries file and added four facts: the fee, the
printer, the pickup window with Riverside's Mondays, and the hold limit.

**What the tokens cost.** About 99% of R's tokens were cache reads, which the API prices at a tenth of fresh input.
Weighted as the API prices them (fresh input 1, a cache write 1.25, a cache read 0.1, output 5), with L's nightly pass
priced as if it ran on the same model rather than the smaller one it used, L cost 0.54, 0.36 and 0.51 of R. That is
with R's cache warm, since day 2 ran within minutes of the evening. A day later, R's first call would write into the
cache what it here read from it; priced that way, L cost 0.26, 0.20 and 0.25 of R.

**So far.** On shelf, LR Memory kept what a resumed session kept: the same checks passed in each of the three chains
after the evening, and in chain 2 at each of three lengths of day 1. Its day 2 did not grow with day 1, at 0.20M to
0.27M tokens, while a resume's did, to 0.97M to 1.45M after a day 1 that ended at 102k to 122k tokens of context:
0.17 to 0.24 of R in tokens, 0.20 to 0.26 priced with a cold cache, and 0.36 to 0.54 with a warm one. Claude Code
alone in a fresh session kept 1 of 12 facts, that one by recomputing, and 2 of 6 rules. All of it is one job, written
for this bench, in three chains.

## Limits

- Day 1 here ends at 121,649 tokens of context at the longest. On the working machine, a return carries back a median
  447k, 3.7 times as much, and the saving there should be larger; this bench does not measure it.
- In money, a cache read costs a tenth of fresh input, so a resume costs less than its tokens suggest. The bench
  reports tokens, with their kinds.
- 11 chains in three jobs, all written for this bench.
- Every session here has a 1M-token window, as on the working machine. With Claude Code's default window of 200k, a
  long day would be compacted, and a resume would carry its summary and the turns after it: another arm, not measured.
- A session kept open all day is a third way. The long-session bench measured it: Claude Code's own smaller window
  saved 24–27% with nothing lost. That saving is Claude Code's, not LR Memory's.
