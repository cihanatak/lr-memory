# A rule for the replies: why "keep summaries short" did not last, and the fix

C3 asks for short answers on day 2: the median of day 2's three answers is 100 words or fewer. On day 1 the user
complained once ("your last summary was way too long and hard to follow. Please keep summaries short.", and the same in
the other two jobs) and never gave a number. In the three jobs' runs, both arms failed C3 almost every time, with LR
Memory as without it. This file finds out why, from the runs' records first, and tests a fix.

## What the records say (no model tokens)

30 day-2 sessions in the three jobs' runs (ledgerly 18, kargo 6, shelf 6), both arms and every LR Memory version:

| Day 2 | Sessions | C3 passed | Answer length, median of the sessions' medians | End-of-day summary, median |
| --- | --- | --- | --- | --- |
| The rule in MEMORY.md | 19 | 1 | 155 words | 200 words |
| The rule not in MEMORY.md | 11 | 0 | 202 words | 256 words |

- No day-2 session read a memory file (0 of 30). What the model had of the rule was its line in MEMORY.md, the one
  memory file Claude Code loads by itself, at the start of the session.
- Claude Code alone kept the rule in its own memory in 5 of its 11 day-2 sessions and passed C3 in 1 of those 5.
- On day 1, in the same session, right after the complaint, the median of the next three answers was 100 words or
  fewer in 8 of 11 chains (median 89 words).
- Day 1's last message asks for "a short summary" in so many words. Those summaries had a median of 113 words, and
  only 1 in 11 was 100 words or fewer.

So on day 2 the rule is known and barely acted on. With it in MEMORY.md the answers were a quarter shorter than
without it (155 words against 202); right after the complaint on day 1 they were 89.

## Three explanations

1. **Distance.** On day 2 the rule is one line at the top of the session, and the reply is written after dozens of
   tool calls. On day 1 the complaint was a few turns back. Prediction: with the rule next to every prompt, day 2
   comes close to day 1 after the complaint.
2. **The work.** Day 2's work needs long answers. Prediction: the rule next to the prompt changes little.
3. **The check.** To the model, "short" means about 110 words even when the user says "short" in the same message,
   so a 100-word median fails anyway. Prediction: answers shorten, and C3 still fails where the summary carries the
   median.

## The fix: LR Memory 0.3.2

- The nightly pass marks a directive about the replies themselves (their length, language, tone or format) as a
  reply rule. When a memory file already covers it, the pass appends the user's words to it and marks that file. The
  marks live in LR Memory's own data (`sleep/replies.json`), so Claude Code's files gain no new fields.
- The cue puts the text of every marked file in front of the model with every prompt, above the turns it brings back:
  at most 4 rules, 400 characters each. It costs no model tokens; the context gains about 100 tokens per prompt.
- Nothing in it names a length: the rule is the one the pass wrote from the user's words.

## The test

Day 2 runs again, with LR Memory 0.3.2 only, on the day-1 records the three jobs' runs kept, in their own folders.
The other arms' rows are reused: Claude Code alone, and the LR Memory version that ran before (0.3.1 for
shelf, 0.3.0 for kargo and ledgerly). The jobs were not held out: their C3 records are what this file starts from.

**Pilot, shelf (3 chains).** Predicted in the run command before it started: C3 in at least 2 of 3 (0.3.1: 0 of 3);
end-of-day summary median 130 words or fewer (0.3.1: 176); about 0.78M tokens (0.6–1.0M). Stop rule: if the summaries
stay above 150 words or C3 passes in none, stop; distance is then not the cause.

**A pilot that did not count.** The first pilot ran in a copy of the shelf run's folder. Claude Code names a project
after its working folder, so day 2 in the copy found neither day 1's sessions nor its memory: memory 0 of 12, rules 0
of 6, and the cue showed no turn. It cost 627,224 tokens and says nothing about the fix. Day 2 now runs in the folder
that holds its day 1. Before the second attempt, the sleep pass alone on the three day-1 records (14,711 tokens)
marked the short-summary rule in 3 of 3 passes, and for day 2's first prompt the cue put it at the top in 3 of 3.

**Pilot result (29 October 2026).** Every other check held as with 0.3.1: memory 9 of 12, rules 6 of 6, task 10 of
12. The nightly pass marked the rule in 3 of 3 chains. The run's records do not keep what the cue said; on the same
day-1 records, the probe above saw it put the rule at the top of day 2's first prompt. C3 passed in none (predicted
2 of 3):

