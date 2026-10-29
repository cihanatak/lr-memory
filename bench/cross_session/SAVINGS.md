# Remember or resume: what LR Memory saves

Claude Code alone has two ways to start the next day. A fresh session with its own memory is cheap and forgets:
that is this bench's arm N. Resuming yesterday's session remembers everything, because every call carries all of
yesterday. The claim to test is that LR Memory gives what a resumed session remembers at what a fresh session costs.
This file finds where the tokens go first, from records that already exist, then sets out the experiment with its
predictions, written before any run.

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

## Limits

- Day 1 here is short. On a real day, the context carried back is more than ten times larger, and so should be the
  saving; this bench does not measure that.
- In money, a cache read costs a tenth of fresh input, so a resume costs less than its tokens suggest. The bench
  reports tokens, with their kinds.
- 11 chains in three jobs, all written for this bench.
- A session kept open all day is a third way. The long-session bench measured it: Claude Code's own smaller window
  saved 24–27% with nothing lost. That saving is Claude Code's, not LR Memory's.
