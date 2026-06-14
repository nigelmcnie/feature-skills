---
name: feature-iterate
description: Address review feedback on the current branch. Use after receiving review feedback from /feature-review or human comments.
disable-model-invocation: true
allowed-tools: Read, Write, Edit, Grep, Glob, Bash, Agent
argument-hint: "[feature-name]"
---

# Iteration Workflow

You are addressing review feedback. You may be starting from main (typical
when invoked after `/feature-review`) or from a feature branch.

## Model check

Check your system context for the model you are running on. If your model name does not contain "opus", warn the user:

> ⚠️ This skill expects Claude Opus. You appear to be on [model name]. Opus is recommended here for stronger reasoning during iteration. Continue anyway?

Wait for their response. If they say no, stop here.

## Step 0: Establish the feature name

If `$ARGUMENTS` is provided, use it as the feature name (FEATURE).
Otherwise, infer from the branch name if you're on a feature branch
(e.g. `features/<name>-pN`), or ask the user.

Resolve `PROJECT`: `PROJECT=$(basename $(git rev-parse --show-toplevel))`.

## Step 0.5: Choose where the work lands

Iteration writes code, so by default isolate it in a worktree — parallel
agents in the same repo then never collide in the shared tree.

Check the current branch (`git branch --show-current`):

- **On `main` (or the default branch)** — typical after `/feature-review`,
  including when review runs this skill inline: isolate in a worktree.
  1. Count completed review-feedback rounds (archived HTML in
     `~/.claude/feature-docs/<PROJECT>/<FEATURE>/.feedback-archive/` plus
     archived markdown in `docs/features/<FEATURE>/.feedback-archive/`);
     call the total M.
  2. Tell the user in one line that you're isolating this round in a
     worktree, then create it **the way this repo wants**: check the
     repo's `CLAUDE.md` (and `.claude/`) for worktree instructions first —
     some repos need extra setup (database, ports, venv) and provide a
     tool for it, which you should use, then `EnterWorktree` with
     `path=<that worktree>`. Otherwise use the standard flow:
     `EnterWorktree` with name `<FEATURE>-iterate-<M+1>` (branches fresh
     from `origin/<default>`).
  3. End up on a branch named `features/<FEATURE>-iterate-<M+1>`, renaming
     if needed:
     ```bash
     git branch -m features/<FEATURE>-iterate-<M+1>
     ```
  4. Fresh checkout — unless the repo's tool provisioned them, install
     deps if QC/build needs them.

  (Quick one-off fix you'd rather land straight on main, un-isolated?
  Only if the user explicitly asks — then stay on main and tell them the
  commit lands directly on main.)
- **On any other branch**: stay there (e.g. invoked manually mid-flow on a
  feature branch that's still in progress) — you're already off the shared
  main, no new worktree needed.

## Step 1: Gather feedback

**Inline handoff (the common path).** When `/feature-review` flows
straight into this skill, it has already triaged the feedback inline
(its Step 8) and there is **no synthesis doc** — the "Applying" items
and any resolved "Need your call" answers are in the conversation. That
triage *is* the feedback; use it directly and skip the doc-reading
below. Jump to Step 2.

Otherwise — when invoked standalone (the developer ran
`/feature-iterate` fresh in a later session) — the review synthesis doc
is canonical HTML at
`~/.claude/feature-docs/<PROJECT>/<FEATURE>/review-feedback-<N>.html`
when an older review produced one. Legacy markdown synthesis docs at
`docs/features/<FEATURE>/review-feedback-<N>.md` are still supported for
transitional reviews.

Pick the highest-numbered synthesis doc (HTML preferred over markdown
if both exist for the same N).

### HTML synthesis doc (canonical)

The synthesis response was submitted via the webapp. Read it from the HTTP
endpoint — the absolute path of the highest-numbered
`review-feedback-<N>.html` in the dev-store is the key:

```bash
curl -fsS "http://127.0.0.1:8800/synthesis-response?path=$HOME/.claude/feature-docs/<PROJECT>/<FEATURE>/review-feedback-<N>.html"
```

- `200 submitted=true` → parse `responses` and `routine_flags` from the
  JSON body.
- `200 submitted=false` → the human hasn't submitted yet. Poll every 5 s;
  emit a "still waiting in the inbox…" line roughly every 60 s.
- `404` → the doc isn't indexed yet — trigger a walk first:
  ```bash
  curl -fsS -X POST http://127.0.0.1:8800/admin/discover >/dev/null 2>&1 || true
  ```
  then retry the poll.

**Fallback**: if the server is unreachable or the user gives up, ask them
to click **Copy responses** in the synthesis doc and paste the JSON blob.
See `docs/webapp-polling.md` in the feature-skills repo for the full
convention. The clipboard shape is:

```json
{
  "doc": "docs/features/<FEATURE>/review-feedback-<N>",
  "responses": { "1": "user text or empty string", ... },
  "routine_flags": { "19": "comment", ... }
}
```

Interpretation (same whether from HTTP or clipboard):

- Empty string in `responses` = agree with your take on that item.
- Non-empty string = user direction; use it.
- Items in `routine_flags` are routine items the user wants to
  discuss — their comment explains why. Treat as needing your call.

The user may also have left click-to-comment annotations on
`requirements.html` or `plan.html`. Fetch those from the webapp — using
the spine doc paths, not the feedback doc path:

```bash
curl -fsS "http://127.0.0.1:8800/comments?path=$HOME/.claude/feature-docs/<PROJECT>/<FEATURE>/requirements.html"
curl -fsS "http://127.0.0.1:8800/comments?path=$HOME/.claude/feature-docs/<PROJECT>/<FEATURE>/plan.html"
```

For each doc with a non-empty `comments` array, fold the comments in as
additional feedback. Then integrate the consumed ids:

```bash
curl -fsS -X POST http://127.0.0.1:8800/comments/integrate \
  -H 'Content-Type: application/json' \
  -d '{"path": "'"$HOME"'/.claude/feature-docs/<PROJECT>/<FEATURE>/requirements.html", "ids": [<ids>]}'
# repeat for plan.html if it also had comments
```

**Fallback**: if the server is unreachable, ask the user to click **Copy
comments** on the relevant doc and paste the blob.

**Sanity-check (clipboard fallback only)**: verify the `doc` field of any
pasted blob matches `docs/features/<FEATURE>/review-feedback-<N>` for
the highest N in the dev-store. If not, warn and confirm before
proceeding.

### Markdown synthesis doc (legacy)

Read the highest-numbered `review-feedback-N.md`. The user's
filled-in "Your thoughts" entries override your take.

### Other sources

- Reviewer subagent output (from the current conversation).
- Human comments (from the current conversation).

## Step 2: Plan before acting

Before making any changes, produce a brief plan in the conversation
listing each feedback item and what you'll do:

- **Fix:** what you'll change and how.
- **Skip:** why it doesn't need addressing (e.g. already handled,
  disagree, out of scope).

