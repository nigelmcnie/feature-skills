# Webapp polling convention

After writing a synthesis or feedback doc to the dev-store, use the webapp
HTTP API to receive responses rather than waiting for a clipboard paste.

## Protocol

1. **Force-walk** — trigger the walker so the doc is indexed immediately:
   ```bash
   curl -fsS -X POST http://127.0.0.1:8800/admin/discover >/dev/null 2>&1 || true
   ```

2. **Poll every 5 s**:
   ```bash
   curl -fsS "http://127.0.0.1:8800/synthesis-response?path=<ABS_PATH>"
   ```
   | Result | Action |
   |--------|--------|
   | `curl` error (server unreachable) | Fall back to clipboard |
   | `404` | Not yet indexed — sleep 5, retry |
   | `200 submitted=false` | Awaiting the human — sleep 5, retry |
   | `200 submitted=true` | Consume `responses` / `routine_flags` |

3. **Periodic status** — emit a brief "still waiting…" line roughly every
   60 seconds so the user knows the skill is live.

4. **Give-up / fallback** — if the user explicitly gives up (e.g. "let's
   just paste it") or the server is unreachable, fall back to the clipboard
   path: ask them to click **Copy responses** and paste the JSON blob.
   The `responses` / `routine_flags` shape is identical either way.
