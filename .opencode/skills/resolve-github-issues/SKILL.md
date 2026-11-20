---
name: resolve-github-issues
description: Resolve GitHub issues end to end — list open issues with `gh issue list`, help the person pick one, then branch, fix, test, commit, push and open a PR that closes it. Use this whenever someone asks to fix, resolve, close, triage or "take a look at" a GitHub issue, names an issue number ("fix #42", "what's in issue 17"), asks what is open in a repo or what to work on next, mentions `gh issue list` or the issue backlog, or points at a GitHub issue URL. Also use it when a repo has an open-issue backlog and the person wants the next task, even if they never say the word "issue".
---

# Resolve GitHub Issues

Take an open GitHub issue and carry it to a merged-ready pull request: find it, understand
it, fix the real cause, prove the fix, and open a PR that closes the issue on merge.

The point of the workflow is that the issue is the **spec**, not a suggestion. A PR that
solves something adjacent to what the issue asked is worse than no PR, because it moves the
issue to "looks handled" while the original problem stays. Read the issue closely, reproduce
what it describes, and check the fix against the reporter's own words before declaring done.

## 0. Preflight

Run these before touching anything; each one fails loudly and cheaply if something is wrong.

```sh
gh auth status                                   # must show a logged-in account
gh repo view --json nameWithOwner,defaultBranchRef --jq '"\(.nameWithOwner) default=\(.defaultBranchRef.name)"'
git status --porcelain                           # must be clean before branching
git branch --show-current
```

- **Dirty working tree** — stop and ask. Committing someone else's half-finished work into a
  fix branch makes the PR unreviewable and the history a lie.
- **No `gh` or not authenticated** — say so and offer the manual path (the person opens the
  issue URL themselves) instead of guessing.
- **Detached HEAD or the default branch is not what you expect** — resolve before branching.

Also read the repo's own instructions now, not later: `AGENTS.md`, `CLAUDE.md`, and the
`Makefile` / `package.json` / `gradlew` / `go.mod` at the root. They dictate the branch
naming, the test command and the commit style, and a PR that ignores them gets bounced.

## 1. List the issues and let the person choose

Default to the repo of the current directory; accept `-R owner/repo` when they name another.
An issue number or URL given up front skips the listing — take it directly.

```sh
scripts/list-issues.sh                       # 50 most recently updated open issues
scripts/list-issues.sh --label bug           # narrowing filters pass through to gh
scripts/list-issues.sh --assignee @me -L 100
scripts/list-issues.sh -R owner/repo
```

The raw command behind it, if you need JSON:

```sh
gh issue list --state open --limit 50 \
  --json number,title,labels,updatedAt,assignees,comments \
  --jq '.[] | "#\(.number) [\([.labels[].name]|join(","))] \(.title) (\(.comments|length) comments)"'
```

Show the list, then ask which issue to take — one question, not an interrogation. If the
person already named one, skip the prompt. Prefer issues that are open, unassigned, and
labelled as bugs/enhancements over ones already being worked on; a comment thread that stalls
mid-way is a signal someone else has a branch open.

When they say "you pick", choose the smallest self-contained issue that does not need
product input — a good first PR beats an ambitious one that stalls.

## 2. Read the whole issue

```sh
gh issue view <n> --json number,title,body,state,labels,assignees,author,comments,createdAt
```

Read the **comments**, not just the body. The reproduction steps, the maintainer's decision,
the "we tried this and it broke X" warning, and the "won't fix, actually intended" verdict all
live there. Missing them is how a PR ends up re-litigating a settled question.

Then classify it before writing code:

| Kind | Move |
|---|---|
| Bug with a reproduction | Fix the cause, add a regression test. |
| Bug without a reproduction | Reproduce it yourself first; if you cannot, ask for the missing detail. |
| Perceptual bug (audio artifact, flicker, "feels slow") | Measure what is measurable, compare against a control, and let the reporter judge — see step 3. |
| Feature request | Confirm the shape with the person before implementing — scope is a product decision. |
| Question / docs / config | Answer or patch docs; usually no code PR. |
| Duplicate / already fixed / by design | Say so with evidence and stop; closing is the right resolution. |
| Too vague to act on | Ask for specifics in one message; do not invent a requirement. |

Never manufacture a code change to make an issue look resolved. "This one is a duplicate of
#12" is a complete outcome.

