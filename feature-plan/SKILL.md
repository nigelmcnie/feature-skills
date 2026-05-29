---
name: feature-plan
description: Create an implementation plan for a feature with approved requirements. Writes the canonical plan.html to the developer-scoped store and optionally exports markdown/HTML to the repo via .feature-workflow.toml. Use after requirements are approved, when the user says it's time to plan, or when there is a requirements doc but no plan yet for a feature they want to implement.
disable-model-invocation: true
allowed-tools: Read, Write, Edit, Grep, Glob, Bash, Agent
argument-hint: "[feature-name]"
---

# Planning Workflow

You are creating an implementation plan for a feature whose requirements
have been approved.

The canonical plan doc is HTML in the developer-scoped store at
`~/.claude/feature-docs/<PROJECT>/<FEATURE>/plan.html`, where `<PROJECT>`
is `basename $(git rev-parse --show-toplevel)`. The repo gets an
exported snapshot (markdown or HTML) when `.feature-workflow.toml` opts
in.

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

## Step 1: Read context

Resolve `PROJECT` once and reuse it:

```bash
PROJECT=$(basename $(git rev-parse --show-toplevel))
```

`$ARGUMENTS` is the feature name (`<FEATURE>`).

Read the following:

- The approved requirements for this feature, in this order of
  preference:
  1. `~/.claude/feature-docs/<PROJECT>/<FEATURE>/requirements.html` if
     it exists — the canonical location.
  2. Otherwise `docs/features/<FEATURE>/requirements.md` — the
     legacy/exported location.

  Including any **Indicative implementation notes** section at the
  bottom, which carries forward plan-level context that didn't belong
  in the requirements body.
- `CLAUDE.md` (architecture and conventions).
- All source modules referenced in the requirements' technical
  approach.
- Existing test files to understand testing patterns.

## Step 2: Draft

Use `~/.claude/skills/feature/plan-template.html` as the basis. Copy
its CSS and JavaScript verbatim. Render the plan into the template's
structure: TOC sidebar, sections per the plan's headings, syntax-
highlighted code blocks, phase badges, clickable checklist, click-to-
comment widget, sticky footer.

Write to `~/.claude/feature-docs/<PROJECT>/<FEATURE>/plan.html`. Create
parent dirs with `mkdir -p` if needed.

Update in the template:

