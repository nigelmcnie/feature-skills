# Feedback Synthesis Template

Shared format for the feedback synthesis documents produced by the feature
workflow:

- `requirements-feedback-N.md` (from `feature-requirements`)
- `review-feedback-N.md` (from `feature-review`)

The `feature-plan` and `feature-iterate` skills handle reviewer feedback
inline in chat rather than producing a synthesis document.

## Numbering

`N` is the round number. If no feedback file of this type exists in the
feature's directory yet, use `1`. If `*-feedback-1.md` exists, use `2`, and so on.

## Structure

Three sections — items live where their triage places them, with continuous
numbering across all sections:

````markdown
# <Feature> <Phase> — Feedback Synthesis #<N>

## Needs your input

### <N>. <Short, descriptive title>

<Detail paragraph(s) — what the issue is, where it occurs, why it matters.
Cite specific files, sections, or lines when relevant.>

**My take:** <Your assessment or recommendation. The specific question to
answer is provided by the calling skill.>

**Your thoughts:**

---

## Feedback

<Optional category — only use categories if there are >5 items in this
section or items naturally cluster, e.g. "Bugs", "Missing scope">

### <N+1>. <Title>

<Detail paragraph(s) when warranted.>

**My take:** <...>

**Your thoughts:**

---

## Routine

- **<N+2>.** <One-line description>. <One-line take.>
- **<N+3>.** <One-line description>. <One-line take.>
- ...
````

## Triage

When deciding which section an item belongs in:

- **Needs your input**: product/conceptual decisions, scope or phasing
  trade-offs, deferral decisions, naming for concepts, anything you're not
  confident about, anything where you might be making assumptions about dev
  velocity.
- **Routine**: only items you're highly confident are uncontroversial —
  factual citation/path fixes, naming mechanics (rename X to Y), wording
  polish, defensive-test additions, observability/logging granularity,
  schema minor specs.
- **Feedback** (the middle): everything else, in the reviewer's original
  order.

When in doubt, prefer **Feedback** over **Routine**. The cost of a Feedback
item that turns out to be uncontroversial is small; the cost of a
misclassified Routine item is larger.

## Guidance

- **Numbered titles**: descriptive enough that a reader grasps the issue at a glance.
- **Detail paragraph**: include when the title alone isn't self-evident. Skip when it is. Always skip in the Routine section.
- **My take**: focus on substance — what should be done, what the tradeoff is, why a finding doesn't apply. Length matches the complexity of the call. In the Routine section, keep it to one line.
- **Your thoughts**: always leave blank in the top and middle sections. The user fills it in. Do not add placeholder hints. The Routine section has no Your thoughts slot — the user pushes back in chat if needed.
- **Horizontal rule**: separate items in the top and middle sections with `---`. Routine items are a flat bullet list, no rules.
- **Categories**: only group items in the middle section when there are enough to benefit (rule of thumb: >5 items, or items naturally cluster). Don't force categories.
- **Item numbering**: number continuously across all three sections (1, 2, 3, ...), not restarting per section.