Ask the user to confirm the plan before proceeding. Once confirmed,
make all the changes.

### Capture decisions

After making changes, capture decisions into the requirements doc
before archiving the synthesis doc.

The canonical requirements doc is
`~/.claude/feature-docs/<PROJECT>/<FEATURE>/requirements.html` if it
exists; otherwise the legacy `docs/features/<FEATURE>/requirements.md`.
Append (or extend) a **Review decisions** section. In the HTML
version, this is `<section id="review-decisions">`; in markdown, a
`## Review decisions` heading.

For each item:

- User-annotated items: `**User:**` prefix, capture their decision.
- Fixes: one line — what was wrong, what was done.
- Declined items: one line — what was suggested, why it was skipped.
- Skip trivial fixes (typos, formatting).

Number each round sequentially.

If the requirements doc was updated in HTML form, re-run the export
when `.feature-workflow.toml`'s `[export].requirements` opts in:

```bash
feature-html-to-md \
    ~/.claude/feature-docs/<PROJECT>/<FEATURE>/requirements.html \
    docs/features/<FEATURE>/requirements.md
```

(or `cp` for `html`). Skip if `none` or absent.

### Archive the synthesis doc

**Skip this entirely on the inline-handoff path** — review produced no
synthesis doc, so there is nothing to archive; the durable record is
the **Review decisions** section you just wrote plus the commit. Only
when a synthesis doc actually exists (a standalone invocation off an
older review) do the following.

Archive the feedback file rather than deleting it (preserves a record
for later analysis).

**HTML synthesis doc**:

```bash
mkdir -p ~/.claude/feature-docs/$PROJECT/<FEATURE>/.feedback-archive
mv ~/.claude/feature-docs/$PROJECT/<FEATURE>/review-feedback-<N>.html \
   ~/.claude/feature-docs/$PROJECT/<FEATURE>/.feedback-archive/
```

The dev-store is local-only — no gitignore needed.

**Markdown synthesis doc** (legacy):

```bash
mkdir -p docs/features/<FEATURE>/.feedback-archive
mv docs/features/<FEATURE>/review-feedback-<N>.md \
   docs/features/<FEATURE>/.feedback-archive/
```

Ensure the archive directory is gitignored locally (not committed).
Append the pattern to the repo's local exclude file if it's not
already there:

```bash
GIT_DIR=$(git rev-parse --git-dir 2>/dev/null)
[ -n "$GIT_DIR" ] && \
  ! grep -qxF '**/.feedback-archive/' "$GIT_DIR/info/exclude" 2>/dev/null && \
  echo '**/.feedback-archive/' >> "$GIT_DIR/info/exclude"
```

## Step 3: Quality control

Invoke `/feature-qa` and work through all checks it defines.

**Do NOT use the Skill tool to invoke `/feature-qa`** — it sets
`disable-model-invocation: true`, which blocks the Skill tool. Read
`~/.claude/skills/feature-qa/SKILL.md` and execute its instructions
inline in this conversation.

## Step 3.5: Commit, push, and (if on a branch) create an MR

Commit all changed files — implementation changes plus whichever
requirements file ended up in the repo via the export step (if any) —
with the message `feat(<FEATURE>): address review feedback` and push.

