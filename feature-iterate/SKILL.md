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

If `$ARGUMENTS` is provided, use it as the feature name (FEATURE). Otherwise,
infer from the branch name if you're on a feature branch (e.g.
`features/<name>-pN`), or ask the user.

## Step 0.5: Choose target branch

Check the current branch:

```bash
git branch --show-current
```

- **On `main` (or the default branch)**: ask the user:
  > Should I put these changes on a new branch, or commit them directly to main?
  - If branch: count existing `iterate-feedback-N.md` files in
    `docs/features/<FEATURE>/` (call this M). Create branch
    `features/<FEATURE>-iterate-<M+1>` and switch to it.
  - If direct: stay on main. Tell the user explicitly that the next commit
    will land on main.
- **On any other branch**: stay there (e.g. invoked manually mid-flow on a
  feature branch that's still in progress).

## Step 1: Gather feedback

Collect feedback from all sources:
- Reviewer subagent output (from the current conversation)
- Any review synthesis documents in `docs/features/<FEATURE>/` (the highest-
  numbered `review-feedback-N.md` is the authoritative one — the user's
  filled-in "Your thoughts" entries override your take)
- Human comments (from the current conversation)

## Step 2: Plan before acting

Before making any changes, produce a brief plan in the conversation listing each
feedback item and what you'll do:
- **Fix:** what you'll change and how
- **Skip:** why it doesn't need addressing (e.g. already handled, disagree, out of scope)

Ask the user to confirm the plan before proceeding. Once confirmed, make all the changes.

After making changes, capture decisions from the feedback file before removing it.
Add a "Review decisions" section to the feature's `requirements.md` (or append to
existing). For each item:
- User-annotated items: `**User:**` prefix, capture their decision.
- Fixes: one line — what was wrong, what was done.
- Declined items: one line — what was suggested, why it was skipped.
- Skip trivial fixes (typos, formatting).

Number each round sequentially.

Archive the feedback file instead of deleting it (preserves a record for
later analysis):

```bash
mkdir -p docs/features/<FEATURE>/.feedback-archive
mv docs/features/<FEATURE>/review-feedback-<N>.md \
   docs/features/<FEATURE>/.feedback-archive/
```

Ensure the archive directory is gitignored locally (not committed). Append
the pattern to the repo's local exclude file if it's not already there:

```bash
GIT_DIR=$(git rev-parse --git-dir 2>/dev/null)
[ -n "$GIT_DIR" ] && \
  ! grep -qxF '**/.feedback-archive/' "$GIT_DIR/info/exclude" 2>/dev/null && \
  echo '**/.feedback-archive/' >> "$GIT_DIR/info/exclude"
```

## Step 3: Quality control

Invoke `/feature-qa` and work through all checks it defines.

## Step 3.5: Commit, push, and (if on a branch) create an MR

Commit all changed files — implementation changes and the updated
`docs/features/<FEATURE>/requirements.md` — with the message
`feat(<FEATURE>): address review feedback` and push.

If you're on a `features/<FEATURE>-iterate-N` branch, create an MR after
pushing. If you're on main (per the Step 0.5 choice), no MR is needed —
the commit has already landed.

## Step 4: Re-review

After making changes, spawn a reviewer subagent using the Agent tool with
`run_in_background: true`. Tell the user the re-reviewer is running.

Prompt for the re-reviewer:

> You are reviewing an implementation after a round of iteration.
> Read the full diff with `git diff main`.
> Read the requirements at `docs/features/<FEATURE>/requirements.md`.
> Read the plan at `docs/features/<FEATURE>/plan.md`.
> Read `CLAUDE.md`.
>
> Check whether the previous review feedback has been addressed, and flag
> any new issues introduced by the changes. Also check whether the changes
> still align with the requirements — not just the plan.
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

If any "Need your call" answers reveal substantive decisions, capture them
in the "Review decisions" section of
`docs/features/<FEATURE>/requirements.md` (same format as Step 2).

Summarise what changed, what was declined and why, and whether all quality
checks pass.

Before removing the synthesis document, capture decisions into the "Review decisions"
section of the feature's `requirements.md` (same format as Step 2). Remove the
synthesis document once decisions are captured.