## 3. Reproduce, then find the cause

Locate the code the issue points at (search for the error text, the endpoint path, the field
name, the string in the screenshot). Reproduce the failure — run the failing test, the
command, or the request — **before** editing. A fix you cannot see fail first is a guess, and
guesses are what turn a one-line bug into a three-file diff.

Write down, in one or two sentences: what breaks, why, and where. If that sentence is hard to
write, keep reading — you do not yet understand the issue.

**When the failure is perceptual** (a hiss in a clip, a stutter, a visual jank) you cannot
reproduce it by running anything — you have no ears or eyes on the artifact. Do not skip
straight to "could not reproduce", and do not assume regeneration will cure it. Work in this
order:

1. **Measure, against controls.** Peak/RMS/clipping, energy spikes and dropouts, noise floor,
   frame timings — and compare the reported case with cases nobody complained about. "Inside
   the control range" is a real finding: it rules out corruption, clipping and gross coding
   damage. It does **not** mean nothing is wrong, and it does not mean "it was a bad take".
2. **Separate a random take from a deterministic performance.** Re-render once and compare
   length and onset, not bytes. Many cloud generators differ in ~half their samples while
   keeping duration and timing identical — same performance, different dither. If that is what
   you see, regeneration **cannot** remove the defect and saying "rebuilt, try again" wastes
   the reporter's evening. Count it out loud and stop proposing it.
3. **Build a one-variable ladder and let the reporter judge.** Change exactly one thing per
   variant so the answer localises the cause: encode/bitrate, speed, voice, and the wording
   itself. Name the files A/B/C/D, say what each one isolates, and ask which sound clean. One
   round trip with four labelled clips beats five rounds of guessing, and it turns a vague
   "still noisy" into a specific lever. Keep the failing case in the set as the reference.
4. **Fix the source, not the artifact.** Once a clean variant is identified, change the thing
   that produced the bad one — the phrase, the rate, the voice setting — and re-render. A
   hand-edited or post-processed file is not reproducible from the repo.

Say plainly that the verdict is the reporter's, and give exact play/compare commands. Never
claim a perceptual fix is verified on your own authority — you could not hear the defect to
begin with.

When the clean variant is a change to **authored content** (a sentence, a label), prefer the
smallest edit that keeps the meaning and the thing being taught intact: reordering or moving a
particle beats rewriting the sentence, and beats changing a project-wide setting like the voice
or the rate for every card.

## 4. Checkpoint the plan

For anything beyond a trivial fix (more than roughly one file, or a design choice, or a
behavior change), state the plan briefly before implementing:

> Issue #42: `parse_date` crashes on an empty string because it indexes `[0]` without a
> length check. Plan: guard the empty case in `src/date.py`, add a regression test for `""`
> and for whitespace, run `pytest`.

This is cheap and catches the case where the person meant something else by the issue. For a
typo or an obvious one-liner, just fix it and say what you did.

## 5. Branch

Keep the issue and the branch linked so GitHub shows the work in the issue timeline:

```sh
gh issue develop <n> --checkout                    # creates the linked branch from the default branch
```

If that is unavailable (older `gh`, fork, protected base), fall back to:

```sh
git switch -c fix/<n>-<short-slug> origin/<default-branch>
```

Use the repo's own prefix convention if it has one (`fix/`, `feat/`, `bugfix/`, ticket ids);
`AGENTS.md` and recent branch names (`git branch -r --sort=-committerdate | head`) tell you.
Never commit the fix straight onto the default branch.

## 6. Implement the smallest correct change

- Fix the **cause** named in step 3, not the symptom the reporter saw.
- Stay inside the issue's blast radius. Drive-by refactors, formatting runs and dependency
  bumps make the diff unreviewable and hide the actual change — open a separate issue instead.
- Follow local conventions from `AGENTS.md` / the `Makefile`: naming, layering, error style,
  how tests are written. Match the surrounding code rather than importing your own taste.
- If a schema or migration change is involved, follow the repo's migration rules (numbered
  SQL, generated migrations) — a fix that only works on a fresh database is not a fix.
- No secrets, tokens, or machine-specific paths in the diff.

## 7. Prove it

Run the repo's own checks — the narrow one first, then the full suite if it is fast:

