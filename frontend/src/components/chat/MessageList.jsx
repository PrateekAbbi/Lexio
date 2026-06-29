import React from "react";
import FormattedMessage from "./FormattedMessage.jsx";
import { sourcePercent } from "../../utils/formatters.js";

export default function MessageList({
  bottomRef,
  error,
  expandedSources,
  loading,
  loadingMessages,
  messages,
  onToggleSources,
}) {
  return (
    <div className="message-list">
      {loadingMessages ? <p className="muted">Loading conversation...</p> : null}
      {messages.map((message) => {
        const isAssistant = message.role === "assistant";
        const sources = message.sources || [];
        const expanded = expandedSources.has(message.id);
        return (
          <article key={message.id} className={isAssistant ? "message assistant" : "message user"}>
            <div className="message-bubble">
              <p>{isAssistant ? <FormattedMessage text={message.content} /> : message.content}</p>
              {isAssistant && message.latency_ms ? <small>{message.latency_ms} ms</small> : null}
            </div>
            {isAssistant && sources.length ? (
              <div className="message-sources">
                <button type="button" onClick={() => onToggleSources(message.id)}>
                  Sources ({sources.length})
                </button>
                {expanded ? (
                  <div className="compact-sources">
                    {sources.map((source, index) => (
                      <div className="compact-source" key={`${source.page}-${source.chunk_index}-${index}`}>
                        <strong>
                          Page {source.page} - {sourcePercent(source)} match
                        </strong>
                        <span>{source.text_snippet}</span>
                      </div>
                    ))}
                  </div>
                ) : null}
              </div>
            ) : null}
          </article>
        );
      })}
      {loading ? (
        <article className="message assistant">
          <div className="message-bubble typing-bubble">
            <span />
            <span />
            <span />
          </div>
        </article>
      ) : null}
      {error ? <p className="error-text">{error}</p> : null}
      <div ref={bottomRef} />
    </div>
  );
}
