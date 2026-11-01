# LR Memory

A fresh Claude Code session knows nothing of yesterday. LR Memory brings yesterday back, from the transcripts Claude Code already keeps on your machine.

- **The cue.** Before Claude reads a prompt, a hook searches this project's earlier sessions with the prompt's words and puts the turns it brings back in front of Claude, word for word: three at most, each once a session. No model call.
- **The note.** Right before a compaction, your last messages, the open tasks, the changed files, the commits and the latest test results are kept word for word. Right after, a short note made from them goes back into the fresh context.
- **Recall.** A local SQLite FTS5 index over every past session. The `recall` skill searches it before redoing or guessing anything that happened earlier, and answers with the date, the session and the commit.
- **Sleep, when you turn it on.** Once a day, or when you run `/lr-memory:sleep`, the rules, corrections and facts you stated go into Claude Code's own memory folder, each backed by your own words. It is the one part that calls the model.

On the author's cross-session bench (Sonnet 5.5, five chains), a fresh day-2 session passed 12 of 20 memory checks with LR Memory and 3 of 20 with Claude Code alone, at the same tokens. The benches, and what they do not show: [Measured on the author's machine](https://github.com/cihanatak/lr-memory#measured-on-the-authors-machine).

## Install

```
/plugin marketplace add cihanatak/lr-memory
/plugin install lr-memory@living-runtime
```

Then restart Claude Code. It needs Python 3.9 or newer and `sh`; on Windows, Claude Code runs hooks with Git Bash, which provides it. Everything LR Memory keeps is in `~/.claude/lr-memory`, and key-shaped strings are masked before they are indexed.

Documentation, configuration and removal: [github.com/cihanatak/lr-memory](https://github.com/cihanatak/lr-memory). MIT licensed.
