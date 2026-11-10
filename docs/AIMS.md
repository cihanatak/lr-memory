# The 13 aims

[Türkçe](AIMS.tr.md)

Living Runtime does not try to add intelligence to Claude Code. It tries to make better use of the intelligence that is already there: to remember, to check itself, and to find the cause when something fails. That comes to thirteen aims in three parts. Each aim has a yardstick, and a status that is written only after a measurement.

- **LR** (memory, aims 1 to 7) is in this repository as the `lr-memory` plugin.
- **COL**, the Cognitive Operating Loop (self-check, aims 8 to 10), is in this repository as the `col` plugin.
- **scnc** (finding causes, aims 11 to 13) is the author's skill for an unknown cause: rival explanations, one cheap experiment that tells them apart, a fix at the root. Its automatic part ships inside `col`, as the check that asks for rival explanations when a fix does not hold.

The [mind panel](../plugins/mind/README.md) shows these aims with live numbers from your own files.

## Where they stand

As of 2026-11-11: **2** works · **4** partial · **4** fails · **2** unused · **1** unclear.

The author's own machine, the full private system (LR, COL, scnc) of which these plugins are a part. Record before 7 Nov 2026: 14 labelled nights, 471 operator messages, 74 corrections. Since 7 Nov a 28-day on/off experiment is running; its numbers are sealed until 5 Dec.

Not every aim holds yet, and this page says which. The measurements were made on the author's own record, with one reader; they are not a benchmark.

### LR: memory

| # | Aim | Status | Yardstick | Last measurement |
| --- | --- | --- | --- | --- |
| 1 | The conversation never closes; compaction loses nothing | ✕ fails | Share of old information still at hand after compaction | After one compaction Claude Code's own summary loses nothing either, so LR adds 0. After repeated compactions about 90% of the operator's old messages are carried by neither; the note adds about 2 points. |
| 2 | What happened is kept word for word and found when needed | ◐ partial | Is the source among the top 3 results | 8 of 9 questions; with real messages as the query, 3 of 8 exact and 3 partial. |
| 3 | Corrections and confirmed lessons become rules | ✓ works | How many corrections produced a rule | At least 24 of 74 corrections produced a rule or an addition to one (a lower bound; one reader). |
| 4 | A rule comes back on its own at the moment it applies | ✕ fails | When a rule existed and the correction still came, had the rule been brought back | In 3 of the 57 corrections that had a rule beforehand, that rule's reminder had come in the previous 24 hours; 15 rules ever got a reminder. |
| 5 | Consolidates at night and lets the useless fade | ◐ partial | Rules written and rules retired | 32 rules written in 16 nights; files went from 408 to 452 and never-opened ones from 210 to 242; nothing was retired. |
| 6 | The same mistake is not made twice | ✕ fails | Corrections whose rule was already written | 24 of 74 (32%); in 33 more a related but more general rule existed. |
| 7 | Context stays small and quality does not drop | ◐ partial | Context per call, and the correction rate | 518.8k to 236.4k tokens per call (-54%), most of it from Claude Code's own setting; the correction rate did not change significantly. |

### COL: self-check

| # | Aim | Status | Yardstick | Last measurement |
| --- | --- | --- | --- | --- |
| 8 | Work that was not done is never reported as done | ✓ works | Claims that do not hold: caught, and reaching the operator | 15 caught in 1,370 turns; 1 of the operator's 74 corrections was of this kind. |
| 9 | What is really wanted is understood and the work goes that way | ✕ fails | Corrections for misunderstanding | 18 of 74. The end-of-turn referee: 369 looks, 13 turned back, 1.79M tokens; it caught 0 of 7 known misses. |
| 10 | A prediction before a big step, a comparison after; what is forbidden stays protected | ◐ partial | Predictions on record and compared, forbidden writes stopped | 820 predictions recorded; 371 compared by number (146 held, 225 missed), 139 could not be compared, 310 have no result; 6 forbidden writes stopped. |

### scnc: finding causes

| # | Aim | Status | Yardstick | Last measurement |
| --- | --- | --- | --- | --- |
| 11 | No jumping to the first explanation; rivals are set up | ○ unused | Hypothesis lines | 3 lines, all in one session, 24 Oct to 7 Nov; none recorded by the ledger. |
| 12 | A cheap experiment decides | ○ unused | Use of the experiment step | Not used. |
| 13 | The fix goes to the root cause and is verified with the same measurement | ? unclear | A second failure in a row going on to a third | October: 33 of 127 (26%). 30 Oct to 7 Nov: 1 of 11 (9%), not separable (p = 0.19). "Verified with the same measurement" is not measured. |

## The brain regions are an analogy

The panel puts each aim on a brain region. It is a way to read the system, not a claim about brains.

| # | Aim | Region and what it stands for |
| --- | --- | --- |
| 1 | The conversation never closes; compaction loses nothing | Dorsolateral prefrontal cortex, keeps working memory up |
| 2 | What happened is kept word for word and found when needed | Hippocampus, episodic memory and recall from a cue |
| 3 | Corrections and confirmed lessons become rules | Anterior temporal neocortex, semantic memory |
| 4 | A rule comes back on its own at the moment it applies | Basal ganglia, habits triggered by a cue |
| 5 | Consolidates at night and lets the useless fade | Thalamocortical spindles and hippocampal–cortical replay in sleep |
| 6 | The same mistake is not made twice | Cerebellum, supervised learning from error |
| 7 | Context stays small and quality does not drop | Posterior parietal cortex, selection by attention |
| 8 | Work that was not done is never reported as done | Anterior cingulate cortex, error and conflict monitoring |
| 9 | What is really wanted is understood and the work goes that way | Temporoparietal junction and medial prefrontal cortex, reading another's intent |
| 10 | A prediction before a big step, a comparison after; what is forbidden stays protected | Orbitofrontal cortex and inferior frontal gyrus, expected outcome and inhibition |
| 11 | No jumping to the first explanation; rivals are set up | Frontopolar cortex, holding alternatives in reserve |
| 12 | A cheap experiment decides | Locus coeruleus, switching to exploration under unexpected uncertainty |
| 13 | The fix goes to the root cause and is verified with the same measurement | Midbrain dopamine cells, updating from prediction error |

## Status words

- **✓ works**: measured, and it holds
- **◐ partial**: measured, and part of it holds
- **✕ fails**: measured, and it does not hold
- **○ unused**: the mechanism is there and is not being used
- **? unclear**: measured, and the numbers cannot tell
- **· not measured**: no measurement; the panel shows this for every aim until you keep a scorecard

## Your own scorecard

The statuses above are the author's. On your machine the panel shows every aim as not measured until you keep a scorecard: a JSON file at `~/.claude/mind/scorecard.json` (or `--scorecard FILE`) in the shape of [scorecard.json](scorecard.json). A text field may be one string or `{"en": …, "tr": …}`.
