---
name: feature-review
description: Review the complete merged implementation of a feature on main against its plan and requirements. Use after all phase MRs have landed, or when the user wants a fresh-eyes review of a fully merged feature.
disable-model-invocation: true
allowed-tools: Read, Grep, Glob, Bash, Agent
argument-hint: "[feature-name]"
---

# Review Workflow

You are reviewing the complete merged implementation of a feature on main —
not a branch in progress. Review happens after all phase MRs have landed.

## Model check

Check your system context for the model you are running on. If your model name does not contain "opus", warn the user:

> ⚠️ This skill expects Claude Opus. You appear to be on [model name]. Opus is recommended here for stronger reasoning during review. Continue anyway?

Wait for their response. If they say no, stop here.

## Step 1: Get on main and pull

Switch to the project's default branch (typically `main`) and pull the latest:

```bash
git checkout main
git pull
```

Tell the user you've switched to main and pulled.

## Step 2: Find the feature docs

If `$ARGUMENTS` is provided, use it as the feature name (FEATURE).
Otherwise, ask the user (we're on main now, so the branch name can't
be used for inference).

Resolve `PROJECT`: `PROJECT=$(basename $(git rev-parse --show-toplevel))`.

Locate the docs, preferring the API and falling back to dev-store HTML
then legacy markdown:

- Requirements: `GET http://127.0.0.1:8800/api/documents/$PROJECT/$FEATURE/requirements/1`
  from the webapp. On 200, use the JSON `sections` array. Fall back to
  `~/.claude/feature-docs/<PROJECT>/<FEATURE>/requirements.html` on 404;
  then `docs/features/<FEATURE>/requirements.md`.
- Plan: `GET http://127.0.0.1:8800/api/documents/$PROJECT/$FEATURE/plan/1`
  from the webapp. On 200, use the JSON `sections` array. Fall back to
  `~/.claude/feature-docs/<PROJECT>/<FEATURE>/plan.html` on 404; then
  `docs/features/<FEATURE>/plan.md`.

When read from a file, call the chosen path `REQUIREMENTS_PATH` /
`PLAN_PATH` as before.

Read these and `CLAUDE.md`.

## Step 3: Verify all phases are merged

Read the plan to count the phases. In an **API plan** (JSON), count the
distinct `phase-N` keys in the `sections` array. In an **HTML plan**,
count the distinct phase prefixes in `data-checklist-item="phase-<N>-..."`
attributes. In a **markdown plan**, count `### Phase N:` headers. For each
phase, verify the corresponding branch landed on main. Different merge
styles to handle:

- **Merge commits**: `git log --merges main --grep "features/<FEATURE>-p<N>"`
- **Squash/rebase**: `git log main --oneline | grep -i "<FEATURE>"` may catch
  the squashed message
- **Platform fallback**: `glab mr list --source-branch features/<FEATURE>-p<N> --state merged`
  (or `gh pr list --search "head:features/<FEATURE>-p<N>" --state closed`)

If any phase doesn't appear to be merged, stop and tell the user — review
should only run after everything has landed.

## Step 4: Establish the review baseline

Anchor the baseline on the **first phase commit**, not the earliest commit
that touched the feature's docs. A feature's context/requirements are often
captured many commits — and several other features — before implementation
starts, so the docs directory's first commit can sit far behind the actual
work and sweep all the intervening history into the review range. Find the
earliest implementation commit for this feature and use its parent:

```bash
# Earliest phase commit (the feat message survives squash/rebase and merge styles):
EARLIEST=$(git log main --reverse --format=%H --grep "feat(<FEATURE>)" | head -1)
# Fall back to the earliest phase-branch merge if no feat message is on main:
[ -z "$EARLIEST" ] && EARLIEST=$(git log main --reverse --format=%H --merges \
    --grep "<FEATURE>-p" | head -1)
BASELINE=$(git rev-parse "$EARLIEST^")
```

The diff range for review is `$BASELINE..main`. Show the user the
diff stat and log:

```bash
git diff $BASELINE..main --stat
git log $BASELINE..main --oneline
```

The range may include unrelated work that landed in parallel — that's
fine. The reviewer will be told to focus on feature-relevant changes.

If both lookups come back empty (an unusual phase-commit message, a purely
local feature, or weird platform state), ask the user for a baseline —
typically the commit just before the first phase MR for this feature landed
on main.

## Step 5: Fetch MR descriptions

For each phase's MR, fetch the description. Implementing agents often leave
useful clues there: noted deviations, items they couldn't verify, edge cases
they hit, alternative choices.

- **GitLab**: `glab mr list --source-branch features/<FEATURE>-p<N> --state merged`
  to find each MR number, then `glab mr view <number>` for each.
- **GitHub**: `gh pr list --search "head:features/<FEATURE>-p<N>" --state closed`
  then `gh pr view <number>` similarly.

