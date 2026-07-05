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

The context document is authored and stored in the webapp's DB via the
logical-key API, addressed as `<PROJECT>/<FEATURE>/context/1`. `<PROJECT>`
is `basename "$(dirname "$(git rev-parse --git-common-dir)")"` (worktree-safe —
resolves to the main checkout's name even from inside a phase worktree). The repo gets an exported
snapshot, sourced from the DB, when `.feature-workflow.toml` opts in.

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

Resolve `PROJECT` once: `PROJECT=$(basename "$(dirname "$(git rev-parse --git-common-dir)")")`.

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

## Step 4: Author context via the API

The context document lives in the webapp's DB, authored by logical key
`<PROJECT>/<FEATURE>/context/1`. All section content is HTML snippets
(no full-page skeleton — just `<p>`, `<ul>`, etc.).

Resolve PROJECT and FEATURE (both set by this point).

**1. Fetch the manifest** to confirm the section keys for this doc type:

```bash
curl -fsS http://127.0.0.1:8800/api/manifests/context
```

The manifest returns a list of sections with their keys. Use those keys
exactly — mismatched keys are rejected. Also read `presentation.stylesheet_url`
from the response and follow `~/.claude/skills/feature/contract-grounding.md`
to fetch the presentation contract and ground all emitted HTML against it.
Context docs use plain HTML tags (`<p>`, `<ul>`, `<dl>`) so grounding is
mostly structural awareness — no special class vocabulary needed.

**2. Create the feature** to register it as Available and record a
one-line note:

```bash
curl -fsS -X POST "http://127.0.0.1:8800/api/projects/$PROJECT/features/$FEATURE" \
  -H 'Content-Type: application/json' \
  -d '{"notes": "…one-line note about what this is…"}'
```

- **200**: feature created. Continue to step 3.
- **409** (already exists): fetch the current state and decide:

  ```bash
  curl -fsS "http://127.0.0.1:8800/api/projects/$PROJECT/features/$FEATURE"
  ```

  - `available` or `parked`: benign resumption — the feature exists
    but hasn't been started. Refresh the notes with the note verb
    and continue:

    ```bash
    curl -fsS -X POST \
      "http://127.0.0.1:8800/api/projects/$PROJECT/features/$FEATURE/note" \
      -H 'Content-Type: application/json' \
      -d '{"notes": "…updated note…"}'
    ```

  - `in_progress` or `done`: in a single-developer context this is
    the same person resuming work. Warn the user ("feature is already
    `<status>`") but continue — adding or refreshing the context doc
    is still valid.

  - Any other unexpected state: surface it to the user before
    proceeding. Don't silently overwrite contested state.

If the webapp is unreachable, skip this sub-step — the context doc
from step 3 is still written below.

**3. Assemble section content** by distilling the conversation:

- **problem-space**: why this might be worth doing, what's broken or
  missing, what conversations or observations triggered it.
- **related-work**: existing patterns or features in the codebase that
  connect to this; links to other context / requirements docs when
  relevant.
- **constraints**: what to watch for, dependencies, prior decisions that
  shape the space.
- **links**: design docs, customer reports, Slack threads, tickets,
  external references.
- **open-questions**: things worth resolving when requirements get
  written.

Omit any section that genuinely has nothing real to put in it — pass an
empty string or omit the key. Don't pad.

Primary source is the recent conversation. Distill — do not transcribe.
Context is not requirements: keep user stories, technical approaches,
phase breakdowns, and wishlist features out. Acknowledge unknowns — a
clear "open question" beats a half-formed guess.

**4. PUT the document**:

```bash
curl -fsS -X PUT \
  "http://127.0.0.1:8800/api/documents/$PROJECT/$FEATURE/context/1" \
  -H 'Content-Type: application/json' \
  -d '{
    "sections": {
      "problem-space": "<p>…</p>",
      "related-work": "<p>…</p>",
      "constraints": "<ul><li>…</li></ul>",
      "open-questions": "<ul><li>…</li></ul>"
    },
    "actor": "agent"
  }'
```

The response includes `{"document_id": N, "url": "/doc/N", ...}`.
Note the `document_id` — it's the doc's stable address in the webapp.

## Step 5: View in the webapp inbox

The context document is immediately in the DB and appears in the inbox
at `http://127.0.0.1:8800`. It is viewable at the `/doc/N` URL from
the PUT response.

## Step 6: Export and commit (if configured)

Check `.feature-workflow.toml` at the repo root.

**Export context** (if `[export].context = "markdown"`):

```bash
mkdir -p docs/features/$FEATURE
feature-html-to-md --webapp http://127.0.0.1:8800 \
    $PROJECT/$FEATURE/context/1 \
    docs/features/$FEATURE/context.md
```

**Export features tracker** (if `[export].features = "markdown"`):

```bash
feature-html-to-md --webapp http://127.0.0.1:8800 \
    --merge-features $PROJECT \
    features.md
```

If either export ran, stage and commit only the exported files, then push:

```bash
git add docs/features/$FEATURE/context.md features.md  # as applicable
git commit -m "docs: add $FEATURE context"
git push
```

If neither export ran (`.feature-workflow.toml` absent or both keys are `"none"`), skip.

## Step 7: Done

Tell the user the context is captured and viewable in the inbox at
`http://127.0.0.1:8800`. Mention the chosen FEATURE name and the
`/doc/N` URL from the PUT response. Tell them `/feature <FEATURE>`
will pick it up when they're ready to work on it. Then return to
whatever the conversation was doing before.
