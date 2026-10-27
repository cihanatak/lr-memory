![Living Runtime: LR Memory and COL, open-source plugins for Claude Code](https://raw.githubusercontent.com/cihanatak/lr-memory/main/assets/banner.jpg)

# COL for Claude Code

[![tests](https://github.com/cihanatak/lr-memory/actions/workflows/tests.yml/badge.svg)](https://github.com/cihanatak/lr-memory/actions/workflows/tests.yml)

[Türkçe](README.tr.md)

An agent can end a turn with "Done, all 12 tests passed" when no test ran, name a commit that does not exist, or commit a key it was never meant to commit. Asking the model to check itself does not fix this. Without an outside signal, self-correction does not make answers more accurate (Huang et al., [arXiv 2310.01798](https://arxiv.org/abs/2310.01798)). Agents also rate their own chances far too high: "some agents that succeed only 22% of the time predict 77% success" (Kaddour et al., [arXiv 2602.06948](https://arxiv.org/abs/2602.06948)).

COL brings the outside signal. It checks what can be checked against what ran and what exists:

1. **A claim check whenever Claude stops.** COL reads the last message and checks each claim it can:
   - A commit it names must exist.
   - A file it cites must be on disk.
   - A test count it gives must appear in real test output from the session.
   - "Done, I fixed it" needs a tool run in the turn, and "committed" needs a commit command or a commit id.

   A false claim blocks the stop and lists what is not backed. Claude then shows the evidence or takes the claim back. COL blocks at most twice per turn, so it can never trap a session.
2. **A prediction ledger.** Some commands do not start until their description holds a measurable prediction:
   - a background job;
   - a step that cannot be taken back, such as `git push`, a publish, a deploy or a Kaggle submission.

   The prediction looks like `Prediction [key]: <what> <number or range> (~<time>)`, and COL records it. Later, Claude writes `Result [key]: <observed>`. COL compares the two from the numbers, like with like: a duration with a duration, a percentage with a percentage, a count with a count of the same thing. A result counts as grounded only when its number appears in real tool output. When a prediction comes due, COL asks for its result once, at the next prompt. A new session in a folder starts with that folder's record.
3. **A key scan before every commit and push.**
   - A commit is judged on what it will record. That covers the staged diff, the changes `-a` picks up, and the files that a `git add` earlier in the same command is about to stage.
   - A push is judged on the commits that no remote has yet.
   - A hit stops the command. COL names the file, the line, the kind of key and a fingerprint, but never shows the key itself.
4. **A question when a fix does not hold.** Sometimes a test run, a build or a type check fails, a file is edited, and the check fails again the same way. Then the edit changed nothing the check sees, and the next guess is usually built on the same wrong idea. At that moment COL asks Claude, once for that check, for two explanations that both fit. One of them must put the cause outside the edited code: a stale copy or cache, the environment or a config file, another definition or file being run, or a wrong test. Claude is also asked for one cheap command that tells the two apart. A check that still fails after two edits gets the same question. A test that is skipped or loosened while its check fails gets a one-line note.

All of this is mechanical: six hooks, one skill and Python's standard library. COL makes no model calls. The only tokens it adds are the short rules at session start and the text of a reminder, a block or a refusal.

## Install

In Claude Code:

```
/plugin marketplace add cihanatak/lr-memory
/plugin install col@living-runtime
```

Then restart Claude Code, since hooks are loaded when it starts. COL does not depend on LR Memory, the other plugin in this marketplace. You can install either one or both.

**Requirements:**
- Claude Code. Tested with 2.1.308.
- Python 3.9 or newer on `PATH` as `python3`, `python` or `py`.
- `sh`, which macOS and Linux have. On Windows, Claude Code runs hooks with Git Bash, which provides it.
- `git` on `PATH`, for the commit lookups and the key scan.

## Use

COL needs nothing from you. This is what Claude sees when a claim does not hold. The text is taken from a real session:

```
COL: these claims in your last message are not backed by what ran or what exists:
- 'all 12 tests passed' is said, but no real test output shows 12 passing tests
- no tool ran in this turn, yet the message says new work was done
Fix the message: show the evidence, or take the claim back.
```

A long job starts with its prediction in the description:

```
Run the suite. Prediction [tests]: 41 passed, 0 failed (~2 min)
```

The reply that reports the result carries the observed value:

```
Result [tests]: 41 passed, 0 failed in 2.1 min
```

The Turkish forms `Öngörü [anahtar]: …` and `Sonuç [anahtar]: …` are read the same way.

A `Hypothesis [key]: …` names one rival explanation under test. A hypothesis whose result misses is ruled out, and it does not count against the model's calibration.

**The report:** ask "COL report" or run `/col:report`. It shows the last 30 days:
- how many finished turns the claim check read, flagged and blocked, and how the blocks turned out;
- how the predictions did: how many held or missed, which way the misses went, and which ones still wait for a result;
- what the key scan stopped.

## What COL checks, exactly

- **Commits:** a 7–40 character hex id next to the word "commit". COL looks it up in the repositories it can reach:
  - the working folder and the repositories right under it;
  - any repository a tool call in the turn worked in;
  - any repository the message cites;
  - the folders `COL_REPOS` names.

  With no repository in reach, it checks nothing.
- **Files:** absolute paths in backticks, and the targets of Markdown links.
  - A relative link is looked up from the working folder and its parents, from the session's memory folder, and among the files the turn touched.
  - A path the message says was deleted is not checked.
  - URLs, anchors, API routes and slash commands are not treated as paths.
- **Test counts:** claims like "12 tests passed", "all 12 tests pass", "3 of 5 tests passed", "12 passed" and "12 test geçti". COL compares them with what test runners print:
  - "N passed" (pytest, vitest, jest, playwright, cargo);
  - "N passing" (mocha);
  - "pass N" (node --test, TAP);
  - "Passed: N" (dotnet);
  - "Ran N tests … OK" (unittest).

  A count that is denied, withdrawn or asked about is not a claim.
- **Work with no action behind it:** a message that opens with "done" and names new work when no tool ran in the turn. Also "committed" when no commit ran and no commit id is given. Neither is flagged if the message says the work was done earlier.
- **Steps that cannot be taken back:**
  - `git push` (except with `--dry-run`), `git reset --hard`, `git clean -f`;
  - `gh release create`, `gh pr merge`, `gh repo delete`;
  - `npm`/`pnpm`/`cargo`/`poetry publish`, `yarn npm publish`, `twine upload`, `docker push`;
  - `terraform apply`/`destroy`, `kubectl apply`/`delete`;
  - `firebase deploy`, `vercel --prod`, `netlify deploy --prod`, `gh-pages -d`;
  - `kaggle competitions submit`, `kaggle kernels push`, `kaggle datasets create`/`version`.

  Text inside a heredoc or a quoted commit message is not a command. Waits, watchers and dev servers run in the background without a prediction, because they have no result to predict.
- **Fixes that did not hold:**
  - A check is a run of pytest, unittest, vitest, jest, mocha, tsc, `playwright test`, `node --test`, cargo, go, `npm`/`pnpm`/`yarn` test, build, lint or typecheck, dotnet, mvn, gradle, ruff, mypy, eslint, flake8 or pyright.
  - A run fails when it exits with an error or its output reports failures, so `| tail` hides nothing.
  - The failure is named by the failing tests when the runner lists them (pytest's short summary), else by its error lines. So `| tail -3` and `| tail -40` show the same failure.
  - An edit is an Edit, Write or MultiEdit call, or a shell command that writes a file (`sed -i`, `git checkout`, `> file.py`, …). A rerun with nothing edited is not a fix.
  - A run of the same tool continues a check when it runs every file or some of the same files. Other tests failing make a check of their own.
  - A refused or interrupted command is not a failure.
  - Adding `pytest.mark.skip`, `xfail`, `approx(`, `except Exception`, `# type: ignore`, `@ts-ignore` and the like to a test file while a check fails gets the note.
- **Keys:** keys from Anthropic, OpenAI, GitHub, GitLab, AWS, Google, Slack, Stripe (live), Hugging Face, npm and Kaggle, plus private key blocks. Files that hold secrets, such as `.env`, `id_rsa`, `*.pem` and `kaggle.json`, are flagged too, but `.env.example` is not. Only added lines count, so a commit that takes a key out goes through.

## How it works

```mermaid
flowchart LR
  S["Session start"] -->|SessionStart| R["The rules and this folder's<br/>prediction record"]
  U["Your message"] -->|UserPromptSubmit| D["Due predictions<br/>asked for once"]
  B["Bash or PowerShell call"] -->|PreToolUse| K{"A key in the<br/>commit or push?"}
  K -->|yes| X["Refused: file, line, kind,<br/>fingerprint, never the key"]
  K -->|no| G{"Background job or irreversible<br/>step without a prediction?"}
  G -->|yes| Y["Refused: write<br/>Prediction [key]: ..."]
  G -->|no| Run["Runs; its prediction<br/>goes to the ledger"]
  E["Claude stops"] -->|Stop| L["Results compared<br/>with predictions"]
  E -->|Stop| C{"Claims backed by what<br/>ran and what exists?"}
  C -->|no| Block["Stop blocked,<br/>at most twice a turn"]
  F["A check runs again<br/>after an edit"] -->|PostToolUse| Q{"The same failure, or<br/>still failing after 2 edits?"}
  Q -->|yes, once a check| A["Two rival explanations<br/>and one cheap command"]
```

**Design choices:**
- **Mechanical, not a judge.** A model asked to judge another model's work spends tokens on every turn and is wrong often enough to cost more than it saves (see below). COL checks only claims that can be checked against files, git and tool output. "The code is cleaner now" goes unchecked.
- **The record goes back to the model.** A prediction is useful only if its outcome is seen again. That is why a due result is asked for, and why each session starts with its folder's hit rate and the direction of its misses. For example: "2 of the last 6 held; of the misses, 3 came in below the range and 1 above; durations: 3 of 6 took less time than predicted".
- **Never in the way.**
  - A failing hook exits 0 and writes to `errors.log`.
  - A key scan that breaks lets the command through.
  - Every git call has a time limit.
  - A block comes at most twice per turn.
- **Blocks are labelled.** Claude's answer to a block is read at the next stop:
  - "I missed it" or "I'm taking that claim back" marks the block right;
  - "I had already answered that in my previous message" marks it wrong.

  Only clear cues label a block, so the counts are a floor.

## What was measured, and what was left out

**Real sessions with this plugin** (Claude Code 2.1.308, Haiku, an empty isolated config, COL installed from this marketplace, a throwaway git repository):
- **A false claim.** Told to reply "Done. I fixed the bug in the parser and all 12 tests passed." without running anything, the session was blocked, and Claude took the claim back.

  Its retraction quoted the count ("no evidence that … 12 tests passed") and was blocked a second time. That second block was wrong. Quoted, denied and asked-about counts are now skipped, and this exact answer is kept as a test.
- **A key.** `git add conf.py && git commit` with a planted Anthropic-shaped key was stopped. The repository kept its single commit. The log holds the kind, the file, the line and a fingerprint, but not the key.
- **A background job.** A job started without a prediction was refused. Claude read the script and retried with `Prediction [check]: 41 passed (~1 sec)`. When the job finished, COL asked for the result and compared it with `Result [check]: 41 passed`: held, and grounded in the job's own output.
- **Cost.** The three sessions together cost 175,704 tokens, and 160,439 of them were cache reads.

**The surprise reflex, on a bench of its own.** The [bench](../../bench/README.md) has four small repositories, each with two causes, so the fix the user asks for fails again the same way. It ran with Claude Code 2.1.308 and `claude -p`: three runs per task and arm, 48 runs in all.

| | Haiku, without | Haiku, with | Sonnet, without | Sonnet, with |
| --- | --- | --- | --- | --- |
| Solved | 9 of 12 | 11 of 12 | 10 of 12 | 10 of 12 |
| Symptom patches | 1 | 0 | 0 | 0 |
| Runs where a fix did not hold | 7 | 8 | 5 | 5 |
| Runs where two fixes did not hold | 0 | 0 | 0 | 0 |
| Tool calls after the first fix that did not hold (median) | 6 | 4 | 2 | 3 |
| Tokens, all 12 runs | 1,155,100 | 1,117,115 | 738,585 | 796,250 |

- None of these differences is beyond chance at this size. For Haiku's solved runs, Fisher's p ≈ 0.6.
- Once a fix did not hold, both models looked elsewhere on their own. No run in either arm had a second fix that did not hold. That is what the reflex asks for, and the models mostly did it unasked.
- 7 of the 8 unsolved runs were in `env_override`. Each found both causes and left the deployment's `.env` for the user to change.
- In every run where the bench's count found a point to ask, the live hook asked: 7 of 7 on Haiku, 5 of 5 on Sonnet.
- In 30 days of the author's own sessions, 36 of 179 failure chains had a fix that did not hold. The tokens spent after one were 4.1% of all tokens, and the reflex works on that slice only.

So the reflex is cheap and did no harm here, but this bench does not show that it helps. On Sonnet it cost 8% more tokens. `COL_INQUIRY=off` turns it off.

**In LR, the agent runtime COL was cut out of:**
- **Claim check.** Its first three warnings, on its first day, were all false alarms. Later it read 348 finished turns and flagged 8. Of the blocks whose answers named a verdict, 1 was right and 1 was wrong; 3 answers were unclear. In red-team runs, LR's check caught every planted false claim: 120 of 120 three times, then 21 of 21 and 100 of 100.
- **Ledger.** It held 100 predictions and 57 results. Of those results, 16 held, 31 missed and 10 could not be compared. 46 of the 57 gave a number that appears in real tool output. 12 launches were stopped until a prediction was written.

  Most predictions missed, and that is the point of keeping the record: it shows which way the model's sense of time and size is off.
- **Key scan.** It stopped nothing in that period, because no key was on its way into a commit.

**Left out, because it did not work in LR:**
- **A model as judge.** LR asked a model whether each request had been met. The judge was right on 2 of its first 8 stops. Its 6 wrong stops made long sessions re-read their context: about 17 million tokens in two days, mostly cache reads.
- **A gate the model fills in for itself.** A self-reported "did you check?" step was skipped 10,420 times.
- **A ritual skill.** A skill that told the model to imagine failures and write predictions changed no behaviour against a baseline without the skill, across 4 scenarios. It cost 46–74% more tokens.
- **A debugging skill the model has to call.** LR's skill for rival explanations was called once between June and October. The reflex now asks at the moment the tool output shows the surprise.

## Configuration

Set these as environment variables, for example under `"env"` in `~/.claude/settings.json`:

| Variable | Default | Meaning |
| --- | --- | --- |
| `COL_CLAIMS` | `on` | `on` blocks a false claim (at most twice a turn), `log` only records it, `off` skips the check. |
| `COL_PREDICT` | `on` | `off` turns off the prediction gate, the ledger and the reminders. |
| `COL_SECRETS` | `on` | `off` turns off the key scan. |
| `COL_INQUIRY` | `on` | `off` turns off the question after a fix that did not hold, and the note on a test made quiet. |
| `COL_LANG` | auto | `en` or `tr`. Auto follows the language you write in; before your first message, the machine's. |
| `COL_DATA` | `~/.claude/col` | Where the logs and the ledger are kept. |
| `COL_TRANSCRIPTS` | `~/.claude/projects` | Where a session's transcript is found when the hook is not given one. |
| `COL_REPOS` | none | More repositories to look for named commits in, as globs separated by `:` (`;` on Windows). |

`CLAUDE_CONFIG_DIR` is respected when set.

**A false alarm in the key scan:** each finding comes with a fingerprint (the first 16 hex digits of the key's SHA-256). Add that fingerprint as a line to `~/.claude/col/secret_allow.txt`, and that string passes from then on. Lines starting with `#` are comments.

## Privacy and removal

Everything stays on your machine, in `~/.claude/col`:
- `checks.jsonl`: one line per finished turn.
- `outcomes.jsonl`: how each block turned out.
- `predictions.jsonl`: the ledger.
- `gate.jsonl`: the refused launches. Command lines are logged with keys masked.
- `secrets.jsonl`: kind, file, line and fingerprint, never a key.
- `inquiry.jsonl`: each question asked, each test made quiet, and how the check ended. It keeps the check's tool and files and up to 200 characters of the failing test lines.
- `errors.log`.
- `state/`: a small file per session, deleted after 30 days.

To remove COL, run `/plugin uninstall col@living-runtime`, then delete `~/.claude/col`.

## Develop

From the repository root:

```bash
python -m pytest tests
```

The tests use temporary folders only. They never read your real `~/.claude`, start Claude or touch the network. The fake keys they plant are built at run time, so no key-shaped string sits in the source.

COL is cut out of LR (Living Runtime), the author's agent runtime, where it has run since October 2026.

## License

MIT
