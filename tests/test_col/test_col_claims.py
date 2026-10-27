"""The claim check on the final message: what holds passes, what was invented is named, and what cannot be checked
is left alone."""
from col import claims
from .colkit import turn

BASH = [{"name": "Bash", "input": {"command": "pytest -q"}}]
READ = [{"name": "Read", "input": {"file_path": "x"}}]


def test_real_evidence_passes_and_invented_evidence_is_named(repo, tmp_path):
    r, h, _ = repo
    real = tmp_path / "report.md"
    real.write_text("x")
    commit = [{"name": "Bash", "input": {"command": "git commit -m x"}}]
    honest = f"Done. Commit {h} is in, `{real.as_posix()}` is written, and 3 tests passed."
    assert claims.check(honest, turn(commit), "3 passed in 0.1s", str(r)) == []
    lies = f"Done. Commit 9a8b7c6 is in, `{(tmp_path / 'gone.md').as_posix()}` is written, and 7 tests passed."
    found = {(p["kind"], p["what"]) for p in claims.check(lies, turn(commit), "3 passed in 0.1s", str(r))}
    assert ("commit", "9a8b7c6") in found and ("tests", "7 tests passed") in found
    assert any(kind == "path" and what.endswith("gone.md") for kind, what in found)


def test_turkish_claims_are_read_too(repo):
    r, h, _ = repo
    found = claims.check("Tamam. commit 9a8b7c6 yapıldı ve 7 test geçti.", turn(BASH), "3 passed", str(r))
    assert {p["kind"] for p in found} == {"commit", "tests"}
    assert claims.check(f"Tamam. commit {h} yapıldı ve 3 test geçti.", turn(BASH), "3 passed", str(r)) == []


def test_the_test_count_is_read_the_way_each_runner_prints_it(tmp_path):
    outputs = {"node": "ℹ tests 6\nℹ suites 0\nℹ pass 6\nℹ fail 0", "tap": "# tests 6\n# pass 6",
               "mocha": "  6 passing (12ms)", "jest": "Tests:       6 passed, 6 total",
               "unittest": "......\n------\nRan 6 tests in 0.004s\n\nOK",
               "dotnet": "Passed!  - Failed: 0, Passed:     6",
               "cargo": "test result: ok. 6 passed; 0 failed"}
    for runner, out in outputs.items():
        for claim in ("6 tests passed.", "All 6 tests pass.", "6/6 tests passed.", "6 test geçti."):
            assert claims.check(claim, turn(BASH), out, str(tmp_path)) == [], (runner, claim)
        assert claims.check("16 tests passed.", turn(BASH), out, str(tmp_path)), runner
    assert claims.check("6 tests passed.", turn(BASH), "ℹ pass 16\nℹ fail 0", str(tmp_path))
    assert claims.check("6 tests passed.", turn(BASH), "Ran 6 tests in 0.1s\n\nFAILED (failures=1)", str(tmp_path))
    # "3 of 5 tests passed" claims three, not five
    assert claims.check("3 of 5 tests passed.", turn(BASH), "3 passed, 2 failed", str(tmp_path)) == []
    assert claims.check("5 testin 3'ü geçti.", turn(BASH), "3 passed, 2 failed", str(tmp_path)) == []


def test_a_count_that_is_withdrawn_denied_or_asked_is_no_claim(tmp_path):
    """The first two are what a real session answered to a block; both were blocked again before this rule."""
    for answer in ("I'm taking that claim back. I ran no tools and no tests in this session, so I have no evidence "
                   "that a parser bug was fixed or that 12 tests passed.",
                   "I'm withdrawing the claim that 12 tests passed.", "Did all 12 tests pass? I cannot say.",
                   "Whether 12 tests passed is unknown.", "12 tests passed is not true.",
                   "12 test geçti iddiasını geri alıyorum."):
        assert claims.check(answer, turn(BASH), "", str(tmp_path)) == [], answer
    assert claims.check("Done. I fixed the bug in the parser and all 12 tests passed.", turn(BASH), "", str(tmp_path))


def test_the_test_output_is_read_only_when_a_count_needs_it(tmp_path):
    reads = []

    def results():
        reads.append(1)
        return "4 passed"

    assert claims.check("Updated the README.", turn(BASH), results, str(tmp_path)) == [] and not reads
    assert claims.check("4 tests passed.", turn(BASH), results, str(tmp_path)) == [] and reads


