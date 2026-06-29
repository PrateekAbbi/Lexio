import { api } from "../api.js";

async function readJsonResponse(response, fallbackMessage) {
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || fallbackMessage);
  return data;
}

// Keep endpoint details out of React components. Components should express
// product actions, while this module owns backend paths and request shapes.
export async function fetchSessions() {
  return readJsonResponse(await api("/sessions"), "Failed to load sessions.");
}

export async function fetchSessionMessages(sessionId) {
  return readJsonResponse(await api(`/sessions/${sessionId}/messages`), "Failed to load messages.");
}

export async function askSessionQuestion(sessionId, question) {
  return readJsonResponse(
    await api(`/sessions/${sessionId}/query`, {
      method: "POST",
      body: JSON.stringify({ question }),
    }),
    "Failed to send question.",
  );
}

export async function createSession(documentId) {
  return readJsonResponse(
    await api("/sessions", {
      method: "POST",
      body: JSON.stringify({ document_id: documentId }),
    }),
    "Failed to create session.",
  );
}

export async function uploadDocument(formData) {
  return readJsonResponse(
    await api("/upload", {
      method: "POST",
      body: formData,
    }),
    "Upload failed.",
  );
}
