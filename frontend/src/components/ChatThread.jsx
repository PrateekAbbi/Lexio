import React, { useEffect, useMemo, useRef, useState } from "react";
import ChatComposer from "./chat/ChatComposer.jsx";
import ChatHeader from "./chat/ChatHeader.jsx";
import DocumentEvidencePanel from "./chat/DocumentEvidencePanel.jsx";
import MessageList from "./chat/MessageList.jsx";
import SessionMetrics from "./SessionMetrics.jsx";
import PanelResizer from "./ui/PanelResizer.jsx";
import { useResizablePanel } from "../hooks/useResizablePanel.js";
import { useSessionChat } from "../hooks/useSessionChat.js";
import { collectSources } from "../utils/messages.js";

export default function ChatThread({ isMobile, sessionId, selectedSession, onSessionUpdated, workspacePrefs }) {
  const chat = useSessionChat(sessionId, { onSessionUpdated });
  const documentPanel = useResizablePanel(340, { min: 280, max: 480 });
  const metricsPanel = useResizablePanel(318, { min: 270, max: 420, direction: -1 });
  const [documentCollapsed, setDocumentCollapsed] = useState(false);
  const [metricsCollapsed, setMetricsCollapsed] = useState(false);
  const bottomRef = useRef(null);
  const textareaRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [chat.messages, chat.loading]);

  function autoGrow(event) {
    const el = event.target;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 150)}px`;
  }

  function handleKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submitQuestion();
    }
  }

  async function submitQuestion() {
    if (!chat.question.trim() || chat.loading) return;
    if (textareaRef.current) textareaRef.current.style.height = "48px";
    await chat.sendQuestion();
  }

  const documentSources = useMemo(() => collectSources(chat.messages), [chat.messages]);
  const showDocumentPreview = workspacePrefs?.documentPreview !== false;
  const showMetrics = workspacePrefs?.metrics !== false;
  const chatGridColumns = useMemo(() => {
    const columns = [];
    if (showDocumentPreview) {
      columns.push(`${documentCollapsed ? 54 : documentPanel.width}px`);
      if (!documentCollapsed) columns.push("10px");
    }
    columns.push("minmax(360px, 1fr)");
    if (showMetrics) {
      if (!metricsCollapsed) columns.push("10px");
      columns.push(`${metricsCollapsed ? 54 : metricsPanel.width}px`);
    }
    return columns.join(" ");
  }, [documentCollapsed, documentPanel.width, metricsCollapsed, metricsPanel.width, showDocumentPreview, showMetrics]);
  const chatBodyStyle = isMobile ? undefined : { gridTemplateColumns: chatGridColumns };

  return (
    <section className="chat-shell">
      <ChatHeader selectedSession={selectedSession} messageCount={chat.messages.length} citationCount={documentSources.length} />

      <div className="chat-body" style={chatBodyStyle}>
        {showDocumentPreview ? (
          <>
            <DocumentEvidencePanel
              selectedSession={selectedSession}
              sources={documentSources}
              collapsed={documentCollapsed}
              onToggleCollapsed={() => setDocumentCollapsed((current) => !current)}
            />
            {!documentCollapsed ? (
              <PanelResizer
                className="workspace-resizer"
                label="Resize document preview"
                onResizeStart={documentPanel.startResize}
              />
            ) : null}
          </>
        ) : null}
        <MessageList
          bottomRef={bottomRef}
          error={chat.error}
          expandedSources={chat.expandedSources}
          loading={chat.loading}
          loadingMessages={chat.loadingMessages}
          messages={chat.messages}
          onToggleSources={chat.toggleSources}
        />
        {showMetrics ? (
          <>
            {!metricsCollapsed ? (
              <PanelResizer className="workspace-resizer" label="Resize metrics panel" onResizeStart={metricsPanel.startResize} />
            ) : null}
            <SessionMetrics messages={chat.messages} collapsed={metricsCollapsed} onToggleCollapsed={() => setMetricsCollapsed((current) => !current)} />
          </>
        ) : null}
      </div>

      <ChatComposer
        disabled={chat.loading || !chat.question.trim()}
        onChange={(event) => {
          chat.setQuestion(event.target.value);
          autoGrow(event);
        }}
        onKeyDown={handleKeyDown}
        onSubmit={submitQuestion}
        textareaRef={textareaRef}
        value={chat.question}
      />
    </section>
  );
}