Collate the descriptions so they can be passed to the reviewer.

If MRs can't be found (purely local feature, weird platform state), skip
this step and note it in the reviewer prompt.

## Step 6: Re-run plan verifications

Re-run any "Verify" / "Done when" shell commands the plan specifies. Build
artefacts (`uv build` + `unzip -l`), empirical checks (`claude --print`,
end-to-end CLI invocations), test suite, QC. These run against main — the
merged code is there now.

The reviewer subagent reads code and reports on consistency with the plan,
but it doesn't execute commands. Implementing agents sometimes mark
verification items complete based on the code they wrote — catch that
empirically here.

If a verification fails, that's a finding the reviewer should know about;
mention it in the prompt.

## Step 7: Spawn reviewer

Use the Agent tool with `run_in_background: true` to spawn a reviewer subagent.
Tell the user the reviewer is running and will surface findings shortly.

Prompt for the reviewer (substitute actual PROJECT, FEATURE, and BASELINE
resolved earlier):

> You are reviewing the complete merged implementation of a feature on main.
>
> Diff stat: <include diff stat from Step 4>
> Diff range: `$BASELINE..main` (substitute the actual SHA)
> Fetch the requirements from the webapp API:
> `GET http://127.0.0.1:8800/api/documents/$PROJECT/$FEATURE/requirements/1`
> (fall back to `~/.claude/feature-docs/<PROJECT>/<FEATURE>/requirements.html`
> or `docs/features/<FEATURE>/requirements.md` if the API returns 404).
> Fetch the plan from the webapp API:
> `GET http://127.0.0.1:8800/api/documents/$PROJECT/$FEATURE/plan/1`
> (fall back to `~/.claude/feature-docs/<PROJECT>/<FEATURE>/plan.html`
> or `docs/features/<FEATURE>/plan.md` if the API returns 404).
> MR descriptions: <paste collated descriptions from Step 5, or "no MRs
> available" if Step 5 was skipped>
>
> Read the full diff with `git diff $BASELINE..main`, the requirements, the
> plan, `CLAUDE.md`, and the MR descriptions above.
>
> The diff range may include unrelated work that landed in parallel. Focus
> your review on changes related to the feature.
>
> Check:
> - Does the implementation match the plan? Flag deviations.
> - Does it match the spirit of the requirements? Plans can diverge from
>   requirements; check both.
> - **Read the MR descriptions carefully for clues** — implementing agents
>   often note deviations, alternative choices, items they couldn't verify,
>   or edge cases they hit. Cross-reference these against the diff: were
>   noted deviations sound? Did they leave items the descriptions claim
>   are done but the diff doesn't actually do?
> - Are cross-cutting concerns called out in `CLAUDE.md` handled?
> - Are there tests? Do they cover the key behaviours?
> - Code quality issues (not style — the project's formatter handles that)
> - Any security concerns (stored user data, trust boundaries)?
> - When you find an issue, check whether the same *class* of issue recurs
>   elsewhere in the touched code — sibling call sites, parallel fields,
>   adjacent loops — and flag every instance, not just the first one you hit.
> - **Deviations**: where does the implementation diverge from the plan,
>   the requirements, the context doc, `CLAUDE.md`, or a prior decision?
>   Call each out explicitly with its magnitude — don't bury it as a minor
>   weakness.
> - **Risk**: which changes are the hardest to reverse or highest blast
>   radius (migrations, stored data, trust boundaries)?
>
> Produce structured feedback. Be specific with file paths and line numbers.

## Step 8: Triage and act

For each piece of reviewer feedback, decide your take — whether it
should be fixed, is a genuine decision for the developer, or can be
ignored, with reasoning.

Review converges in one pass. The dev-store history is unambiguous:
across the features reviewed so far, **no feature has ever needed a
second review round**, the findings are reliably minor, and the
developer reliably accepts them. So this stage does **not** write a
synthesis doc or poll the inbox the way `/feature-requirements` does —
it mirrors `/feature-plan`'s lighter inline triage, and it **acts**
rather than asking-then-waiting. You surface what you found, do the
uncontroversial work, and pause **only** for a genuine decision. The
developer keeps the ability to redirect after seeing your summary; the
history shows they almost never need to.

First, fold in any click-to-comment annotations the developer left on
the spine docs (a bonus input, not a gate — skip on any error):

```bash
curl -fsS "http://127.0.0.1:8800/api/documents/$PROJECT/$FEATURE/requirements/1/comments"
curl -fsS "http://127.0.0.1:8800/api/documents/$PROJECT/$FEATURE/plan/1/comments"
```

For each doc with a non-empty `comments` array, fold the comments in as
additional feedback. Integrate the consumed ids afterwards so they don't
resurface:

```bash
curl -fsS -X POST \
  "http://127.0.0.1:8800/api/documents/$PROJECT/$FEATURE/requirements/1/comments/integrate" \
  -H 'Content-Type: application/json' \
  -d '{"ids": [<ids>]}' 2>/dev/null || true
# repeat for plan/1/comments/integrate if it also had comments
```

### Triage

Sort each finding into one of three buckets:

- **Need your call**: a genuine decision — product/conceptual choices,
  scope or phasing trade-offs, deferrals, naming for concepts, a
  behaviour change, anything hard to reverse or high blast radius
  (stored data, security, trust boundaries), anything you're not
  confident about, or anything that assumes something about dev
  velocity. Two cases are easy to miss and belong here: (1) anything
  your take resolves by **deferring, cutting, or not doing** something
  raised — a confident "let's not" is still a direction decision, not an
  Apply; (2) **deviations** from the requirements, plan, context doc,
  `CLAUDE.md`, or a prior recorded decision — these capture what the
  developer already believes, so a meaningful divergence is where their
  input is most likely needed. **These, and only these, pause for the
  developer.**
- **Apply**: everything you'll fix without asking — bug fixes,
  factual/path corrections, defensive-test additions, naming, wording,
  observability, determinism fixes, schema minor specs, and any
  middle-ground feedback you agree with. When unsure whether something
  is a decision or just an Apply, lean Apply but state your take when you
  present it, so a wrong call is visible and cheap to reverse.
- **Skip**: already handled, out of scope, or you disagree — note why.

### Present and act

Present the triage inline — no synthesis doc, no inbox poll:

> Review feedback:
>
> **Applying:**
> - <one-line description of each Routine/Feedback item you'll fix>
>
> **Skipping:** (omit if none)
> - <one-line + why: already handled, out of scope, or you disagree>
>
> **Need your call:** (omit if none)
> 1. <the decision>. My take: <brief recommendation>.

Then:

- **No "Need your call" items** (the common case) → **proceed
  immediately; do not wait for a yes.** Continue into the iteration
  stage (Step 9), apply the "Applying" items, and summarise what you
  did when finished. The developer redirects after the fact if
  anything's off — the history shows they almost never need to.
- **"Need your call" items present** → surface them and wait. Apply any
  "Applying" items the decision can't affect; hold anything it might
  change. Resume once answered.
- **Nothing to apply and nothing to ask** (a fully clean review) → skip
  straight to Step 10 (mark shipped).

There is no review-feedback HTML doc in this flow — the triage lives in
the conversation and is consumed inline by the iteration that follows.
Decision capture and any feedback-doc archiving are handled inside the
iteration stage (`/feature-iterate` Step 2).

## Step 9: Iterate

When there are items to apply (the common case), **continue into the
iteration stage automatically — do not wait to be asked.** That is the
whole point of the act-then-summarise flow: the triage from Step 8 is
the input, and you carry it straight into the fixes. If you paused on a
"Need your call" item in Step 8, resume here once it's answered. If the
review found nothing to apply, skip to Step 10.

**Do NOT use the Skill tool to invoke `/feature-iterate`** — it sets
`disable-model-invocation: true`, which blocks the Skill tool. Read
`~/.claude/skills/feature-iterate/SKILL.md` and execute its
instructions inline in this conversation, treating the Step 8 triage as
the feedback to address (there is no synthesis doc to read).

You're on `main` here, so feature-iterate's Step 0.5 will isolate the
fixes in a worktree by default — that's intended; it keeps the applied
changes off the shared tree. The fixes then land via an iterate MR, so
"mark shipped" (Step 10) waits for that MR to merge, exactly as
feature-iterate's wrap-up describes.

## Step 10: Mark shipped

When the review cycle is complete with no outstanding items — either
the initial review had no findings, or the user signals they are
satisfied after iterations ("looks good", "all done", "ship it",
"nothing else", or similar):

Call the ship API to move this feature to Done:

```bash
curl -fsS -X POST "http://127.0.0.1:8800/api/projects/$PROJECT/features/$FEATURE/ship" \
  -H 'Content-Type: application/json' \
  -d '{"outcome": "Shipped. …one or two sentence summary of what landed…"}'
```

A 200 response means the feature is marked Done. If the webapp is
unreachable, skip silently.

Archive any leftover synthesis docs from older standalone review rounds
(the inline-triage flow writes no synthesis doc, so this is normally a
no-op):

```bash
mkdir -p ~/.claude/feature-docs/$PROJECT/<FEATURE>/.feedback-archive
mv ~/.claude/feature-docs/$PROJECT/<FEATURE>/review-feedback-*.html \
   ~/.claude/feature-docs/$PROJECT/<FEATURE>/.feedback-archive/ 2>/dev/null || true
```

Tell the user the feature is marked shipped.
