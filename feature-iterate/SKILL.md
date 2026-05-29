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

## Step 0.5: Choose target branch

Check the current branch:

```bash
git branch --show-current
```

- **On `main` (or the default branch)**: ask the user:
  > Should I put these changes on a new branch, or commit them directly to main?
  - If branch: count completed review-feedback rounds (archived
    HTML in `~/.claude/feature-docs/<PROJECT>/<FEATURE>/.feedback-archive/`
    plus archived markdown in `docs/features/<FEATURE>/.feedback-archive/`).
    Call the total M. Create branch
    `features/<FEATURE>-iterate-<M+1>` and switch to it.
  - If direct: stay on main. Tell the user explicitly that the next
    commit will land on main.
- **On any other branch**: stay there (e.g. invoked manually mid-flow
  on a feature branch that's still in progress).

## Step 1: Gather feedback

The review synthesis doc is canonical HTML at
`~/.claude/feature-docs/<PROJECT>/<FEATURE>/review-feedback-<N>.html`
when feature-review has produced one. Legacy markdown synthesis docs
at `docs/features/<FEATURE>/review-feedback-<N>.md` are still
supported for transitional reviews.

Pick the highest-numbered synthesis doc (HTML preferred over markdown
if both exist for the same N).

### HTML synthesis doc (canonical)

The HTML synthesis doc is a form: the user fills in "Your thoughts"
fields and clicks **Copy responses** to emit a JSON blob in this
shape:

```json
{
  "doc": "docs/features/<FEATURE>/review-feedback-<N>",
  "responses": { "1": "user text or empty string", ... },
  "routine_flags": { "19": "comment", ... }
}
```

If the user pasted the blob already (it should be visible above in
the conversation), parse it. If not, ask them to click **Copy
responses** in the open HTML and paste the JSON.

- Empty string in `responses` = agree with your take on that item.
- Non-empty string = user direction; use it.
- Items in `routine_flags` are routine items the user wants to
  discuss — their comment explains why. Treat as needing your call.

The user may also have left click-to-comment annotations on
`requirements.html` or `plan.html` and pasted a `{"doc": ".../<file>",
"comments": [...]}` blob. Fold those in as additional feedback.

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
