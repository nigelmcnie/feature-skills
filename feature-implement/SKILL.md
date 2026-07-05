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

Resolve `PROJECT` once: `PROJECT=$(basename "$(dirname "$(git rev-parse --git-common-dir)")")`.
`$ARGUMENTS` is the feature name (FEATURE).

Locate and read the plan, in this order of preference:

1. **API** — `GET /api/documents/$PROJECT/$FEATURE/plan/1` from the
   local webapp. This is the canonical location when the plan was
   authored via the API.
   ```bash
   curl -fsS "http://127.0.0.1:8800/api/documents/$PROJECT/$FEATURE/plan/1"
   ```
   A `200` response gives a JSON object with a `sections` array of
   `{"key": "...", "body": "..."}` objects.
2. **Dev-store HTML** — `~/.claude/feature-docs/<PROJECT>/<FEATURE>/plan.html`
   if it exists and the API returned 404 (legacy plans written before
   the API migration).
3. **Markdown** — `docs/features/<FEATURE>/plan.md` — older legacy.

Remember which source was used (API or file) and which format (sections
JSON, HTML, or markdown).

### Find the first unchecked phase

**API plan**: extract the `checklist` section body from the sections
array, then scan for unchecked items:

```bash
# After storing the API JSON response in PLAN_JSON:
CHECKLIST=$(echo "$PLAN_JSON" | python3 -c \
  "import sys,json; secs=json.load(sys.stdin)['sections']; \
   print(next((s['body'] for s in secs if s['key']=='checklist'), ''))")
echo "$CHECKLIST" | grep -oE \
  'data-checklist-item="phase-[0-9]+-[0-9]+"[^>]*>[[:space:]]*<input[^>]*>' \
  | grep -v ' checked'
```

**HTML plan file**: grep the file directly:

```bash
grep -oE 'data-checklist-item="phase-[0-9]+-[0-9]+"[^>]*>[[:space:]]*<input[^>]*>' "$PLAN_PATH" \
  | grep -v ' checked'
```

(The `[[:space:]]*` tolerates same-line whitespace. The checklist
adjacency contract requires the `<li>` and `<input>` on the same
line — if a re-render pretty-prints across multiple lines, the grep
will miss items.)

**Markdown plan**: find the first unchecked `- [ ]` item in the
checklist. The phase number is the most recent `### Phase N:` header
preceding it.

The first matching line names the next phase via its
`phase-<N>-<step>` ID.

If all items are checked, tell the user the feature is fully
implemented and suggest running manual verification — and stop. Do
not proceed to the branch check.

Note the phase number (N) — this is the phase you are about to
implement.

## Step 1: Isolate this phase in a worktree

**Decision-gate phases first.** If the phase's plan section reads as a
conditional decision gate rather than committed scope (e.g. "assess X,
take it only if it comes out clean, otherwise defer with a note" —
language like "decision gate, not committed scope" is a strong signal),
do the assessment in the current tree first, read-only — no worktree yet.
Only call `EnterWorktree` once the assessment concludes there is code to
write. If the verdict is to defer, there is no code phase to isolate at
all: skip straight to checking off the item (see "Checking off an item"
below) and go to Step 7 with nothing to commit.

Each phase is built in its own git worktree, so parallel agents in the
same repo never collide in the shared working tree. The branch must be
`features/<FEATURE>-p<N>` (always include the phase number, even for
single-phase features — use `-p1`), since review and MR-detection rely on
that name.

- If you're already on `features/<FEATURE>-p<N>` (e.g. resuming this
  phase), proceed.