def test_done_and_committed_need_an_action_behind_them(tmp_path):
    assert [p["kind"] for p in claims.check("Done. I fixed the bug.", turn(), "", str(tmp_path))] == ["no-tools"]
    assert claims.check("Tamam, hatayı düzelttim.", turn(), "", str(tmp_path))
    assert claims.check("Done: it was already fixed in the previous turn.", turn(), "", str(tmp_path)) == []
    assert claims.check("You are right; I will look tomorrow.", turn(), "", str(tmp_path)) == []
    assert [p["kind"] for p in claims.check("Everything is committed.", turn(READ), "", str(tmp_path))] == [
        "commit-claim"]
    assert claims.check("Hepsi commit'lendi.", turn(READ), "", str(tmp_path))
    for honest in ("Nothing is committed yet.", "The changes are not committed.", "Once committed, CI runs.",
                   "It will be committed after review.", "Değişiklikler commit'lenmedi.",
                   "It was already committed earlier."):
        assert claims.check(honest, turn(READ), "", str(tmp_path)) == [], honest
    commit = [{"name": "Bash", "input": {"command": "git add -A && git commit -m fix"}}]
    assert claims.check("Everything is committed.", turn(commit), "", str(tmp_path)) == []


def test_a_commit_listed_after_the_word_counts(repo):
    r, h, git = repo
    git("commit", "-q", "--allow-empty", "-m", "second")
    h2 = git("rev-parse", "--short=7", "HEAD")
    assert claims.check(f"Both are committed ({h}, {h2}).", turn(READ), "", str(r)) == []
    assert claims.check("Committed (total 1234567 bytes).", turn(READ), "", str(r))  # a number is not a commit


def test_paths_are_looked_up_where_links_point(tmp_path):
    proj = tmp_path / "proj"
    (proj / "src").mkdir(parents=True)
    (proj / "src" / "app.py").write_text("x")
    memory = tmp_path / "memory"
    memory.mkdir()
    (memory / "MEMORY.md").write_text("x")
    cited = f"See [app.py](src/app.py:12), [the index](MEMORY.md) and `{(proj / 'src' / 'app.py').as_posix()}`."
    assert claims.check(cited, turn(BASH), "", str(proj), str(memory)) == []
    assert [p["what"] for p in claims.check("See [x](src/missing.py).", turn(BASH), "", str(proj))] == [
        "src/missing.py"]
    assert claims.check(f"The old file `{(proj / 'old.md').as_posix()}` was deleted.", turn(BASH), "", str(proj)) == []
    assert claims.check(f"Removed `{(proj / 'old.md').as_posix()}`.", turn(BASH), "", str(proj)) == []
    wrote = [{"name": "Write", "input": {"file_path": "D:/elsewhere/notes/plan.md"}}]
    assert claims.check("Wrote [plan](notes/plan.md).", turn(wrote), "", str(proj)) == []
    for not_a_path in ("Open [docs](https://example.com/a.md).", "See [above](#setup).", "Call `/api/v1/health`.",
                       "Run `/plugin install col@living-runtime`.", "Open [the session](#local_abc)."):
        assert claims.check(not_a_path, turn(BASH), "", str(proj)) == [], not_a_path


def test_no_repository_in_reach_means_no_commit_lookup(tmp_path):
    lonely = tmp_path / "nothing-here"
    lonely.mkdir()
    assert claims.check("Shipped as commit 9a8b7c6.", turn(BASH), "", str(lonely)) == []


def test_a_repository_the_turn_worked_in_is_searched(repo, tmp_path):
    r, h, _ = repo
    outside = tmp_path / "outside"
    outside.mkdir()
    worked = [{"name": "Bash", "input": {"command": f"git -C {r.as_posix()} log -1"}}]
    assert claims.check(f"It is commit {h}.", turn(worked), "", str(outside)) == []
    assert claims.check("It is commit 9a8b7c6.", turn(worked), "", str(outside))
    # a repository right under the working folder is in reach too
    assert claims.check("It is commit 9a8b7c6.", turn(BASH), "", str(r.parent))
    assert claims.check(f"It is commit {h}.", turn(BASH), "", str(r.parent)) == []