```sh
# pick what the repo actually uses
make test
./gradlew test --tests "fully.qualified.Class"
./mvnw test -Dtest=Class#method
go test ./pkg -run TestName
npm test        # or: pnpm test / cargo test / pytest
```

Add a regression test that **fails without the fix**. Then verify it fails on the old code
(`git stash` the fix, run it, unstash) — a test that passes either way proves nothing. Note:
some repos have no test harness (this one says so in `AGENTS.md`); in that case run the
manual reproduction from step 3 and record the command and its output in the PR body.

Report honestly: if the full suite has unrelated pre-existing failures, say which ones and
show that they also fail on the base branch.

## 7b. When the fix produces no committable diff

Not every issue resolves into a diff. Build artifacts, generated media, `.gitignore`d outputs,
linter/formatter runs, dashboard and CI settings, database rows — the fix can be real, verified
and still leave `git status` clean. Check for this **before** step 8: if the only thing you
changed is untracked or ignored, `git diff` will be empty and steps 8–9 have nothing to do.

```
git status --short        # is anything staged-able?
git diff --stat           # empty? the fix lives outside version control
```

Recognise the shapes:

| Shape | Resolution |
|---|---|
| Regenerated artifact (media, lockfile, build output) | Do the regeneration, verify it, and report it as a local action. No branch, no PR. |
| The *tool* cannot do what the issue asks | Fix the tool — that **is** the committable change, and it is usually the real root cause of the issue being hard to resolve. |
| Config/state outside the repo (CI, hosting, dashboard) | Report the exact change and where it lives; a PR cannot carry it. |
| Docs already correct | Say so with evidence; the resolution is "no code change needed". |

Then prune the tail: skip the branch, commit and PR, and in the report state what you did,
what you verified, and what remains for a human to confirm (a listen, a look, a re-import).
Never open an empty PR, and never invent an unrelated change to justify one.

If the artifact is ignored *and* the consumer caches it by name, say that too — a rebuilt file
that the importer skips is a fix that will not reach the person who reported the bug.

## 8. Commit

One logical change per commit, message in the repo's existing style (check `git log --oneline -15`).
Reference the issue so GitHub links the commit:

```sh
git add <specific files>          # never `git add -A` blindly; review with `git status`
git commit -m "fix(date): guard empty input in parse_date

Closes #42"
```

Conventional Commits (`fix(scope): …`) is a safe default when the repo has no visible style.

## 9. Open the pull request

```sh
git push -u origin HEAD

gh pr create --base <default-branch> --title "fix(date): guard empty input in parse_date" \
  --body "$(cat <<'EOF'
## Summary
Fixes #42 — `parse_date("")` crashed with `IndexError` because the empty string was indexed
before the length check. Now returns `None`, matching the function's documented behaviour for
unparseable input.

## Changes
- `src/date.py`: guard the empty/whitespace case in `parse_date`
- `tests/test_date.py`: regression tests for `""` and `"   "`

## Testing
- `pytest tests/test_date.py` — passes
- Confirmed both new tests fail on the base commit without the fix
EOF
)"
```

`Fixes #42` / `Closes #42` in the body is what actually closes the issue on merge — do not
close the issue by hand afterwards, and do not claim it is fixed before the PR exists.

Use `Refs #42` instead when the PR is **necessary but not sufficient** — it fixes the tool that
rebuilds the broken artifact, or one of several causes, or needs the reporter to confirm the
result. Auto-closing in that case hides an unresolved issue behind a merged PR.

Never `git push --force` to a shared branch, and never open the PR against the wrong base
(e.g. `main` when the repo releases from `develop`).

## 10. Report

Close the loop with: the issue number and title, the one-sentence root cause, the files
changed, the exact test command and result, and the PR URL. If anything was left out of scope,
say what and why.

## Guardrails

- **No PR without a verified fix.** If tests fail or the reproduction still fails, say so and
  show the failure — an honest "blocked on X" is better than a green-looking PR.
- **One issue per branch and PR.** Unrelated changes go to their own issue.
- **Do not close, label, assign or edit the issue** unless asked; the merged PR does the
  closing, and label changes are the maintainer's call.
- **Ask before touching `main`, rewriting history, or pushing over someone else's branch.**
- **If the issue contradicts the code's documented behaviour** — the docs say `None`, the
  issue says it should raise — surface the conflict instead of silently choosing a side.