- Otherwise, from `main` or the default branch, isolate the work. Tell the
  user in one line that you're isolating this phase in a worktree, then
  create it **the way this repo wants**:
  - **Check the repo's `CLAUDE.md` (and `.claude/`) for worktree
    instructions first.** Some repos need extra setup for a *working*
    worktree — database, ports, venv, env files — and provide a dedicated
    tool or script; `EnterWorktree` on its own bypasses that setup. If
    such instructions exist, follow them. They typically have you run the
    repo's tool to create the worktree under `.claude/worktrees/`, then
    call `EnterWorktree` with `path=<that worktree>` to switch the session
    into it.
  - **Otherwise, use the standard flow**: first fetch to ensure
    `origin/<default-branch>` is genuinely up to date (prior merged phases
    may not be in the local fetch cache yet):
    ```bash
    git fetch origin
    ```
    Then call `EnterWorktree` with name `<FEATURE>-p<N>`. It branches fresh
    from `origin/<default-branch>` (the `worktree.baseRef` default), so you
    start from the latest main — including prior merged phases.

    **Exception — no remote** (`git remote -v` is empty): `EnterWorktree`'s
    default `fresh` mode requires an origin and will fail. Instead, create the
    worktree manually then enter it by path:
    ```bash
    git worktree add .claude/worktrees/<FEATURE>-p<N> -b features/<FEATURE>-p<N>
    # then call EnterWorktree with path=.claude/worktrees/<FEATURE>-p<N>
    ```
  Then make sure you end up on a branch named `features/<FEATURE>-p<N>`,
  renaming if the tool or standard flow named it otherwise:
  ```bash
  git branch -m features/<FEATURE>-p<N>
  ```
  The worktree is a fresh checkout — unless the repo's tool already
  provisioned them, install whatever QC/build needs (`uv`-based projects
  resolve on first `uv run`).
- If you're on some other branch that doesn't match this pattern, stop and
  ask the user before doing anything.

Never commit implementation work directly to the default branch. If
worktrees are unavailable (not a git repo) or the user vetoes isolation,
fall back to `git checkout -b features/<FEATURE>-p<N>` in the current tree
and tell them you're not isolated.

## Step 2: Implement the phase

Work through the phase's checklist items. For each item:

1. Make the change.
2. Check off the item in the plan document (see below).

Use a capable but cost-effective model — the plan is detailed enough
that you should not need to make significant design decisions.

### Checking off an item

**API plan**: GET the current plan content, update the `checklist`
section HTML to add `checked` to the matching `<input>`, then PUT all
sections back:

1. GET current plan:
   ```bash
   PLAN_JSON=$(curl -fsS "http://127.0.0.1:8800/api/documents/$PROJECT/$FEATURE/plan/1")
   ```

2. In the `checklist` section body, change the matching item:
   ```
   <li data-checklist-item="phase-1-3"><input type="checkbox"><span class="label">…</span></li>
   ```
   becomes:
   ```
   <li data-checklist-item="phase-1-3"><input type="checkbox" checked><span class="label">…</span></li>
   ```
   Use the `data-checklist-item` ID to locate the right `<input>`.
   IDs are stable — don't pattern-match by item text.

3. PUT all sections back with the updated checklist:
   `sections` must be a JSON **object keyed by section key** — NOT an
   array like the GET response returns.
   ```bash
   curl -fsS -X PUT \
     "http://127.0.0.1:8800/api/documents/$PROJECT/$FEATURE/plan/1" \
     -H 'Content-Type: application/json' \
     -d '{"sections": {"overview": "...", "checklist": "...", "phase-1": "..."}, "actor": "agent"}'
   ```

**HTML plan file** (legacy — only when the plan was read from the
dev-store in Step 0): edit the file and add `checked` to the
matching `<input>`. No markdown re-export: `plan.md` is a
post-approval snapshot, deliberately frozen.

**Markdown plan** (legacy): change `- [ ]` to `- [x]` for the
matching item.

### Closing out a decision-gate item that was deferred

