---
name: document-archive
description: "Archive or unarchive a single API-authored feature-workflow document (context/requirements/plan/etc.) via the webapp's API, instead of hand-editing the database. Use when a document is stale, superseded, a duplicate, or obsolete and needs to be retired — or when a previously archived document needs restoring. Trigger phrases: \"archive this document\", \"retire this doc\", \"this requirements doc is superseded/a duplicate/obsolete\", \"mark this document as archived\", \"this document's content moved to X, archive it\", \"unarchive this document\", \"restore this archived document\", or any request to remove/hide a document that isn't a whole feature (for whole-feature archival see the tracker's drop/archive verb instead)."
allowed-tools: Bash
---

# Document Archive / Unarchive

Individual feature-workflow documents (context, requirements, plan, or any
bespoke doc type) can be archived and unarchived over the webapp's API. This
is document-level — it retires one document, not a whole feature. Archiving
a document is reversible, requires a reason, and is discoverable: an archived
document still shows up (via `?status=archived`) and its doc-view page
explains why it was retired.

**Only API-authored documents** (no `source_path` — anything written through
the API rather than imported from a file on disk) can be archived this way.
A file-sourced document returns `409` — the file-walker resets its status
from the file on the next walk, so archiving it here wouldn't stick. Retire
those by moving/deleting the source file instead.

## Resolve the identity and the webapp helper

`FEATURE`, `DOC_TYPE`, and `INSTANCE` identify the document being archived —
take these from the conversation (the document just discussed), not from a
shell lookup. `PROJECT` and the helper resolve the usual way:

```bash
PROJECT=$(basename "$(dirname "$(git rev-parse --path-format=absolute --git-common-dir)")")
# BASE = this skill's base directory, shown at the top of the invocation.
WEBAPP="$(dirname "$(readlink -f "BASE")")/bin/webapp"
```

See `docs/webapp-helper.md` for the helper's full contract.

## Archive a document

```bash
printf '%s' '{"reason": "superseded", "superseded_by": "'"$PROJECT"'/'"$FEATURE"'/vision/1", "note": "content moved to the vision doc"}' \
  | "$WEBAPP" post "/api/documents/$PROJECT/$FEATURE/$DOC_TYPE/$INSTANCE/archive" -
```

- `reason` is **required**, one of `superseded` / `duplicate` / `obsolete`.
- `superseded` and `duplicate` each **require** `superseded_by`; `obsolete`
  may stand alone.
- `superseded_by` is free text — a document logical key
  (`project/feature/type/instance`), an MR link, or a decision reference.
  It's only resolved into a link at read time if it happens to match a real
  document; there's no validation against it existing.
- `note` is optional free text.
- Idempotent: archiving an already-archived document is a no-op
  (`changed: false`), returning its existing metadata unchanged. To correct
  a mistaken reason/pointer, unarchive first, then re-archive.

Responses: `200` (archived or already-archived), `400` (missing/unknown
reason, missing required `superseded_by`, or a self-referential pointer),
`404` (document not found), `409` (file-sourced, not archivable here).

## Unarchive a document

```bash
"$WEBAPP" post "/api/documents/$PROJECT/$FEATURE/$DOC_TYPE/$INSTANCE/unarchive" -
```

Body is optional. Idempotent: unarchiving an already-active document is a
no-op. Clears the reason/superseded_by/note/archived_at metadata.

## Enumerate archived documents

```bash
"$WEBAPP" get "/api/projects/$PROJECT/features/$FEATURE/documents?status=archived"
# or ?status=all for both active and archived
```

Each returned document carries `status`, and archived ones additionally
carry `reason` / `superseded_by` / `note` / `archived_at`.

## Full contract

`/openapi.json` is the authoritative, always-current schema for both verbs
(request/response shapes, all status codes) — fetch it if anything above is
unclear or the API has moved on since this was written:

```bash
"$WEBAPP" get /openapi.json
```
