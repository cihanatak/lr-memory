# Remember or resume: what LR Memory saves

Claude Code alone has two ways to start the next day. A fresh session with its own memory is cheap and forgets:
that is this bench's arm N. Resuming yesterday's session remembers everything, because every call carries all of
yesterday. The claim to test is that LR Memory gives what a resumed session remembers at what a fresh session costs.
This file finds where the tokens go first, from records that already exist, then sets out the experiment with its
predictions, written before any run, and stage 1's result.

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

## Limits

- Day 1 here is short. On a real day, the context carried back is more than ten times larger, and so should be the
  saving; this bench does not measure that.
- In money, a cache read costs a tenth of fresh input, so a resume costs less than its tokens suggest. The bench
  reports tokens, with their kinds.
- 11 chains in three jobs, all written for this bench.
- A session kept open all day is a third way. The long-session bench measured it: Claude Code's own smaller window
  saved 24–27% with nothing lost. That saving is Claude Code's, not LR Memory's.
