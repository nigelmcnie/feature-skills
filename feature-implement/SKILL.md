---
name: feature-implement
description: Implement one phase of a planned feature. Use after the plan is approved, when the user says it's time to implement or start building, or when there is a plan.md with unchecked phases. Re-invoke for each subsequent phase.
disable-model-invocation: true
allowed-tools: Read, Write, Edit, Grep, Glob, Bash
argument-hint: "[feature-name]"
---

# Implementation Workflow

You are implementing one phase of a feature according to its approved plan.
Each invocation of this skill implements one phase and creates one MR.
Re-invoke for subsequent phases.

## Model check

Check your system context for the model you are running on. If your model name does not contain "sonnet", warn the user:

> ⚠️ This skill expects Claude Sonnet. You appear to be on [model name]. Sonnet is recommended here — implementation follows a detailed plan and doesn't need Opus-level reasoning. Continue anyway?

Wait for their response. If they say no, stop here.

## Current branch
!`git branch --show-current`

## Step 0: Read the plan

Read `docs/features/$ARGUMENTS/plan.md`. Find the first unchecked phase
in the checklist. If all phases are checked, tell the user the feature
is fully implemented and suggest running manual verification — and stop;
do not proceed to the branch check.

Note the phase number (N) of the first unchecked phase — this is the phase
you are about to implement.

## Step 1: Branch check

The branch for this phase must be `features/<FEATURE>-p<N>` (always include
the phase number, even for single-phase features — use `-p1`).

- If you're already on it, proceed.
- If you're on `main` or the project's default branch, create it:
  ```bash
  git checkout -b features/<FEATURE>-p<N>
  ```
- If you're on a different branch (including a `features/...` branch that
  doesn't match this pattern), stop and ask the user before switching.

Tell the user you've switched to a new branch. Never commit implementation
work directly to the default branch.

## Step 2: Implement the phase

Work through the phase's checklist items. For each item:
1. Make the change
2. Check off the item in the plan document

Use a capable but cost-effective model — the plan is detailed enough that
you should not need to make significant design decisions.

## Step 2.5: Verify "Verify" items empirically

Items in the checklist that begin with "Verify" — or that appear under
"Done when:" — typically specify a shell command (`uv build`, `unzip -l`,
`claude --print`, an end-to-end CLI invocation, etc.). Before checking
these off, **run the command and confirm the output**. Don't tick
based on having written code that *should* satisfy the criterion.

This is where the trust-the-checklist failure mode lives: an agent
writes the implementation, infers from the code that the verification
should pass, and ticks the box without confirming. The reviewer (or
the next session) then trusts the box and ships a broken state.

## Step 3: Handle deviations

If implementation reveals the plan needs to change:
- For minor deviations (same approach, different details): update the plan
  inline, note what changed and why, continue
- For significant deviations (different approach or scope): stop, explain
  the situation to the user, and get approval on the revised plan before
  continuing. Do not silently diverge from the approved plan.

## Step 4: Quality control

Before committing, invoke `/feature-qa` and work through all checks it
defines. Do not rely on having run QC incrementally — do a full pass now.

## Step 5: Commit and create MR

Commit with a clear message referencing the feature and phase. Push the
branch. Create an MR for this phase.

## Step 6: Verification guidance

Tell the user what to manually verify to confirm this phase is working.
Even if automated tests pass, give the human concrete steps:
- What to run or observe
- What the expected outcome looks like
- Any specific channels, dashboards, or CLI commands to check

Keep this brief and actionable. The human should be able to follow these
steps immediately after the MR is merged.

If there are subsequent phases, tell the user to say something like "next
phase" or "continue" once this MR is merged — you will automatically
re-invoke `/feature-implement $ARGUMENTS` when they do. Before re-invoking,
explicitly ask: "Has the MR for this phase been merged?" Do not start the
next phase until they confirm — starting phase N on an unmerged phase N-1
branch causes conflicts.

If all phases are now complete, tell the user:

> All phases implemented. When you're ready to review, switch to your Opus
> session and run `/feature-review <FEATURE>`.

Do not invoke `/feature-review` yourself.
