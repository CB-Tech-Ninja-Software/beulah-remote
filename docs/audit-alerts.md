# Connection audit and alerts

## What the client already sends (read from `src/hbbs_http/sync.rs`)

The heartbeat (`POST {api-server}/api/heartbeat`, `sync.rs:245`) carries `id`, `uuid`, `ver`,
`modified_at`, and `conns` as a bare `Vec<i32>` of connection IDs (`sync.rs:240`). It has no peer
name or IP, and it only fires when an `api-server` is configured and is not public
(`heartbeat_url`). The per-connection records (`new` / authorized / `close`) go through
`Connection::post_conn_audit` (`src/server/connection.rs`), and are dropped when
`server_audit_conn` is empty, which is the normal case without a Pro API server.

So no local HTTP receiver is needed or added: the data lives in-process. I hooked
`post_conn_audit` with one line, which runs before the early return.

## What was built

`src/server/connection_audit.rs`:
- Appends one JSON line per event to `<log dir>/connections.log` (`Config::log_path()`).
  Fields: `time` (RFC 3339), `event` (`new` | `authorized` | `close`), `conn_id`, `ip`,
  `peer_id`, `peer_name`, `type`.
- On `authorized` (a peer actually logged in) on macOS, shows a system notification via
  `osascript display notification`. No new dependency. The `new` and `close` events are logged
  without an alert.

## Verify

1. Connect to this host from another RustDesk client.
2. A notification "Incoming remote connection: <name> (<id>) connected from <ip>" appears.
3. `tail ~/Library/Logs/<app>/connections.log` (or the `log` dir under the app's config) shows
   `new`, `authorized`, `close` lines.
4. `cargo test --lib connection_audit` runs the unit tests.

## Known limits
- Notification comes from `osascript`, so it is attributed to Script Editor and needs
  notification permission for it in System Settings.
- The log is append-only with no rotation.
