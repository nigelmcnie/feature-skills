---
name: feature-context
description: "Capture a feature idea for later — write a context.html to the developer-scoped store and add an entry to the Available section of the project's feature tracker. Use when the user wants to stash an idea that's emerged from the current conversation. Common trigger phrases include \"let's capture a feature for this\", \"write a context for a new feature\", \"add a feature for X\", \"let's get a feature/context up for Y\", \"stash this as a feature\", \"put it in the available features\", \"queue this up as a feature\", and \"we should track this as a feature for later\"."
allowed-tools: Read, Write, Edit, Grep, Glob, Bash
argument-hint: "[feature-name]"
---

# Feature Context Workflow

You are capturing background context for a feature that may be worked on later.
This is the historical ledger a future requirements session will draw on — not
requirements itself.

The primary source of context is the **current conversation**: distill what's
been discussed into the structure outlined in Step 4.

HTML is canonical; it lives in a developer-scoped store at
`~/.claude/feature-docs/<PROJECT>/<FEATURE>/context.html`, where `<PROJECT>`
is `basename $(git rev-parse --show-toplevel)`. The repo gets an export
(markdown or HTML) only if `.feature-workflow.toml` opts in.

## Step 1: Establish the feature name

Pick a short kebab-case name and proceed. Don't ask for permission to
invoke this skill — the trigger language already gave it. Don't bikeshed
the name.

Sources, in order of preference:

1. If `$ARGUMENTS` is provided, use it verbatim.
2. Otherwise, pick a name from the conversation. The clearer the user's
   ask, the less you should hesitate.
3. Only if the conversation truly doesn't make a name obvious (rare),
   ask for the name once — and only the name; don't ask whether to proceed.

If the name turns out to be wrong, the user can rename the directory or
the `features.md` row after — it's cheap to fix. Don't pre-validate by
asking.

Store the chosen name as FEATURE. Mention the name in your "done" message
at Step 9 so the user knows what you chose.

## Step 2: Workflow setup (first run)

Resolve `PROJECT` once: `PROJECT=$(basename $(git rev-parse --show-toplevel))`.

The feature workflow needs two pieces to fully engage with the repo:

1. **features.html** at `~/.claude/feature-docs/<PROJECT>/features.html`
   — the canonical project-level tracker (local-only).
2. **`.feature-workflow.toml`** at the repo root — opts the repo into
   exporting feature docs (markdown / HTML / none per artifact).

Check setup state and act:

- **If `~/.claude/feature-docs/<PROJECT>/.no-tracker` exists**: the
  user declined setup previously. Skip this step; the rest of the
  skill runs dev-store-only.
- **If `~/.claude/feature-docs/<PROJECT>/features.html` exists, OR
  `features.md` exists at the repo root, OR `.feature-workflow.toml`
  exists at the repo root**: setup has happened (perhaps partially).
  Skip this step.
- **Otherwise**: ask the user once:

  > This project doesn't have the feature workflow set up yet. Want
  > me to scaffold it?
  >
  > 1. **features.html tracker** at
  >    `~/.claude/feature-docs/<PROJECT>/features.html` — canonical,
  >    local-only.
  > 2. **`.feature-workflow.toml`** at the repo root with all four
  >    `[export]` keys set to `"markdown"` — feature docs and the
  >    tracker get exported to `docs/features/<feature>/` and
  >    `features.md`, committed alongside code.
  >
  > Say no and I'll just write to the dev-store (private to your
  > machine, nothing in the repo). To change the choice later,
  > delete `~/.claude/feature-docs/<PROJECT>/.no-tracker`.

  - **Accept**: create
    `~/.claude/feature-docs/<PROJECT>/features.html` from
    `~/.claude/skills/feature/features-template.html` (set
    `<title>`, `<h1>`, subtitle for the project; leave tables
    empty). Write `.feature-workflow.toml` at the repo root with:

    ```toml
    [export]
    context = "markdown"
    requirements = "markdown"
    plan = "markdown"
    features = "markdown"
    ```

  - **Decline**: write the marker:

    ```bash
    mkdir -p ~/.claude/feature-docs/$PROJECT
    touch ~/.claude/feature-docs/$PROJECT/.no-tracker
    ```

## Step 3: Read context

Read:
- `CLAUDE.md` (architecture and conventions)
- `features.md` if the project has one — to see what already exists and
  avoid duplicating
