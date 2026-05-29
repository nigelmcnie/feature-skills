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

If `$ARGUMENTS` is provided, use it as the feature name (FEATURE). Otherwise,
ask the user (we're on main now, so the branch name can't be used for
inference). Read:
- `docs/features/<FEATURE>/requirements.md`
- `docs/features/<FEATURE>/plan.md`
- `CLAUDE.md`

## Step 3: Verify all phases are merged

Read `plan.md` to count the phases (look for `### Phase N:` headers in the
Checklist section). For each phase, verify the corresponding branch landed
on main. Different merge styles to handle:

- **Merge commits**: `git log --merges main --grep "features/<FEATURE>-p<N>"`
- **Squash/rebase**: `git log main --oneline | grep -i "<FEATURE>"` may catch
  the squashed message
- **Platform fallback**: `glab mr list --source-branch features/<FEATURE>-p<N> --state merged`
  (or `gh pr list --search "head:features/<FEATURE>-p<N>" --state closed`)

If any phase doesn't appear to be merged, stop and tell the user — review
should only run after everything has landed.

## Step 4: Establish the review baseline

Find the earliest commit on main that touched the feature's docs directory,
and use its parent as the baseline:

```bash
EARLIEST=$(git log --reverse --diff-filter=A --format=%H -- "docs/features/<FEATURE>/" | head -1)
BASELINE=$(git rev-parse "$EARLIEST^")
```

The diff range for review is `$BASELINE..main`. Show the user the diff stat
and log:

```bash
git diff $BASELINE..main --stat
git log $BASELINE..main --oneline
```

The range may include unrelated work that landed in parallel — that's fine.
The reviewer will be told to focus on feature-relevant changes.

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

Prompt for the reviewer:

> You are reviewing the complete merged implementation of a feature on main.
>
> Diff stat: <include diff stat from Step 4>
> Diff range: `$BASELINE..main` (substitute the actual SHA)
> Requirements: `docs/features/<FEATURE>/requirements.md`
> Plan: `docs/features/<FEATURE>/plan.md`
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

When the reviewer returns, check how many `review-feedback-N.md` files already exist
in `docs/features/<FEATURE>/` and create the next numbered one (e.g.
`review-feedback-1.md` if none exist, `review-feedback-2.md` if one exists, etc.).

Follow the format and triage guidance in
`/home/nigel/.claude/skills/feature/feedback-template.md`. For each piece
of reviewer feedback, **My take** should say whether it should be fixed,
is a blocker, or can be ignored — with reasoning. Address blocking issues
before suggestions or nitpicks.

Tell the user the synthesis document is ready and ask them to fill in their
thoughts on items in the **Needs your input** and **Feedback** sections.

Once the user indicates they are done, summarise which items will be addressed in
`/feature-iterate` and which are being set aside. The synthesis document serves as
the brief for the iteration step — leave it in place for `/feature-iterate` to consume.

## Step 9: Handoff

If there are findings to address and the user wants to act on them — any of:
"let's fix those", "address the feedback", "iterate", "go ahead", or similar
— automatically invoke `/feature-iterate <FEATURE>`.

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
  `[text](path)` link to `<a href="path">text</a>`, leaving the href
  as-is. Drop any `<tr class="empty">` placeholders for tbodies that
  now have real rows. Write the file to
  `~/.claude/feature-docs/<PROJECT>/features.html`.
- **Otherwise, if neither exists**: skip this entire step. The
  project doesn't use a tracker.

### Move the feature to Done

If the feature has a row in the `In Progress` section, remove it and
append an equivalent row to the `Done` section's `<tbody>`. The Done
section is optional in the template — if the section is absent,
clone the structure from the template (`<section id="done">` with a
two-column table: Feature, Outcome) and insert it after the
`Available` section.

Each Done row has two cells:

- `<td class="feature-name"><a href="docs/features/<FEATURE>/context.md">FEATURE</a></td>`
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

Tell the user the feature is marked shipped.
