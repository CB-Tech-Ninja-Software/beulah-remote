use hbb_common::{config::Config, log};
use serde_json::{json, Value};
use std::{fs::OpenOptions, io::Write, path::PathBuf};

pub fn audit_log_path() -> PathBuf {
    Config::log_path().join("connections.log")
}

fn format_record(conn_id: i32, ip: &str, v: &Value, now: &str) -> Option<(String, String)> {
    let (event, peer_id, peer_name, conn_type) = match v["action"].as_str() {
        Some("new") => ("new", "", "", Value::Null),
        Some("close") => ("close", "", "", Value::Null),
        Some(_) => return None,
        None => (
            "authorized",
            v["peer"][0].as_str().unwrap_or(""),
            v["peer"][1].as_str().unwrap_or(""),
            v["type"].clone(),
        ),
    };
    let line = json!({
        "time": now,
        "event": event,
        "conn_id": conn_id,
        "ip": ip,
        "peer_id": peer_id,
        "peer_name": peer_name,
        "type": conn_type,
    })
    .to_string();
    let alert = if event == "authorized" {
        format!("{} ({}) connected from {}", peer_name, peer_id, ip)
    } else {
        String::new()
    };
    Some((line, alert))
}

pub fn record(conn_id: i32, ip: &str, v: &Value) {
    let now = chrono::Local::now().to_rfc3339();
    let Some((line, alert)) = format_record(conn_id, ip, v, &now) else {
        return;
    };
    let path = audit_log_path();
    if let Some(dir) = path.parent() {
        let _ = std::fs::create_dir_all(dir);
    }
    match OpenOptions::new().create(true).append(true).open(&path) {
        Ok(mut f) => {
            if let Err(e) = writeln!(f, "{}", line) {
                log::warn!("write connection audit log failed: {}", e);
            }
        }
        Err(e) => log::warn!("open connection audit log failed: {}", e),
    }
    if !alert.is_empty() {
        notify(&alert);
    }
}

#[cfg(target_os = "macos")]
fn notify(body: &str) {
    let escaped = body.replace('\\', "\\\\").replace('"', "\\\"");
    let script = format!(
        "display notification \"{}\" with title \"Incoming remote connection\"",
        escaped
    );
    if let Err(e) = std::process::Command::new("osascript")
        .arg("-e")
        .arg(script)
        .spawn()
    {
        log::warn!("connection alert notification failed: {}", e);
    }
}

#[cfg(not(target_os = "macos"))]
fn notify(_body: &str) {}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn authorized_login_logs_peer_and_alerts() {
        let v = json!({"peer": ["123456", "Bob's Mac"], "type": 0});
        let (line, alert) = format_record(7, "10.0.0.5", &v, "T").unwrap();
        let p: Value = serde_json::from_str(&line).unwrap();
        assert_eq!(p["event"], "authorized");
        assert_eq!(p["peer_id"], "123456");
        assert_eq!(p["ip"], "10.0.0.5");
        assert_eq!(alert, "Bob's Mac (123456) connected from 10.0.0.5");
    }

    #[test]
    fn new_and_close_log_without_alert() {
        let (line, alert) = format_record(1, "1.2.3.4", &json!({"action": "new"}), "T").unwrap();
        assert!(line.contains("\"event\":\"new\"") && alert.is_empty());
        let (line, alert) = format_record(1, "1.2.3.4", &json!({"action": "close"}), "T").unwrap();
        assert!(line.contains("\"event\":\"close\"") && alert.is_empty());
        assert!(format_record(1, "", &json!({"action": "other"}), "T").is_none());
    }
}
