import { useCallback, useEffect, useState } from "react";
import { isAuthSessionExpiredError } from "../api.js";
import { askSessionQuestion, fetchSessionMessages } from "../services/sessions.js";

function optimisticUserMessage(content) {
  return {
    id: `local-user-${Date.now()}`,
    role: "user",
    content,
    sources: null,
    latency_ms: null,
    created_at: new Date().toISOString(),
  };
}

function assistantMessageFromAnswer(data) {
  return {
    id: `local-assistant-${Date.now()}`,
    role: "assistant",
    content: data.answer,
    sources: data.sources,
    latency_ms: data.latency_ms,
    created_at: new Date().toISOString(),
  };
}

export function useSessionChat(sessionId, { onSessionUpdated } = {}) {
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadingMessages, setLoadingMessages] = useState(true);
  const [error, setError] = useState("");
  const [expandedSources, setExpandedSources] = useState(new Set());

  const loadMessages = useCallback(async () => {
    setLoadingMessages(true);
    setError("");
    try {
      setMessages(await fetchSessionMessages(sessionId));
    } catch (err) {
      if (isAuthSessionExpiredError(err)) return;
      setError(err.message || "Failed to load messages.");
    } finally {
      setLoadingMessages(false);
    }
  }, [sessionId]);

  useEffect(() => {
    loadMessages();
  }, [loadMessages]);

  async function sendQuestion() {
    const cleanQuestion = question.trim();
    if (!cleanQuestion || loading) return false;

    // Keep the chat feeling instantaneous while the backend performs retrieval
    // and answer generation. The persisted messages are loaded on session entry.
    setMessages((current) => [...current, optimisticUserMessage(cleanQuestion)]);
    setQuestion("");
    setLoading(true);
    setError("");

    try {
      const data = await askSessionQuestion(sessionId, cleanQuestion);
      setMessages((current) => [...current, assistantMessageFromAnswer(data)]);
      onSessionUpdated?.();
      return true;
    } catch (err) {
      if (isAuthSessionExpiredError(err)) return false;
      setError(err.message || "Failed to send question.");
      return false;
    } finally {
      setLoading(false);
    }
  }

  function toggleSources(messageId) {
    setExpandedSources((current) => {
      const next = new Set(current);
      if (next.has(messageId)) next.delete(messageId);
      else next.add(messageId);
      return next;
    });
  }

  return {
    error,
    expandedSources,
    loading,
    loadingMessages,
    messages,
    question,
    sendQuestion,
    setQuestion,
    toggleSources,
  };
}
