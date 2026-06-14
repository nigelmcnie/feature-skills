---
name: feature-implement
description: Implement one phase of a planned feature. Use after the plan is approved, when the user says it's time to implement or start building, or when there is a plan with unchecked phases. Re-invoke for each subsequent phase.
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

Resolve `PROJECT` once: `PROJECT=$(basename $(git rev-parse --show-toplevel))`.
`$ARGUMENTS` is the feature name (FEATURE).

Locate the plan, in this order of preference:

1. `~/.claude/feature-docs/<PROJECT>/<FEATURE>/plan.html` — the
   canonical HTML in the dev-store. Use this when it exists.
2. Otherwise `docs/features/<FEATURE>/plan.md` — the legacy markdown
   plan (for features planned before the HTML migration).

Call the chosen path `PLAN_PATH` and remember which format it is.

### Find the first unchecked phase

**HTML plan**: every checklist `<li>` carries
`data-checklist-item="phase-<N>-<step>"`. An item is checked when its
`<input>` element has the `checked` attribute. Walk the items in
document order and find the smallest phase number `N` that still has
at least one item without `checked`. That's the phase you're about
to implement.

A quick scan:

```bash
grep -oE 'data-checklist-item="phase-[0-9]+-[0-9]+"[^>]*>[[:space:]]*<input[^>]*>' "$PLAN_PATH" \
  | grep -v ' checked'
```

(The `[[:space:]]*` tolerates same-line whitespace between the `<li>`
open tag and the `<input>`. The plan template's checklist adjacency
contract still requires them on the same line — if a re-render
pretty-prints the checklist across multiple lines, the grep will
miss items.)

The first matching line names the next phase via its
`phase-<N>-<step>` ID.

**Markdown plan**: find the first unchecked `- [ ]` item in the
checklist. The phase number is the most recent `### Phase N:` header
preceding it.

If all items are checked, tell the user the feature is fully
implemented and suggest running manual verification — and stop. Do
not proceed to the branch check.

Note the phase number (N) — this is the phase you are about to
implement.

## Step 1: Isolate this phase in a worktree

Each phase is built in its own git worktree, so parallel agents in the
same repo never collide in the shared working tree. The branch must be
`features/<FEATURE>-p<N>` (always include the phase number, even for
single-phase features — use `-p1`), since review and MR-detection rely on
that name.

- If you're already on `features/<FEATURE>-p<N>` (e.g. resuming this
  phase), proceed.
- Otherwise, from `main` or the default branch, isolate the work:
  1. Tell the user in one line that you're isolating this phase in a
     worktree.
  2. `EnterWorktree` with name `<FEATURE>-p<N>`. It branches fresh from
     `origin/<default-branch>` (the `worktree.baseRef` default), so you
     start from the latest main — including any prior merged phases — with
     no separate pull.
  3. Rename the worktree's branch to the MR convention:
     ```bash
     git branch -m features/<FEATURE>-p<N>
     ```
  4. The worktree is a fresh checkout: if the project needs installed
     dependencies to build or run QC (e.g. `node_modules`), install them
     now. `uv`-based projects resolve on first `uv run`.
- If you're on some other branch that doesn't match this pattern, stop and
  ask the user before doing anything.

Never commit implementation work directly to the default branch. If
`EnterWorktree` is unavailable (not a git repo) or the user vetoes
isolation, fall back to `git checkout -b features/<FEATURE>-p<N>` in the
current tree and tell them you're not isolated.

## Step 2: Implement the phase

Work through the phase's checklist items. For each item:

1. Make the change.
2. Check off the item in the plan document (see below).

Use a capable but cost-effective model — the plan is detailed enough
that you should not need to make significant design decisions.

### Checking off an item

**HTML plan** (`plan.html` in dev-store): edit `$PLAN_PATH` and add
the `checked` attribute to the `<input>` inside the matching
`<li data-checklist-item="phase-<N>-<step>">`:

```
<li data-checklist-item="phase-1-3"><input type="checkbox"><span class="label">…</span></li>
```

becomes

```
<li data-checklist-item="phase-1-3"><input type="checkbox" checked><span class="label">…</span></li>
```

Use the `data-checklist-item` ID to locate the right `<input>`. IDs
are stable across re-renders — don't pattern-match by item text. No
markdown re-export: `plan.md` (if it was exported at handoff) is a
post-approval snapshot, deliberately frozen at the start of
implementation.

**Markdown plan** (legacy): change `- [ ]` to `- [x]` for the
matching item.

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

- For minor deviations (same approach, different details): update
  `$PLAN_PATH` inline, note what changed and why, continue. For the
  HTML plan, edit the relevant `<section>` body directly. No
  re-export.
- For significant deviations (different approach or scope): stop,
  explain the situation to the user, and get approval on the revised
  plan before continuing. Do not silently diverge from the approved
  plan.

## Step 4: Quality control

Before committing, invoke `/feature-qa` and work through all checks
it defines. Do not rely on having run QC incrementally — do a full
pass now.

