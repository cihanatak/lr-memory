---
name: recall
description: Finds how something was done, decided, measured or said in earlier Claude Code sessions, from the word-for-word record of every past session (the user's messages, the assistant's notes, commits, commands, compaction summaries, subagent reports and memory files), and answers with the source instead of guessing. Use whenever the user points to the past, such as "how did we", "last time", "what did we decide", "do you remember", "in the previous session", "what was that", "which commit", "when did we", "nasıl yapmıştık", "daha önce", "geçen sefer", "ne karar vermiştik", "hatırlıyor musun" or "hangi commit". Use it yourself, unasked, before redoing, assuming or guessing anything that was done, decided or measured earlier and is not in the current context, such as after a compaction, in a session about an old project, or when a past number or reason is needed. Not for how the code is now; read the code for that.
---

# Recall: find it in the record, don't guess

Claude Code keeps every past session word for word in `~/.claude/projects/*/*.jsonl`. lr-memory keeps a local search index over them. The index covers the user's words, the assistant's notes and answers, commits, command descriptions, compaction summaries, subagent reports and the memory files. A search costs no model tokens and usually takes under a second. It prints a few short hits, each with its local date and time, session and row.

## Steps

1. **Choose the words the record would contain, not the question.** Rare words work best: file, function and command names (`keyscan.py`, `listed_commits`), error text, numbers, commit hashes, and the user's own phrasing. Use two to five words per query.
2. **Search with two or three variants in one Bash call.** Vary the language, try a synonym, add a file name:
   ```bash
   sh "${CLAUDE_PLUGIN_ROOT}/scripts/run.sh" search comparator unit minutes; sh "${CLAUDE_PLUGIN_ROOT}/scripts/run.sh" search compare predict.py --kind commit,assistant
   ```
   When there are too many hits, narrow them:
   - `--kind`: user, assistant, commit, step, summary, report, memory or prompt
   - `--since 2026-10-20`
   - `--session 3f2a9c1e`
   - `-k 5`
3. **Open the one or two hits that look right**, for example `sh "${CLAUDE_PLUGIN_ROOT}/scripts/run.sh" show 3f2a9c1e:5852`. This prints the turn around that row: what the user and the assistant wrote, plus the commands and files right next to it. Tool output is left out.
4. **Answer from what you read, and cite it.** Give the date and time, the session (first 8 characters) and the commit hash when there is one. Quote the user's words exactly when they matter. If the record and today's code disagree, say so; the code is what is true now.
5. **If three variants find nothing, say so.** Name what you searched and say it was not in the record. Do not fill the gap from general knowledge or from what seems likely.

## How matching works

- **Word forms.** Letters are folded (ı→i, ş→s, ç→c, ğ→g, ö→o, ü→u, accents dropped) and each word is cut to its first five letters, so `düzeltmiştik` also finds `düzeltme` and `comparator` finds `compare`. A hit with the whole word ranks above one with only the cut form.
- **Short words.** Two-letter words (db, ui, js) match only as whole words.
- **Names.** A name containing `_`, `.` or `-` (`listed_commits`, `predict.py`, `58.2`) is matched as the whole name.
- **Ranking.** A hit scores by how rare its matching query words are, so one exact name outweighs several common words. A long query of common words ranks noise; prefer fewer, rarer words.
- **Scope.** Hits come from all projects. A `prompt` hit is a script's prompt (`claude -p`, the Agent SDK), not the user's words.
- **Freshness and keys.** Each search first indexes whatever was written since the last one. The first search on a long history may say the index is still being built; search again to cover the older sessions. Key-shaped strings are masked as `[secret]`.

## Cost

A search prints about 0.4–1.2 KB, a few hundred tokens. A `show` prints up to about 7 KB. Grepping the raw `.jsonl` files instead prints every matching JSON row with its tool output (0.3–4.5 MB for the same words in one measured history) and misses other word forms.
