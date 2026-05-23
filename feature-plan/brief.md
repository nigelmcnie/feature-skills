# Planning Brief

## Purpose
You are drafting an implementation plan for a feature. The requirements
document has been approved. This brief guides the structure and detail
level of the plan.

## Structure
A good implementation plan contains:
- **Overview**: what we're building, in one paragraph
- **Key technical decisions**: choices that shape the implementation, with
  rationale. Include code snippets showing key interfaces.
- **File structure**: what files are created or modified
- **Phase breakdown**: for each delivery phase from the requirements:
  - What's built
  - Which files are touched
  - Key code snippets (interfaces, data structures, function signatures)
  - What tests are needed
  - What the MR chain looks like (each phase = one MR, invoked separately)
- **Checklist**: a flat checklist of all steps across all phases, at the
  bottom of the document. The implementing agent checks items off as it works.

## Detail level
The plan should be detailed enough that an implementing agent (which may be
a different, less capable model) can follow it without needing to make
significant design decisions. Include:
- Function signatures with type hints
- Schema changes
- Key conditional logic ("if X, then Y; otherwise Z")
- Test descriptions (what's tested, not full test code)

Do NOT include:
- Full implementation code (that's the implementing agent's job)
- Exact line numbers (files change)
- Style decisions (formatter handles them)

## What to read
Before drafting, read:
- The approved requirements document for this feature — including any
  **Indicative implementation notes** section at the bottom, which carries
  forward plan-level context that didn't belong in the requirements body
- `CLAUDE.md` — architecture, cross-cutting concerns, conventions
- All modules mentioned in the requirements' technical approach section
- Existing test files to understand testing patterns

## Quality control
The plan should reference `CLAUDE.md` for quality control steps rather than
hardcoding them. Instruct the implementing agent to follow whatever
`CLAUDE.md` says at implementation time.

## Phasing
- Each phase results in a separate MR
- Each phase is independently testable
- Each phase is implemented by a separate invocation of `/feature-implement`
- The implementing agent checks off items in this plan as it works
- The plan is a living document — it gets updated if the approach changes
  during implementation. If a deviation is significant, pause and get the
  human to review the revised plan before continuing.

## Checklist format

The flat checklist at the bottom **must** use phase headers so the implementing
agent can identify phase boundaries unambiguously. Example:

```markdown
## Checklist

### Phase 1: <name>
- [ ] Step A
- [ ] Step B

### Phase 2: <name>
- [ ] Step C
- [ ] Step D
```

Items within each phase should be ordered as they will be implemented.
