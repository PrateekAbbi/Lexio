import React from "react";
import { messageCountLabel, relativeTime } from "../../utils/formatters.js";

export default function SessionList({ sessions, selectedSessionId, loading, onSelectSession }) {
  return (
    <div className="session-list">
      {loading ? <p className="muted">Loading sessions...</p> : null}
      {!loading && !sessions.length ? (
        <div className="sidebar-empty">
          <strong>No sessions yet</strong>
          <span>Upload your first PDF to create a review workspace.</span>
        </div>
      ) : null}
      {sessions.map((item) => (
        <button
          type="button"
          key={item.session_id}
          className={item.session_id === selectedSessionId ? "session-item active" : "session-item"}
          onClick={() => onSelectSession(item.session_id)}
        >
          <span className="session-filetype">PDF</span>
          <strong title={item.filename}>{item.filename}</strong>
          <span>{(item.title || "Untitled session").slice(0, 40)}</span>
          <small>
            {relativeTime(item.last_active_at)} - {messageCountLabel(item.message_count)}
          </small>
        </button>
      ))}
    </div>
  );
}