- `<title>`, the `<h1>` (feature name), the subtitle.
- The TOC entries to match the actual sections in the plan (use `id`
  attributes on each `<section>` that match the TOC's `href` anchors).
- The JS `docId` constant — e.g. `docs/features/<FEATURE>/plan`.

### Plan structure

A good implementation plan contains:

- **Overview**: what we're building, in one paragraph.
- **Key technical decisions**: choices that shape the implementation,
  with rationale. Include code snippets showing key interfaces.
- **File structure**: what files are created or modified.
- **Phase breakdown**: for each delivery phase from the requirements:
  - What's built
  - Which files are touched
  - Key code snippets (interfaces, data structures, function signatures)
  - What tests are needed
  - MR chain (each phase = one MR, invoked separately)
- **Checklist**: a flat checklist of all steps across all phases at
  the bottom of the document. The implementing agent checks items off
  as it works.

### Detail level

The plan should be detailed enough that an implementing agent (which
may be a different, less capable model) can follow it without making
significant design decisions. Include:

- Function signatures with type hints.
- Schema changes.
- Key conditional logic ("if X, then Y; otherwise Z").
- Test descriptions (what's tested, not full test code).

Do NOT include:

- Full implementation code (that's the implementing agent's job).
- Exact line numbers (files change).
- Style decisions (formatter handles them).

### Phasing

- Each phase results in a separate MR.
- Each phase is independently testable.
- Each phase is implemented by a separate invocation of
  `/feature-implement`.
- The implementing agent checks off items in this plan as it works.
- The plan is a living document — it gets updated if the approach
  changes during implementation. If a deviation is significant, pause
  and get the human to review the revised plan before continuing.

### Checklist format

Every checklist `<li>` **must** carry a stable
`data-checklist-item="phase-<N>-<step>"` attribute. `<N>` is the phase
number; `<step>` is the 1-indexed position of the item within that
phase. Example:

```html
<section id="checklist">
  <h2>Checklist</h2>
  <h3>Phase 1: Foo</h3>
  <ul class="checklist">
    <li data-checklist-item="phase-1-1"><input type="checkbox"><span class="label">Step A.</span></li>
    <li data-checklist-item="phase-1-2"><input type="checkbox"><span class="label">Step B.</span></li>
  </ul>
  <h3>Phase 2: Bar</h3>
  <ul class="checklist">
    <li data-checklist-item="phase-2-1"><input type="checkbox"><span class="label">Step C.</span></li>
  </ul>
</section>
```

`feature-implement` marks items checked by `data-checklist-item` ID
rather than positional or text matching, so the IDs must be unique
and stable across re-renders. If the plan iterates and items get
reordered or inserted, mint new IDs for new items but preserve
existing IDs for items that already exist.

**Adjacency contract**: keep `<li>` and the inner `<input>` on the
same line (or with only whitespace between them). The detector used
by `feature-implement` / the router greps for unchecked items via
the `<li ...><input...>` pattern; pretty-printing the checklist
across multiple lines would make the detector miss items and report
"all done" prematurely. Re-renders (Step 4 / Step 5 below) must
preserve the single-line item shape.

Items within each phase are ordered as they will be implemented.

### Quality control

Reference `CLAUDE.md` for quality control steps rather than hardcoding
them. Instruct the implementing agent to follow whatever `CLAUDE.md`
says at implementation time.

### Export to the repo (if configured)

Check `.feature-workflow.toml` at the repo root. The relevant key is
`[export].plan`. If the file is absent or the key is missing or set to
`"none"`, skip this step.

Otherwise:

- **`markdown`**:

  ```bash
  mkdir -p docs/features/<FEATURE>
  feature-html-to-md \
      ~/.claude/feature-docs/<PROJECT>/<FEATURE>/plan.html \
      docs/features/<FEATURE>/plan.md
  ```

- **`html`**:

  ```bash
  mkdir -p docs/features/<FEATURE>
  cp ~/.claude/feature-docs/<PROJECT>/<FEATURE>/plan.html \
     docs/features/<FEATURE>/plan.html
  ```

Remember the export-target path; you'll commit it at handoff (Step 6).

### Open it

```bash
google-chrome ~/.claude/feature-docs/<PROJECT>/<FEATURE>/plan.html &
```

The trailing `&` backgrounds the browser process so the agent doesn't
wait.

## Step 3: Present and review in parallel

Tell the user the plan is ready for their review and that the HTML is
open in Chrome. Spawn a reviewer subagent using the Agent tool with
`run_in_background: true` so it runs while the human reads.

Prompt for the reviewer:

> You are reviewing an implementation plan for a feature.
> Read the plan at `~/.claude/feature-docs/<PROJECT>/<FEATURE>/plan.html`.
> Read the requirements at `~/.claude/feature-docs/<PROJECT>/<FEATURE>/requirements.html`
> (fall back to `docs/features/<FEATURE>/requirements.md` if the HTML
> doesn't exist).
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

## Step 4: Process reviewer feedback inline

When the reviewer returns, triage each item into one of:

- **Apply** — you agree with the reviewer, and the change is
  uncontroversial: factual corrections, missed dependencies,
  citation/path fixes, polish, wording. These get applied directly
  without asking.
- **Ask** — the item involves a real decision: product semantics,
  naming for concepts, scope or phasing trade-offs, deferral
  decisions, anything strategic. Surface inline with your take.
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

The user may also leave click-to-comment annotations in `plan.html`
and paste a JSON blob back. Format:

```json
{
  "doc": "docs/features/<FEATURE>/plan",
  "comments": [
    {"excerpt": "...", "text": "user comment"}
  ]
}
```

Fold those comments into the same triage — each comment is an
additional piece of feedback. The user may paste comments alongside
the reviewer's output, before it, or independently.

Before folding the blob in, sanity-check the `doc` field: it should
be `docs/features/<FEATURE>/plan`. If it doesn't match (wrong
feature, or pasted from a different doc by mistake), warn the user
inline and don't proceed until they confirm.

Wait for the user's response. Apply the "Will apply" items plus the
resolved questions and any actionable comment annotations.

If any "Need your call" answers reveal substantive design decisions
(principles, reasoning, broader implications beyond the specific
item), capture them in a **Design notes** section of
`~/.claude/feature-docs/<PROJECT>/<FEATURE>/requirements.html` (add
the section if it doesn't exist). Keep entries to one or two lines,
cite the review round. Re-run the requirements export if
`.feature-workflow.toml` opts in for `requirements`.

### Re-render plan.html

After integrating the round of feedback, **rewrite `plan.html` from
scratch** — a fresh render that incorporates all applied items.
Preserve existing `data-checklist-item` IDs for unchanged steps; mint
new IDs for new ones. The fresh-render discipline mirrors the
historical markdown workflow: the canonical HTML reflects the full
integrated state, not a patchwork of in-place edits.

### Re-run the export (if configured)

If `.feature-workflow.toml` opts in for `plan`, re-run the export
step (markdown or HTML copy) so the repo snapshot reflects the
integrated state.

Summarise what was applied to the user. They can refresh the Chrome
tab to see the new render.

## Step 5: Iterate

If the user provides further feedback via any of:

- Click-to-comment JSON pasted from `plan.html`.
- Direct chat instructions.

Then:

1. Re-read `plan.html` to pick up its current state.
2. Apply the new feedback by rewriting `plan.html` (fresh render).
3. If the changes are substantial, re-spawn the reviewer subagent on
   the updated HTML.
4. Re-run the export (if configured).
5. Follow Step 4 (triage) for any new reviewer feedback.

Repeat until the user approves conversationally.

## Step 6: Handoff

When the user signals approval — any of: "looks good", "approved",
"let's implement", "ready to implement", "start building", "time to
implement", or similar:

1. Re-confirm: integrate any unprocessed click-to-comment feedback
   (per Step 4) before proceeding.
2. Commit only what ended up in the repo via the export step:
   - If `[export].plan` is `markdown` or `html`, commit
     `docs/features/<FEATURE>/plan.{md,html}`.
   - If `requirements.html` was updated with design notes in this
     session and `[export].requirements` opts in, the regenerated
     `docs/features/<FEATURE>/requirements.{md,html}` is also
     pending — commit it too.
   - If both keys are `none` or absent, there's nothing to commit —
     the canonical HTML in the dev-store is local-only working
     memory. Skip the commit step.
3. Use the message `docs(<FEATURE>): add implementation plan`. Push.
4. Tell the user:

   > Plan approved. When you're ready to implement, switch to your Sonnet session and run:
   >
   > `/feature-implement <FEATURE>`

Do not invoke `/feature-implement` yourself.
