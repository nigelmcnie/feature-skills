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

Locate the docs, preferring the dev-store HTML and falling back to
legacy markdown:

- Requirements:
  `~/.claude/feature-docs/<PROJECT>/<FEATURE>/requirements.html` if it
  exists, otherwise `docs/features/<FEATURE>/requirements.md`.
- Plan: `~/.claude/feature-docs/<PROJECT>/<FEATURE>/plan.html` if it
  exists, otherwise `docs/features/<FEATURE>/plan.md`.

Call the chosen paths `REQUIREMENTS_PATH` and `PLAN_PATH`.

Read these and `CLAUDE.md`.

## Step 3: Verify all phases are merged

Read `PLAN_PATH` to count the phases. In an HTML plan, count the
distinct phase prefixes in `data-checklist-item="phase-<N>-..."`
attributes; in a markdown plan, count `### Phase N:` headers. For each
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

Prompt for the reviewer (substitute the actual REQUIREMENTS_PATH and
PLAN_PATH resolved in Step 2):

> You are reviewing the complete merged implementation of a feature on main.
>
> Diff stat: <include diff stat from Step 4>
> Diff range: `$BASELINE..main` (substitute the actual SHA)
> Requirements: `<REQUIREMENTS_PATH>`
> Plan: `<PLAN_PATH>`
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
curl -fsS "http://127.0.0.1:8800/comments?path=$HOME/.claude/feature-docs/<PROJECT>/<FEATURE>/requirements.html"
curl -fsS "http://127.0.0.1:8800/comments?path=$HOME/.claude/feature-docs/<PROJECT>/<FEATURE>/plan.html"
```

Integrate any consumed ids afterwards (`POST /comments/integrate`, the
same contract the other skills use), so they don't resurface next round.

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

The canonical tracker is
`~/.claude/feature-docs/<PROJECT>/features.html`, where `<PROJECT>` is
`basename $(git rev-parse --show-toplevel)`. The repo's `features.md`
(if any) is a script-generated snapshot when `.feature-workflow.toml`
opts in.

### Workflow setup (first run)

If `~/.claude/feature-docs/<PROJECT>/.no-tracker` exists, the user
previously declined workflow setup — skip the rest of this step
("Mark shipped" is a no-op without a tracker).

If **none** of `~/.claude/feature-docs/<PROJECT>/features.html`,
`features.md` at the repo root, or `.feature-workflow.toml` at the
repo root exists, this project hasn't been set up. Offer once:

> This project doesn't have the feature workflow set up yet. Want me
> to scaffold it?
>
> 1. **features.html tracker** at
>    `~/.claude/feature-docs/<PROJECT>/features.html`.
> 2. **`.feature-workflow.toml`** at the repo root with all four
>    `[export]` keys set to `"markdown"` — feature docs and tracker
>    exported to the repo.
>
> Say no and I'll skip the mark-shipped step. To change the choice
> later, delete `~/.claude/feature-docs/<PROJECT>/.no-tracker`.

- **Accept**: create features.html (from
  `~/.claude/skills/feature/features-template.html`, blank tables)
  and `.feature-workflow.toml` (all four `[export]` keys =
  `"markdown"`). Continue.
- **Decline**: `mkdir -p ~/.claude/feature-docs/$PROJECT &&
  touch ~/.claude/feature-docs/$PROJECT/.no-tracker`, then skip the
  rest of this step.

### Ensure features.html exists in the dev-store

- **If `~/.claude/feature-docs/<PROJECT>/features.html` exists**: use
  it.
- **Otherwise, if `features.md` exists at the repo root**: migrate.
  Use `~/.claude/skills/feature/features-template.html` as the basis.
  Set the `<title>`, `<h1>`, and subtitle for the project. Render the
  existing markdown tables into the template's sections: `In
  Progress` rows → `<section id="in-progress">` tbody; `Available` →
  `<section id="available">`; `Done` (if present) →
  `<section id="done">`; `Suggested order` (if present) → keep as
  prose/list in `<section id="suggested-order">`. Convert each
  `[text](path)` link to `<a href="path">text</a>`. Rewrite
  feature-doc hrefs from the legacy repo-relative form
  `docs/features/<feature>/<artifact>.md` to the dev-store-sibling
  form `<feature>/<artifact>.html` (e.g.
  `docs/features/rule-ir/context.md` →
  `rule-ir/context.html`), so the canonical tracker has working
  click-through. Leave hrefs that don't match this pattern alone.
  Drop any `<tr class="empty">` placeholders for tbodies that
  now have real rows. Write the file to
  `~/.claude/feature-docs/<PROJECT>/features.html`.
- **Otherwise, if `.feature-workflow.toml` exists but no tracker**:
  scaffold a fresh `features.html` from
  `~/.claude/skills/feature/features-template.html` (blank tables).

### Move the feature to Done

If the feature has a row in the `In Progress` section, remove it and
append an equivalent row to the `Done` section's `<tbody>`. The Done
section is optional in the template — if the section is absent,
clone the structure from the template (`<section id="done">` with a
two-column table: Feature, Outcome) and insert it after the
`Available` section.

Each Done row has two cells:

- `<td class="feature-name"><a href="<FEATURE>/context.html">FEATURE</a></td>`
- `<td class="feature-outcome"><strong>Shipped.</strong> …short
  summary of what landed, drawn from the implementation diff and MR
  descriptions…</td>`

Keep the outcome cell to one or two sentences capturing the
substantive shape of what shipped — not a play-by-play of the
review. The current convention in established trackers (kea) is to
lead with "Shipped." in bold so the status reads at a glance.

If the feature was never claimed (no row in any section), skip
silently.

### Export to the repo (if configured) and commit

Check `.feature-workflow.toml`'s `[export].features` key. If
`markdown`:

```bash
feature-html-to-md \
    ~/.claude/feature-docs/<PROJECT>/features.html \
    features.md
```

If `html`:

```bash
cp ~/.claude/feature-docs/<PROJECT>/features.html features.html
```

If `none` or absent, skip the export and skip the commit.

If something was exported, commit the change directly to the current
branch (we're on main; see Step 1) with the message
`docs: mark <FEATURE> as shipped` and push.

### Archive any leftover synthesis docs

The inline-triage flow (Step 8) writes no synthesis doc, so there is
normally nothing to archive. But a doc may exist from an older
standalone review round — sweep any leftover into the archive
defensively (the `|| true` makes it a no-op when there's none):

```bash
mkdir -p ~/.claude/feature-docs/$PROJECT/<FEATURE>/.feedback-archive
mv ~/.claude/feature-docs/$PROJECT/<FEATURE>/review-feedback-*.html \
   ~/.claude/feature-docs/$PROJECT/<FEATURE>/.feedback-archive/ 2>/dev/null || true
```

Tell the user the feature is marked shipped.
