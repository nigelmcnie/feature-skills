---
name: feature-plan
description: Create an implementation plan for a feature with approved requirements. Use after requirements are approved, when the user says it's time to plan, or when there is a requirements.md but no plan.md yet for a feature they want to implement.
disable-model-invocation: true
allowed-tools: Read, Write, Edit, Grep, Glob, Bash, Agent
argument-hint: "[feature-name]"
---

# Planning Workflow

You are creating an implementation plan for a feature whose requirements
have been approved.

## Model check

Check your system context for the model you are running on. If your model name does not contain "opus", warn the user:

> ⚠️ This skill expects Claude Opus. You appear to be on [model name]. Opus is recommended here for stronger reasoning during planning. Continue anyway?

Wait for their response. If they say no, stop here.

## Branch check

Requirements and plan documents commit directly to main (the project's
default branch) so that implementation phase branches — which fork from
main — have the docs they need to reference.

Check the current branch:

```bash
git branch --show-current
```

- **On `main`** (or the project's default branch): run `git pull` to
  catch up, then proceed.
- **On any other branch**: stop and tell the user. Ask whether to switch
  to main, or whether this project uses a different doc convention.

Do not silently switch branches — uncommitted work might be lost.

## Step 1: Load the brief

Check for a project override at `docs/feature-skill-briefs/plan.md` and
read it if it exists. Otherwise, read the bundled brief at `brief.md` in
this skill's directory.

## Step 2: Read context

Read the following files:
- `docs/features/$ARGUMENTS/requirements.md` (approved requirements) —
  including any **Indicative implementation notes** section at the bottom,
  which carries forward plan-level context that didn't belong in the
  requirements body
- `CLAUDE.md` (architecture and conventions)
- All source modules referenced in the requirements' technical approach
- Existing test files to understand testing patterns

## Step 3: Draft

Plans are produced in **two formats** during Phase 2A. Markdown is
canonical (committed to the repo, source of truth for the workflow,
read by the implementing agent). HTML is the rich review surface.

### Pass 1 — Write the markdown plan

Write to `docs/features/$ARGUMENTS/plan.md`.

Follow the structure and guidance in the brief. Include:
- Key technical decisions with code snippets
- File structure showing what's created/modified
- Phase breakdown with test descriptions and MR chain
- Flat checklist of all steps at the bottom

### Pass 2 — Render the HTML plan

Use `~/.claude/skills/feature/plan-template.html` as the basis. Copy its
CSS and JavaScript verbatim. Render the markdown plan into the template's
structure: TOC sidebar, sections per the markdown's headings, syntax-
highlighted code blocks, phase badges, clickable checklist, click-to-
comment widget, sticky footer.

Write to `~/.claude/feature-docs/<PROJECT>/<FEATURE>/plan.html`, where
`<PROJECT>` is `basename $(git rev-parse --show-toplevel)`. Create
parent dirs with `mkdir -p` if needed.

Update in the template:
- `<title>`, the `<h1>` (feature name), the subtitle
- The TOC entries to match the actual sections in the plan (use `id`
  attributes on each `<section>` that match the TOC's `href` anchors)
- The JS `docId` constant — e.g. `docs/features/<FEATURE>/plan`

### Open it

Open the HTML in the user's browser:

```bash
google-chrome ~/.claude/feature-docs/<PROJECT>/<FEATURE>/plan.html &
```

The trailing `&` backgrounds the browser process so the agent doesn't wait.

## Step 4: Present and review in parallel

Tell the user the plan is ready for their review. Spawn a reviewer subagent
using the Agent tool with `run_in_background: true` so it runs while the
human reads. Tell the user the reviewer is running and they can start reading
immediately.

Prompt for the reviewer:

> You are reviewing an implementation plan for a feature.
> Read the plan at `docs/features/$ARGUMENTS/plan.md`.
> Read the requirements at `docs/features/$ARGUMENTS/requirements.md`.
> Read `CLAUDE.md` for architectural context.
>
> Check:
> - Does the plan cover all requirements? Flag any gaps.
> - Are the file paths correct? Do the modules exist?
> - Does it account for cross-cutting concerns called out in `CLAUDE.md`?
> - Are there dependency issues or blockers?
> - Is the phasing sensible? Can each phase be independently tested?
> - Are the code snippets consistent with existing patterns?
>
> Be specific. Reference sections by name.

## Step 5: Process reviewer feedback inline

When the reviewer returns, triage each item into one of:

- **Apply** — you agree with the reviewer, and the change is uncontroversial:
  factual corrections, missed dependencies, citation/path fixes, polish,
  wording. These get applied directly without asking.
- **Ask** — the item involves a real decision: product semantics, naming
  for concepts, scope or phasing trade-offs, deferral decisions, anything
  strategic. Surface inline with your take.
- **Skip** — you disagree with the reviewer or it's already covered.
  Briefly say why.

Present the triage in chat — do not write a synthesis document. Format:

> Reviewer feedback for plan:
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
> 2. <Question>. My take: <brief>.
>
> Reply with answers (or "go" to take my take on all of them) and I'll apply.

The user may also leave click-to-comment annotations in `plan.html` and
paste a JSON blob back. Format:

```json
{
  "doc": "docs/features/<FEATURE>/plan",
  "comments": [
    {"excerpt": "...", "text": "user comment"}
  ]
}
```

Fold those comments into the same triage — each comment is an additional
piece of feedback. The user may paste comments alongside the reviewer's
output, before it, or independently.

Wait for the user's response. Apply the "Will apply" items plus the
resolved questions and any actionable comment annotations.

If any "Need your call" answers reveal substantive design decisions
(principles, reasoning, broader implications beyond the specific item),
capture them in a "Design notes" section of
`docs/features/<FEATURE>/requirements.md`. Keep entries to one or two
lines, cite the review round.

After applying changes to `plan.md`, **re-render the HTML** (Step 3 Pass 2)
to keep `plan.html` in sync. The user may want to reload it.

Summarise what was applied to the user.

## Step 6: Iterate

If the user provides further feedback via any of:
- Inline `note: ...` annotations in `plan.md`
- Click-to-comment JSON pasted from `plan.html`
- Direct chat instructions

Then:
1. Re-read `plan.md` to pick up any inline edits
2. Apply the new feedback to `plan.md`
3. Re-render `plan.html` from the updated markdown
4. (If the changes are substantial) re-spawn the reviewer subagent on the
   updated content
5. Follow Step 5 (triage and process inline) for any new reviewer feedback

Repeat until the user approves conversationally.

## Step 7: Handoff

When the user signals approval — any of: "looks good", "approved", "let's
implement", "ready to implement", "start building", "time to implement", or
similar:

1. Check for any remaining `plan-feedback-N.md` files. If found, integrate
   them (per Step 5b) before proceeding.
2. Commit `docs/features/<FEATURE>/plan.md` and `docs/features/<FEATURE>/requirements.md`
   (the latter may have been updated with design notes) with the message
   `docs(<FEATURE>): add implementation plan` and push.
3. Tell the user:

   > Plan approved. When you're ready to implement, switch to your Sonnet session and run:
   >
   > `/feature-implement <FEATURE>`

Do not invoke `/feature-implement` yourself.
