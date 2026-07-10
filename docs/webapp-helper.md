# The `webapp` helper

Every feature skill talks to the webapp through one bundled helper,
`bin/webapp`, instead of raw `curl`. It ships in this repo, so it is present
wherever the skills are, and it depends only on the Python 3 standard library —
no `curl`, no `jq`, nothing installed, nothing about any one machine's setup.

## Why it exists

Raw `curl` to the webapp is fragile in ways that bite agents:

- shell-quoting quirks around URLs and JSON bodies,
- command guards that false-positive on quoted `localhost` URLs,
- output filters that lossily rewrite JSON responses.

`webapp` sidesteps all of these — it is plain `urllib` against the API — and it
centralises the base URL so no skill hard-codes it.

## Base URL

Defaults to `http://127.0.0.1:8800`. The webapp is expected on localhost —
directly, or via an SSH tunnel from wherever you're working. To point somewhere
else, set `FEATURE_WEBAPP_URL`; nothing else changes.

## Resolving the helper

The helper lives at `bin/webapp` in this repo, one level up from each skill's
own directory. Resolve it once at the start of any skill that calls the webapp,
substituting the skill's base directory (shown at the top of every skill
invocation) for `BASE`:

```bash
WEBAPP="$(dirname "$(readlink -f "BASE")")/bin/webapp"   # BASE = this skill's base directory
```

`readlink -f` resolves the skill directory to its real location in the repo
(the skills are commonly symlinked into `~/.claude/skills/`), so `dirname` lands
on the repo root and `bin/webapp` is found regardless of how the skills were
installed. The file is executable, so `"$WEBAPP" …` runs it directly.

## Verbs

```bash
"$WEBAPP" get  <path>                 # GET; prints the response body
"$WEBAPP" put  <path> <file>          # PUT a JSON body from <file> (or "-" / omitted = stdin)
"$WEBAPP" post <path> <file>          # POST a JSON body from <file> (or "-" / omitted = stdin)
"$WEBAPP" wait <path> [--deadline N]  # long-poll until submitted=true or N seconds (default 1800)
```

`<path>` is everything after the base URL, e.g.
`/api/documents/$PROJECT/$FEATURE/plan/1` (a leading slash is optional; query
strings like `?dry_run=true` are fine).

The response body is printed verbatim to stdout — pipe it into `python3` to
parse JSON. A non-2xx status prints `<status> <body>` to stderr and exits 1
(like `curl -f`); a transport failure prints the error and exits 1.

## Examples

```bash
# Read a document (parse the JSON however you like)
"$WEBAPP" get /api/documents/$PROJECT/$FEATURE/requirements/1

# Validate section keys without persisting
printf '%s' "$SECTIONS_JSON" > /tmp/body.json
"$WEBAPP" put "/api/documents/$PROJECT/$FEATURE/requirements/1?dry_run=true" /tmp/body.json

# Write a document (body assembled into a file first — keeps JSON escaping sane)
"$WEBAPP" put /api/documents/$PROJECT/$FEATURE/requirements/1 /tmp/body.json

# Fire-and-forget POST (best-effort; ignore failure)
"$WEBAPP" post /api/projects/$PROJECT/features/$FEATURE/claim /tmp/owner.json || true

# Fetch and integrate click-to-comments
"$WEBAPP" get /api/documents/$PROJECT/$FEATURE/plan/1/comments
printf '{"ids": [1,2]}' | "$WEBAPP" post /api/documents/$PROJECT/$FEATURE/plan/1/comments/integrate -
```

## Waiting on a human (long-poll)

`wait` replaces the hand-rolled reconnect schedule. It re-issues the long-poll
across the server's short holds internally and returns only once the human
submits (`submitted=true`) or the deadline elapses — so an arbitrarily long
wait costs **one** invocation, not one turn per server timeout. Run it in the
background and you're notified on completion:

```bash
"$WEBAPP" wait /api/documents/$PROJECT/$FEATURE/requirements-feedback/$N/synthesis/wait --deadline 1800
```

On return, parse the body: `submitted=true` carries the `responses` /
`routine_flags`; `submitted=false` means the deadline elapsed with no
submission — reconnect (another `wait`) or hand back to the developer.
