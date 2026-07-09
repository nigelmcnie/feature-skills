---
name: feature-ship
description: Re-verify a feature's merged implementation on main and mark it shipped (Done) in the tracker. Use after all phase MRs — and any iterate MR — have merged and review has already happened; this is the lightweight tail that re-verifies the merged state and flips the tracker, without re-reviewing the code. feature-review delegates here for the actual ship; the post-iterate path invokes it directly once the iterate MR merges.
disable-model-invocation: true
allowed-tools: Read, Grep, Glob, Bash
argument-hint: "[feature-name]"
---

# Ship Workflow

Mark a feature **Done** once its implementation — and any iteration —
has landed on main. This is the lightweight tail of the workflow. It
does **not** re-review the code: review/iterate already did that. It
re-verifies the *merged* state empirically and flips the tracker.

It exists so "ship" is one shared step with two callers, rather than
logic duplicated across skills:

- **`feature-review` Step 10**, inline, when a review was fully clean
  (no iteration): review has already done get-on-main / verify-phases /
  QC, so it jumps straight to **Step 4 (Mark shipped)** below and skips
  Steps 1–3.
- **A developer (or `feature-iterate`'s wrap-up) after an iterate MR
  merges**: run `/feature-ship <feature>` on main for the full
  verify-then-ship. This is the cheap re-entry that replaces re-running
  the whole of `/feature-review` just to ship — the review already
  happened; only the merged state needs re-checking.

## Model check

Check your system context for the model you are running on. If your model name does not contain "opus", warn the user:

> ⚠️ This skill expects Claude Opus. You appear to be on [model name]. Opus is recommended here. Continue anyway?

Wait for their response. If they say no, stop here.

## Step 1: Get on main and pull

```bash
git checkout main
git pull
```

Tell the user you've switched to main and pulled.

## Step 2: Resolve names and confirm the work has landed

Resolve `PROJECT`: `PROJECT=$(basename "$(dirname "$(git rev-parse --path-format=absolute --git-common-dir)")")`
(`--path-format=absolute` matters: from the main checkout `--git-common-dir`
returns the relative `.git`, so without it `PROJECT` resolves to `.`).
Take `FEATURE` from `$ARGUMENTS`; if absent, ask (we're on main, so the
branch name can't be used to infer it).

Confirm the feature's phase branches — and any iterate branch — actually
merged to main, the same lookup `feature-review` Step 3 uses:

```bash
git log --merges main --grep "<FEATURE>-p"        # phase MRs
git log --merges main --grep "<FEATURE>-iterate"  # iterate MRs (if any)
```

Squash/rebase fallback: `git log main --oneline | grep -i "<FEATURE>"`,
or the platform (`glab mr list --source-branch features/<FEATURE>-p<N> --state merged`
/ `gh pr list --search "head:features/<FEATURE>-p<N>" --state closed`).

If nothing for this feature appears merged, **stop and tell the user** —
there's nothing on main to ship. If a phase still looks unmerged, say so;
don't ship a partially-landed feature.

## Step 3: Re-verify the merged state

Re-run the project's QC gate against main — the empirical catch that the
merge (and any parallel work) didn't break the merged result. Invoke
`feature-qa` inline: **do NOT use the Skill tool** (it sets
`disable-model-invocation: true`); read `~/.claude/skills/feature-qa/SKILL.md`
and run the commands it discovers from `CLAUDE.md`. All must pass.

If any check fails, **stop and tell the user** — do not ship a red main.
A failure here is no longer a ship: it's an iterate (read
`~/.claude/skills/feature-iterate/SKILL.md` and address it), then ship.

## Step 4: Mark shipped

(`feature-review` enters here directly when its review was clean — it has
already done Steps 1–3.)

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
mkdir -p ~/.claude/feature-docs/$PROJECT/$FEATURE/.feedback-archive
mv ~/.claude/feature-docs/$PROJECT/$FEATURE/review-feedback-*.html \
   ~/.claude/feature-docs/$PROJECT/$FEATURE/.feedback-archive/ 2>/dev/null || true
```

### Refresh the committed tracker snapshot

The ship API flips the feature to Done in the webapp DB, but the repo's
committed `features.md` snapshot only reflects that once it's re-exported.
Don't rely on a parallel feature's export happening to propagate it — a
quiet solo repo would leave Done never reaching the committed tracker.
Re-export and commit here, but **only** when `.feature-workflow.toml` at
the repo root has `[export].features = "markdown"` (skip this whole
sub-step otherwise):

```bash
feature-html-to-md --webapp http://127.0.0.1:8800 \
    --merge-features $PROJECT \
    features.md
```

Then commit **only** `features.md`, and only if it actually changed. A
sibling feature's export may already have propagated this feature's Done
status (the render is whole-tracker), in which case there's nothing to
commit — skip silently. Scope the commit with an explicit pathspec: a
shared working tree may carry a concurrent agent's unrelated staged work,
and a bare `git commit` would sweep it in.

```bash
if git diff --quiet -- features.md && git diff --cached --quiet -- features.md; then
  echo "tracker already current — nothing to commit"
else
  git add features.md
  git commit -m "docs: mark $FEATURE shipped in tracker" -- features.md
  git push
fi
```

Tell the user the feature is marked shipped.
