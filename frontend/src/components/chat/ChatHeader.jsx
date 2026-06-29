import React from "react";

export default function ChatHeader({ citationCount, messageCount, selectedSession }) {
  return (
    <header className="chat-header">
      <div>
        <span>{selectedSession?.filename || "Legal document"}</span>
        <h1>{selectedSession?.title || "New legal Q&A session"}</h1>
      </div>
      <div className="chat-header-actions" aria-label="Session status">
        <span>{messageCount} messages</span>
        <strong>{citationCount} citations</strong>
      </div>
    </header>
  );
}
