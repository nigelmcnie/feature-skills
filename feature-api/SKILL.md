---
name: feature-api
description: "Points at the webapp's self-describing HTTP API for the feature workflow — load this whenever a session is reading or changing feature-workflow documents (context/requirements/plan/review), or the project/feature tracker. Not specific to any one operation: it's how an agent discovers what the API can do (read a document, list a feature's documents, claim/park/ship/archive/unarchive a feature, archive/unarchive a document, PUT document content, and anything else exposed) rather than needing a dedicated skill per verb. Trigger whenever a task touches a feature's docs or tracker state outside the guided /feature-* workflow commands."
allowed-tools: Bash
---

# feature-api

The webapp exposes its full HTTP API as a self-describing OpenAPI 3.1 spec at
`/openapi.json` — every route, method, request body, and response shape,
always current. That spec is the source of truth for what the API can do.
This skill is a **pointer to it**, not a mirror of it: it does not enumerate
or describe individual operations, and it is not the place to add one when a
new capability ships. Read the spec instead.

## Resolve the project and the webapp helper

```bash
PROJECT=$(basename "$(dirname "$(git rev-parse --path-format=absolute --git-common-dir)")")
# BASE = this skill's base directory, shown at the top of the invocation.
WEBAPP="$(dirname "$(readlink -f "BASE")")/bin/webapp"
```

Every skill in this repo talks to the webapp through this one bundled
helper — see `docs/webapp-helper.md` for its full contract (verbs, base URL,
long-polling). Never reach for raw `curl`: it's fragile against this API in
ways that specifically bite agents (shell-quoting, command-guard false
positives on `localhost`, lossy JSON rewriting).

## Discover what's possible

```bash
"$WEBAPP" get /openapi.json
```

Read the spec for the operation you need — its path, method, request body
shape, and response codes are all there. A couple of orienting examples
(illustrative only — not an exhaustive list):

```bash
# Fetch a document's content
"$WEBAPP" get /api/documents/$PROJECT/$FEATURE/plan/1

# List a feature's documents
"$WEBAPP" get /api/projects/$PROJECT/features/$FEATURE/documents
```

`$FEATURE`, `$DOC_TYPE`, and any other identity comes from the conversation
(the feature or document already being discussed), not from a shell lookup.

## Don't build a per-operation skill

If a capability isn't obvious from the spec, read more of it — don't write a
new skill that hand-documents one route. A per-operation skill goes stale the
moment the API changes; `/openapi.json` never does.
