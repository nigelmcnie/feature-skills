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

Find the earliest commit on main that touched the feature's docs
directory, and use its parent as the baseline:

```bash
EARLIEST=$(git log --reverse --diff-filter=A --format=%H -- "docs/features/<FEATURE>/" | head -1)
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

If `docs/features/<FEATURE>/` doesn't exist in the repo (the project's
`.feature-workflow.toml` has all `[export]` keys set to `"none"`, so
nothing was exported here), the `git log` lookup returns empty. In
that case, ask the user for a baseline — typically the commit just
before the first phase MR for this feature landed on main.

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
>
> Produce structured feedback. Be specific with file paths and line numbers.

## Step 8: Produce feedback synthesis document

For each piece of reviewer feedback, decide your take. **My take**
should say whether it should be fixed, is a blocker, or can be
ignored — with reasoning. Address blocking issues before suggestions
or nitpicks.

### Triage

Items get bucketed into three tiers:

- **Needs your input**: product/conceptual decisions, scope or
  phasing trade-offs, deferral decisions, naming for concepts,
  anything you're not confident about, anything where you might be
  making assumptions about dev velocity.
- **Routine**: only items you're highly confident are
  uncontroversial — factual citation/path fixes, naming mechanics
  (rename X to Y), wording polish, defensive-test additions,
  observability/logging granularity, schema minor specs.
- **Feedback** (the middle): everything else, in the reviewer's
  original order.

When in doubt, prefer **Feedback** over **Routine**. The cost of a
Feedback item that turns out to be uncontroversial is small; the
cost of a misclassified Routine item is larger.

Item-level guidance:

- **Numbered titles**: descriptive enough that a reader grasps the
  issue at a glance. Number continuously across all three tiers
  (1, 2, 3, …), not restarting per section.
- **Detail paragraph**: explain the item simply, in plain language —
  what it is, where it occurs, and why it matters — so the reader
  grasps it without holding the full review in their head. Assume
  they haven't been following along closely: spell out jargon, name
  the concrete file/section, and avoid terse shorthand. A sentence or
  two is usually enough. Skip only in the Routine tier.
- **My take**: focus on substance. Length matches the complexity of
  the call. In the Routine tier, keep it to one line.
- **"Your thoughts"**: left blank in the top and middle tiers (the
  HTML form provides the textareas). The Routine tier has no input
  — the user pushes back in chat if needed.

### Pick the next N

Count existing review-feedback files across both the dev-store
(`~/.claude/feature-docs/<PROJECT>/<FEATURE>/`, including
`.feedback-archive/`) and the legacy repo location
(`docs/features/<FEATURE>/`, including `.feedback-archive/`). Take
the max N and increment. If none exist, `N = 1`.

### Write the HTML synthesis doc

Use `~/.claude/skills/feature/feedback-template.html` as the basis.
Copy its CSS and JavaScript verbatim. Render the triaged items into
the template's three-tier structure (Needs your input / Feedback /
Routine).

Write to
`~/.claude/feature-docs/<PROJECT>/<FEATURE>/review-feedback-<N>.html`.
Create parent dirs with `mkdir -p` if needed.

Update in the template:
- `<title>`, the `<h1>`, the subtitle (e.g. "Review Feedback Synthesis #N").
- The meta line (item counts).
- The textarea total in the footer.
- The JS `docId` constant — e.g.
  `docs/features/<FEATURE>/review-feedback-<N>`.

### Open it

It's in the inbox at `http://127.0.0.1:8800`.

### Poll for submission

After writing the doc, force-walk so the webapp indexes it:

```bash
curl -fsS -X POST http://127.0.0.1:8800/admin/discover >/dev/null 2>&1 || true
```

Then poll `GET /synthesis-response?path=<ABS_PATH>` every 5 seconds (where
`<ABS_PATH>` is the absolute path of the doc you just wrote, e.g.
`~/.claude/feature-docs/<PROJECT>/<FEATURE>/review-feedback-<N>.html`):

```bash
curl -fsS "http://127.0.0.1:8800/synthesis-response?path=$HOME/.claude/feature-docs/<PROJECT>/<FEATURE>/review-feedback-<N>.html"
```

- `curl` error → server unreachable; fall back to clipboard (see below).
- `404` → not yet indexed; sleep 5, retry.
- `200 submitted=false` → awaiting the human; sleep 5, retry. Emit a brief
  "still waiting in the inbox…" line roughly every 60 s.
- `200 submitted=true` → read `responses` and `routine_flags` from the
  JSON. Then fetch active comments from the spine docs:

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
  comments** on the relevant doc and paste the JSON blob:
  `{"doc": "docs/features/<FEATURE>/requirements", "comments": [...]}`.

**Fallback**: if the server is unreachable or the user gives up ("just paste
it"), ask them to click **Copy responses** and paste the JSON blob. The
`responses`/`routine_flags` shape is identical either way. See
`docs/webapp-polling.md` in the feature-skills repo for the full convention.

**Sanity-check (clipboard fallback only)**: verify the `doc` field of any
pasted blob — for the synthesis blob it should be
`docs/features/<FEATURE>/review-feedback-<N>` for the N you just opened.
If it doesn't match, warn and confirm before proceeding.

Then parse and summarise which items will be addressed in
`/feature-iterate` and which are being set aside. The synthesis HTML
stays in dev-store for `/feature-iterate` to consume.

## Step 9: Handoff

If there are findings to address and the user wants to act on them —
any of: "let's fix those", "address the feedback", "iterate", "go
ahead", or similar — automatically continue into the iteration stage.

**Do NOT use the Skill tool to invoke `/feature-iterate`** — it sets
`disable-model-invocation: true`, which blocks the Skill tool. Read
`~/.claude/skills/feature-iterate/SKILL.md` and execute its
instructions inline in this conversation.

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

### Archive any unprocessed synthesis docs

If the user ships without iteration, the synthesis HTML from Step 8
is still live in
`~/.claude/feature-docs/<PROJECT>/<FEATURE>/review-feedback-<N>.html`.
Archive it now:

```bash
mkdir -p ~/.claude/feature-docs/$PROJECT/<FEATURE>/.feedback-archive
mv ~/.claude/feature-docs/$PROJECT/<FEATURE>/review-feedback-*.html \
   ~/.claude/feature-docs/$PROJECT/<FEATURE>/.feedback-archive/ 2>/dev/null || true
```

If `/feature-iterate` already ran, the file is already archived and
the move is a no-op.

Tell the user the feature is marked shipped.
