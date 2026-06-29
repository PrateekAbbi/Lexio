export function assistantMessages(messages) {
  return messages.filter((message) => message.role === "assistant" && Number.isFinite(message.latency_ms));
}

export function collectSources(messages) {
  return messages
    .filter((message) => message.role === "assistant" && Array.isArray(message.sources))
    .flatMap((message, answerIndex) =>
      message.sources.map((source) => ({
        ...source,
        answerIndex: answerIndex + 1,
        key: `${message.id}-${source.page}-${source.chunk_index}`,
      })),
    )
    .sort((a, b) => (b.similarity_score || 0) - (a.similarity_score || 0));
}

export function topSourceMatch(message) {
  const sources = message?.sources || [];
  if (!sources.length) return null;
  return Math.max(...sources.map((source) => source.similarity_score || 0));
}