| Shelf, day 2 | Claude Code alone | 0.3.1 | 0.3.2 |
| --- | --- | --- | --- |
| C3 | 0 of 3 | 0 of 3 | 0 of 3 |
| The sessions' median answers, words | 134, 155, 191 | 120, 128, 148 | 103, 123, 141 |
| End-of-day summaries, words | 239, 254, 267 | 142, 176, 229 | 142, 144, 150 |
| Day-2 tokens with the sleep pass, median | 212,052 | 254,801 | 277,368 |

- What carried the median was the report on the first item (103–141 words); the answers on the second were 40–78.
- The summaries came out at 142–150 words, against the 130 or fewer predicted; the longest one shrank, the others did
  not. By chain, the sessions' medians went up in two chains and down in one.
- Chain 1 cost 443,859 tokens, the most of any day 2 in this job.

The stop rule held, so the second stage did not run. The rule next to every prompt does not bring day 2 back to day 1:
reminded of "short" with no number, the model writes about 140 words. Distance is not the whole cause.

## Second attempt: LR Memory 0.3.3

What "short" meant to this user is in the record: the reply they complained about, and the replies they took
without a word after it. 0.3.3 puts those lengths next to the rule.

- When the nightly pass marks a reply rule, it reads the transcript around the first message of the day that the
  rule cites: the reply before it, and up to ten replies from that message on, each the last text of its turn. The
  lengths are kept with the mark.
- The cue gives them after the rule's text, for example: "When the user said this, the reply before it had 173 words;
  the 4 replies from then on had 43–115 words, median 62." No length comes from the plugin: the numbers are the
  record's.
- The pass costs what it did; the cue gains about 30 tokens per rule.

**Pilot, shelf (3 chains), predicted before it ran.** From the day-1 records, the cue should give: chain 1, 173
words before, 43–115 after, median 62; chain 2, 83 before, 49–106 after, median 70; chain 3, 112 before, 36–161
after, median 74. Predicted: C3 in 2 of 3 (1 to 3; 0.3.2: 0 of 3); the sessions' median answers 100 words or fewer in
at least 2 of 3 (0.3.2: 103, 123, 141); end-of-day summaries 120 words or fewer, median (0.3.2: 144); memory 9 of 12,
rules 6 of 6 and task 9 or more of 12, as before; about 0.85M tokens (0.6–1.1M). Stop rule: if C3 passes in none,
the number is not enough either, and the second stage does not run.

Before the pilot, the sleep pass alone on the three day-1 records (14,530 tokens) marked the short-summary rule in 3
of 3 passes, with exactly the lengths above, and the cue for day 2's first prompt gave them in 3 of 3.

**Pilot result (29 October 2026).** In the pilot, too, the nightly pass marked the rule in 3 of 3 chains. Memory 9 of 12,
rules 6 of 6 and task 10 of 12 held. C3 passed in none (predicted 2 of 3), and the answers were no shorter than
with 0.3.2:

| Shelf, day 2 | Claude Code alone | 0.3.1 | 0.3.2 | 0.3.3 |
| --- | --- | --- | --- | --- |
| C3 | 0 of 3 | 0 of 3 | 0 of 3 | 0 of 3 |
| The sessions' median answers, words | 134, 155, 191 | 120, 128, 148 | 103, 123, 141 | 113, 129, 138 |
| Last answers of the day, words | 239, 254, 267 | 142, 176, 229 | 142, 144, 150 | 113, 139, 152 |
| Day-2 tokens with the sleep pass, median | 212,052 | 254,801 | 277,368 | 235,206 |

- The median was carried by the report on the first item (129–138 words) and by the last answer (113–152). The
  last answer reports the audit and then sums up the day, as the third message asks. The answers on the second
  item were 50–71 words.
- Read in full, the long answers hold what was asked for: what changed, the tests, the decision not to rename
  anything in `shelf/api.py`, the changelog lines, the audit count. On day 1, the user's last message asked for "a
  short summary" in so many words, and those summaries had a median of 113 words.
- The pilot cost 767,014 tokens.

The stop rule held again. The rule came with every prompt, with the lengths the user took on day 1 beside it, and the
answers were no shorter than with the rule alone. On this job the length follows what the model judges an answer has
to say, and C3's 100 words is below that even when the user says "short" in the same message. On this evidence C3
measures the model, not its memory: no arm passes it, so it does not tell the arms apart.

## What ships

Neither change. 0.3.2 and 0.3.3 add a rule to every prompt and passed C3 in none of 6 chains. Their summaries were
shorter than 0.3.1's in these pilots, but by too little and over too few chains to show an effect. LR Memory stays
at 0.3.1. C3 stays in the bench as it was: changing a check after seeing it fail would fit the check to the result.
