# Contract grounding

Follow these steps whenever you write HTML for a content document.

Webapp calls below use the bundled `webapp` helper (`"$WEBAPP" get …`); the
calling skill resolves `$WEBAPP` once at its start — see `docs/webapp-helper.md`.

## 1. Fetch the presentation contract

The manifest response for any content doc type carries a `presentation` block:

```bash
"$WEBAPP" get /api/manifests/<doc_type>
```

The `presentation.stylesheet_url` field points to the contract stylesheet (typically
`/static/doc.css`). Fetch it:

```bash
"$WEBAPP" get /static/doc.css
```

If the manifest carries no `presentation` block, proceed using section keys and your
judgement — grounding is best-effort when the pointer is absent.

If the pointer is present but the fetch fails, warn the user:

> ⚠️ Couldn't fetch the presentation contract; proceeding best-effort.

Then continue without blocking.

## 2. Ground emitted HTML against the contract

The stylesheet includes teaching comments that describe each class's purpose and expected
structure. Read those comments to understand the vocabulary before writing any HTML.

Every `class` attribute you emit must be defined as a selector in the fetched CSS.
If a class you're considering is not present in the stylesheet, it is out of contract —
use the nearest in-contract alternative instead.

**No section-level `<h2>`.**  The webapp template supplies each section's `<h2>` heading
from the section label. Section body HTML must start at `<h3>` or lower. Emitting an
`<h2>` in a section body would duplicate the webapp-rendered heading.

## 3. Using `extra_css` — only when nothing fits

The `extra_css` field on a document write is a safety valve, not a shortcut.

Use it only when the content genuinely requires presentation vocabulary that the contract
does not cover and that cannot reasonably be expressed through the contract's existing
classes plus plain HTML elements (`<table>`, `<blockquote>`, `<dl>`, etc.).

**Counter-example — do not reach for `extra_css`:**

> "I need a highlighted warning box."

The contract already has `<blockquote>` (accent-bordered callout) and `.questions`
(surface-bordered block). Either fits the intent. Introducing `.warning-box` via
`extra_css` is unnecessary — it duplicates in-contract vocabulary.

When you do introduce a genuine gap via `extra_css`, record it in the feature's design
notes or retro so the webapp stylesheet can absorb it in a future iteration.

## 4. Verify with the lint gate

After a PUT succeeds, run `doc-contract-lint` against the just-written document:

```bash
doc-contract-lint --webapp http://127.0.0.1:8800 <project>/<feature>/<doc_type>/<N>
```

A clean exit (code 0) confirms the emitted HTML is fully grounded. If the lint reports
violations, resolve them before completing the authoring step — fix the class names in
the section bodies and re-PUT, then re-run the lint.

For opaque documents (synthesis / feedback forms) that legitimately keep a residual
`<style>` for interactive-form chrome the contract has no vocabulary for, add
`--allow-h2`. In that mode the lint allows `<h2>` headings and accepts any class defined
in the document's own `<style>` block — so the form chrome passes — while a genuinely
ungrounded class (one styled neither by the contract nor the doc's own `<style>`) still
fails. So a correctly-converged opaque doc exits 0; a typo or stray class still trips it.