When a decision-gate phase (see Step 1) concludes "defer" rather than
"implement," the assessment itself is the deliverable — check the item
off (it's done: assessed and decided), but only after writing a durable
note explaining the outcome. Append it to the phase's own section in the
plan (not just the checklist label — IDs are stable, don't touch them):
what was assessed, the concrete reason it doesn't come out clean, and what
a future attempt would need. A bare checkmark with no rationale is opaque
to whoever reads the plan next; the note is what makes "defer" a real
answer instead of a shrug.

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

If a "Verify" step needs live credentials or interactive auth, attempt it
first — don't probe the environment for creds to decide whether to try, and
don't pre-skip the step. When the developer is present, their credential
store often prompts for approval (or, for a hook-blocked command like
`aws-vault`, they can refresh the session live) and the step just passes.
Only on failure: ask the developer directly (they may be reachable right
now and can unblock it in the moment) rather than silently deferring. If
they're genuinely unreachable or the service is down, note the constraint
in the MR description, provide a structural equivalent where possible (a
test that proves the same guarantee), and flag it as requiring manual
verification post-merge.

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

**No-remote repos** (`git remote -v` is empty): commit, then merge directly
into the default branch and remove the worktree — no push, no MR, no CI.
Skip to Step 7.

```bash
# from inside the worktree
git commit -m "feat(<FEATURE>): ..."
# exit worktree (keep), then from default branch:
git merge features/<FEATURE>-p<N> --no-edit
git worktree remove .claude/worktrees/<FEATURE>-p<N>
git branch -d features/<FEATURE>-p<N>
```

**With a remote**: commit with a clear message referencing the feature and
phase. Push the branch. Create an MR for this phase.

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
  | grep -qE 'Pipeline state: (success|failed|canceled)'; do
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

Before telling the user what to check, consider what live environment state
the verification assumes and close the gap yourself where safe:

- If the phase affects a service or process that reads from the repo (pull,
  reinstall, restart), do it now — don't list it as a user step. If you're
  unsure whether it's safe (shared service, running transactions, destructive
  deploy), ask first. For uv editable installs, pull the main checkout
  **before** restarting — the service reads from the editable source
  directory, so restart without pull serves stale code.
- For other state-change steps (migrations, cache flush, re-index): attempt
  them directly if non-destructive and reversible; ask if unsure.

Then give the user what's left — the things only a human can do:
- A direct link or command to check the result (don't make them look it up)
- What the expected outcome looks like
- Any specific channels, dashboards, or CLI commands to check

Keep this brief and actionable. The human should be able to follow these
steps immediately after the MR is merged.

Emit a `phase-report` (see `docs/handoff-protocol.md`) carrying this phase's
results across the merge gate. Tag the verification steps above as `safe`
(you may run them automatically once merged) or `human`; carry any unrunnable
"Verify" items (Step 2.5) as `verify_flags`; set `mr` to this phase's MR; and
use `notes` for anything else worth flagging to whoever picks this up — plan
deviations, surprises, things to watch. Before setting `status`, verify every
plan checklist item for all phases is ticked — check the plan API or file;
don't signal `all-complete` while any item remains unchecked. Set `status`
to `phase-complete` if phases remain, else `all-complete` (which attaches an
`agent-handoff` to `/feature-review`, Opus, `when: after-merge`).

With no handoff mechanism defined, the `phase-report` renders to the developer
as today's behaviour:

- **Subsequent phases remain** — tell the user to say "next phase" or
  "continue" once this MR is merged; you will automatically re-invoke
  `/feature-implement $ARGUMENTS` when they do. Before re-invoking, ask
  explicitly: "Has the MR for this phase been merged?" Do not start the next
  phase until they confirm — starting phase N on an unmerged phase N-1 branch
  causes conflicts.
- **All phases complete** — render the attached `agent-handoff`:

  > All phases implemented. When you're ready to review, switch to your Opus
  > session and run `/feature-review <FEATURE>`.

Do not invoke `/feature-review` yourself.

### Worktree teardown

The phase's work is safe on the remote branch once pushed, so the worktree
has done its job. Leave it in place until the MR merges (the branch is
checked out there), then remove it — once the user confirms the merge, or
at the start of the next phase. **For the final phase** (no next phase
exists to trigger cleanup), don't just go idle after rendering the
all-complete message — ask the user to confirm the MR merged, then tear
the worktree down before ending the session. Remove it the way this repo
wants: if its `CLAUDE.md` documents a worktree tool, use that to remove it
(it may also tear down the database/ports the tool set up); otherwise
`git worktree remove .claude/worktrees/<dir>` (or `ExitWorktree` with
`action: remove, discard_changes: true` if you're still inside it — the
branch always has commits from the merged phase, so `discard_changes` is
required). The next phase creates its own fresh worktree, so don't carry
this one forward.

## Step 8: Invite a process retro

Before wrapping up this session, add a soft one-line invite:

> Before you wrap up, consider `/feature-retro <FEATURE>` — it looks
> back over how the *process* went (not the code) and surfaces ways to
> streamline the feature-skills workflow itself.

This is a suggestion, not a step you run yourself. Skip it if the session
was trivial (e.g. a single-line fix with no friction worth reflecting on).