- Any specific docs the user has pointed to in the conversation

## Step 4: Draft context.html

Use `~/.claude/skills/feature/context-template.html` as the basis. Copy
its CSS and JavaScript verbatim. Render the conversation's distilled
context into the template's sections:

- **Problem space and motivation** (`id="problem-space"`): why this
  might be worth doing, what's broken or missing, what conversations
  or observations triggered it.
- **Related work** (`id="related-work"`): existing patterns or features
  in the codebase that connect to this; link to other context /
  requirements docs when relevant.
- **Constraints and considerations** (`id="constraints"`): what to watch
  for, dependencies, prior decisions that shape the space.
- **Links** (`id="links"`): design docs, customer reports, Slack
  threads, tickets, external references.
- **Open questions** (`id="open-questions"`): things worth resolving
  when requirements get written.

Omit any section that genuinely has nothing real to put in it — don't
pad with placeholder content.

Update in the template:
- `<title>`, the `<h1>`, the subtitle.
- The JS `docId` constant — e.g. `docs/features/<FEATURE>/context`.

Write to `~/.claude/feature-docs/<PROJECT>/<FEATURE>/context.html`,
where `<PROJECT>` is `basename $(git rev-parse --show-toplevel)`.
Create parent dirs with `mkdir -p` if needed.

Primary source is the recent conversation. Distill — do not transcribe.
If the user discussed a problem, the rationale for solving it, related
work, or constraints, those go in. Conversational filler does not.

Context is not requirements: keep user stories, technical approaches,
phase breakdowns, and wishlist features out. Capture *why* this came
up, not just *what* was discussed. Acknowledge unknowns — a clear
"open question" beats a half-formed guess.

## Step 5: Export to the repo (if configured)

Check `.feature-workflow.toml` at the repo root. The relevant key is
`[export].context`. If the file is absent or `context` is missing or
set to `"none"`, skip this step entirely.

Otherwise:

- **`markdown`**: run the export script to produce
  `docs/features/<FEATURE>/context.md`:

  ```bash
  mkdir -p docs/features/<FEATURE>
  feature-html-to-md \
      ~/.claude/feature-docs/<PROJECT>/<FEATURE>/context.html \
      docs/features/<FEATURE>/context.md
  ```

- **`html`**: copy the HTML in place:

  ```bash
  mkdir -p docs/features/<FEATURE>
  cp ~/.claude/feature-docs/<PROJECT>/<FEATURE>/context.html \
     docs/features/<FEATURE>/context.html
  ```

Remember the export-target path (the markdown or HTML file just written
into the repo); you'll commit it in Step 8.

## Step 6: View in the webapp inbox

It's in the inbox at `http://127.0.0.1:8800`.

## Step 7: Update the features tracker

If `~/.claude/feature-docs/<PROJECT>/.no-tracker` exists, the user
declined setup in Step 2 — skip this entire step.

Otherwise, the canonical tracker is
`~/.claude/feature-docs/<PROJECT>/features.html`. The repo's
`features.md` (if any) is a script-generated snapshot when
`.feature-workflow.toml` opts in.

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
- **Otherwise, if neither exists**: skip this entire step (Step 2's
  setup offer was probably skipped or accepted-but-toml-only; this
  project doesn't have a tracker).

### Add the row to Available

Append a `<tr>` to the `Available` section's `<tbody>` with two cells:

- `<td class="feature-name"><a href="<FEATURE>/context.html">FEATURE</a></td>`
- `<td class="feature-notes">…one-line note about what this is…</td>`

Do not move anything to In Progress — this feature is being captured
for later, not started now. If the `Available` tbody had a
`<tr class="empty">` placeholder, remove it now.

### Export to the repo (if configured)

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

If `none` or absent, skip. The tracker state is local-only in that
case.

Remember the export-target path; you'll commit it in Step 8.

## Step 8: Commit and push

Commit whatever ended up in the repo this session:

- The context export-target file from Step 5 (if anything was
  exported).
- The features tracker export-target file from Step 7 (if anything
  was exported).

Use the message `docs: capture <FEATURE> context` and push.

If nothing was exported in either step, skip — there's nothing to
commit. The canonical HTML in the dev-store is local-only working
memory.

## Step 9: Done

Tell the user the context is captured and that `/feature <FEATURE>`
will pick it up when they're ready to work on it. Mention the chosen
FEATURE name. Then return to whatever the conversation was doing before.