If `.feature-workflow.toml`'s `[export].requirements` is `none` or
absent, the requirements changes are local-only in the dev-store and
nothing requirements-related gets committed. The implementation
changes still commit.

If you're on a `features/<FEATURE>-iterate-N` branch, create an MR
after pushing. If you're on main (per the Step 0.5 choice), no MR is
needed — the commit has already landed.

## Step 4: Re-review

After making changes, spawn a reviewer subagent using the Agent tool with
`run_in_background: true`. Tell the user the re-reviewer is running.

Prompt for the re-reviewer (substitute dev-store paths if the HTML
docs exist, otherwise legacy markdown paths):

> You are reviewing an implementation after a round of iteration.
> Read the full diff with `git diff main`.
> Read the requirements at
> `~/.claude/feature-docs/<PROJECT>/<FEATURE>/requirements.html`
> (fall back to `docs/features/<FEATURE>/requirements.md` if the HTML
> doesn't exist).
> Read the plan at
> `~/.claude/feature-docs/<PROJECT>/<FEATURE>/plan.html`
> (fall back to `docs/features/<FEATURE>/plan.md` if the HTML doesn't
> exist).
> Read `CLAUDE.md`.
>
> Check whether the previous review feedback has been addressed, and
> flag any new issues introduced by the changes. Also check whether
> the changes still align with the requirements — not just the plan.
> When you find an issue, check whether the same *class* of issue recurs
> elsewhere in the touched code — sibling call sites, parallel fields,
> adjacent loops — and flag every instance, not just the first one you hit.
>
> Be specific with file paths and line numbers.

## Step 5: Process re-reviewer feedback inline

When the re-reviewer returns, triage each item into one of:

- **Apply** — new issue to fix that you agree with and that's uncontroversial.
  These get applied directly without asking.
- **Ask** — the item involves a real decision. Surface inline with your take.
- **Skip** — already addressed, or you disagree. Briefly say why.

Present the triage in chat — do not write a synthesis document. Format:

> Re-review feedback:
>
> **Will apply:**
> - <one-line description>
> - ...
>
> **Will skip:**
> - <one-line description + brief reason>
> - ...
>
> **Need your call:**
> 1. <Question>. My take: <brief>.
>
> Reply with answers (or "go" to take my take on all of them) and I'll apply.

Wait for response. Apply the "Will apply" items plus the resolved questions.

If any "Need your call" answers reveal substantive decisions,
capture them in the **Review decisions** section of
`~/.claude/feature-docs/<PROJECT>/<FEATURE>/requirements.html`
(legacy: `docs/features/<FEATURE>/requirements.md`). Same format as
Step 2. Re-export if `.feature-workflow.toml` opts in for
requirements.

Summarise what changed, what was declined and why, and whether all
quality checks pass.

## Step 6: Wrap up — ship

A single corrective pass is the norm: re-review (Step 4) → apply its
findings inline (Step 5) → ship. The dev-store history shows no feature
has ever needed a second iteration round, so **default to shipping**
once the re-review is addressed; treat a second round as the rare
exception, not a gate to wait at.

Only if the re-reviewer surfaced something genuinely substantial, or the
user explicitly asks to keep going ("more changes", "another round"),
tell them they can re-invoke `/feature-iterate <FEATURE>` once this
iteration's MR has landed (or stay in chat for more edits on the current
branch).

Otherwise — re-review addressed, or the user signals satisfaction
("looks good", "all done", "ship it", "nothing else", or similar):

- **If the current branch is `main`** (the Step 0.5 direct-commit
  path): re-run the mark-shipped procedure now. **Do NOT use the
  Skill tool to invoke `/feature-review`** — it sets
  `disable-model-invocation: true`, which blocks the Skill tool. Read
  `~/.claude/skills/feature-review/SKILL.md` Step 10 ("Mark shipped")
  and execute it inline. Skip the earlier steps of feature-review —
  the re-review already happened in Step 4 above; you don't need to
  rerun verification.
- **If the current branch is `features/<FEATURE>-iterate-N`** (open
  iteration MR): the MR has to merge before shipping. Tell the user:

  > Once this iteration's MR has merged, run `/feature-review <FEATURE>`
  > on main — it'll re-verify against the merged state and run the
  > mark-shipped procedure if everything's clean.

  Don't try to mark shipped from a branch.

If this round ran in a worktree (the Step 0.5 default), tear it down once
its work is safe — after the MR merges, or immediately if you committed
straight to main. Remove it the way this repo wants: if its `CLAUDE.md`
documents a worktree tool, use that (it may also tear down the
database/ports it set up); otherwise `git worktree remove
.claude/worktrees/<dir>` (or `ExitWorktree` with `action: remove` if
you're still inside it).

(or `ExitWorktree` with `action: remove` if you're still inside it).

## Step 7: Invite a process retro

Before wrapping up this session, add a soft one-line invite:

> Before you wrap up, consider `/feature-retro <FEATURE>` — it looks
> back over how the *process* went (not the code) and surfaces ways to
> streamline the feature-skills workflow itself.

This is a suggestion, not a step you run yourself. Skip it if the
iteration was trivial (a one-line tweak with no friction worth
reflecting on).