**Do NOT use the Skill tool to invoke `/feature-qa`** — it sets
`disable-model-invocation: true`, which blocks the Skill tool. Read
`~/.claude/skills/feature-qa/SKILL.md` and execute its instructions
inline in this conversation.

## Step 5: Commit and create MR

Commit with a clear message referencing the feature and phase. Push
the branch. Create an MR for this phase.

Note the source branch (`features/<FEATURE>-p<N>`) and the MR URL.
You'll watch the pipeline next.

## Step 6: Watch the pipeline

After the MR opens, CI fires. Don't end here — many failures the
agent could fix immediately get discovered hours later by the
human. Poll until the pipeline terminates and react.

The CLAUDE.md SessionStart hook (or `git remote -v`) tells you
whether this is GitLab (`glab`) or GitHub (`gh`). Use the matching
toolchain throughout this step.

### Wait for the pipeline to terminate

CI registration sometimes lags a push by a few seconds; if the
first status query returns "no pipeline found", wait ~10s and try
again.

Once the pipeline exists, watch it until it reaches a terminal
state. Use a background Bash with an until-loop so you're notified
when the pipeline terminates rather than burning context on
hand-rolled polls.

**GitLab:**

```bash
BRANCH=features/<FEATURE>-p<N>
until glab ci status -b "$BRANCH" 2>/dev/null \
  | grep -qE '(success|failed|canceled)'; do
  sleep 60
done
glab ci status -b "$BRANCH"
```

**GitHub:** `gh run watch --exit-status <RUN_ID>` blocks until
terminal and sets exit code from the run's status; use that
directly.

Upper bound: ~15 minutes. If the pipeline is still running at that
point, kill the watcher, tell the user it's running slow, give the
MR URL, and skip to Step 7. Don't hang here.

### On terminal state

- **Success** → continue to Step 7.
- **Canceled** → tell the user, don't auto-retry.
- **Failed** → triage and react.

### Triage failed jobs

Pull the failing job logs.

- GitLab: `glab ci view -b "$BRANCH"` to see job names + statuses,
  then `glab ci trace <job-id>` per failing job.
- GitHub: `gh run view "$RUN_ID" --log-failed` shows only the
  failing-step logs.

Categorise each failure:

- **Mechanical** (auto-fix attempted): ruff format / ruff lint /
  import order / trailing whitespace / any failure the project's
  QC tooling (`CLAUDE.md` § "QC before each commit") can fix by
  running locally. Type-checker errors with obvious one-line fixes
  (missing annotation, simple `cast`, narrow `assert`) count as
  mechanical; cross-module type refactors do not.
- **Strategic** (surface to user): test failures whose fix isn't
  obvious from the diff, behaviour mismatches, security findings,
  coverage drops, anything involving a real decision.
- **Flaky / infra**: transient errors — runner timeout, network
  failure, dependency-fetch failure. Retry the pipeline once
  (`glab ci retry <pipeline-id>` / `gh run rerun --failed`) and
  re-watch. If it fails again with the same shape, treat as
  strategic.

### Mechanical auto-fix loop

For each mechanical failure:

1. Reproduce locally: run the exact command the failing CI step
   ran (the trace usually shows it verbatim). Confirm you see the
   same error.
2. Apply the fix locally — `uv run ruff format`,
   `uv run ruff check --fix`, edit code for type errors, etc.
3. Re-run feature-qa locally (full pass; see Step 4) so the fix
   doesn't break anything else. **Do NOT use the Skill tool to
   invoke `/feature-qa`** — read its SKILL.md and execute inline.
4. Commit with the message
   `fix(<FEATURE>): address CI <type> failures [phase <N>]` (e.g.
   `address CI ruff failures`). Push.
5. Go back to "Wait for the pipeline" and watch the new pipeline.

Cap at **3 auto-fix attempts** per phase. If three rounds in and
CI still fails, escalate — repeated failures usually mean the
agent is fixing the wrong thing.

### Escalation

When escalating (strategic failure, cap reached, or pipeline
still running at the 15-min limit):

1. Tell the user the pipeline state, the failing job(s), and a
   one-line summary of each.
2. Quote the most relevant lines of the trace (`file:line` + error
   message — not the whole log).
3. Give the MR URL.
4. Continue to Step 7 so the user has the complete picture.

Don't loop on escalation. The human takes it from here.

## Step 7: Verification guidance

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

### Worktree teardown

The phase's work is safe on the remote branch once pushed, so the worktree
has done its job. Leave it in place until the MR merges (the branch is
checked out there), then remove it — once the user confirms the merge, or
at the start of the next phase:

```bash
git worktree remove .claude/worktrees/<FEATURE>-p<N>
```

(or `ExitWorktree` with `action: remove` if you're still inside it). The
next phase creates its own fresh worktree, so don't carry this one
forward.

## Step 8: Invite a process retro

Before wrapping up this session, add a soft one-line invite:

> Before you wrap up, consider `/feature-retro <FEATURE>` — it looks
> back over how the *process* went (not the code) and surfaces ways to
> streamline the feature-skills workflow itself.

This is a suggestion, not a step you run yourself. Skip it if the session
was trivial (e.g. a single-line fix with no friction worth reflecting on).
