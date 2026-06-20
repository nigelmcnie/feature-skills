# Webapp polling convention

After writing a synthesis or feedback doc to the DB via the API, use the
webapp HTTP API to receive responses rather than waiting for a clipboard paste.

## Protocol (keyed API — current)

For docs authored via the logical-key API (`PUT /api/documents/...`):

1. **No force-walk needed** — docs authored via the API are immediately
   indexed in the DB. There is no need to POST to `/admin/discover`.

2. **Poll every 5 s** — use the document's logical key:
   ```bash
   curl -fsS "http://127.0.0.1:8800/api/documents/$PROJECT/$FEATURE/<doc_type>/$N/synthesis"
   ```
   | Result | Action |
   |--------|--------|
   | `curl` error (server unreachable) | Fall back to clipboard |
   | `404` | Doc not found — fall back to clipboard |
   | `200 submitted=false` | Awaiting the human — sleep 5, retry |
   | `200 submitted=true` | Consume `responses` / `routine_flags` |

3. **Periodic status** — emit a brief "still waiting…" line roughly every
   60 seconds so the user knows the skill is live.

4. **Give-up / fallback** — if the user explicitly gives up (e.g. "let's
   just paste it") or the server is unreachable, fall back to the clipboard
   path: ask them to click **Copy responses** and paste the JSON blob.
   The `responses` / `routine_flags` shape is identical either way.

## Legacy path-based polling (dev-store docs)

For docs written to the dev-store by older skills, the path-based endpoint
is still available. The path **must be fully absolute and tilde-expanded** —
the walker stores `source_path` expanded, so a literal `~` never matches
and 404s forever. Use `$HOME`, which expands inside the quoted URL:

1. **Force-walk** — trigger the walker so the doc is indexed immediately:
   ```bash
   curl -fsS -X POST http://127.0.0.1:8800/admin/discover >/dev/null 2>&1 || true
   ```

2. **Poll every 5 s**:
   ```bash
   curl -fsS "http://127.0.0.1:8800/synthesis-response?path=$HOME/.claude/feature-docs/<PROJECT>/<FEATURE>/<doc>.html"
   ```
   | Result | Action |
   |--------|--------|
   | `curl` error (server unreachable) | Fall back to clipboard |
   | `404` | Not yet indexed — sleep 5, retry |
   | `200 submitted=false` | Awaiting the human — sleep 5, retry |
   | `200 submitted=true` | Consume `responses` / `routine_flags` |

New features use API-authored docs and the keyed protocol above.
