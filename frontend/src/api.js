import { supabase } from "./supabaseClient";

const API_BASE_URL = normalizeApiBaseUrl(import.meta.env.VITE_API_BASE_URL);

function normalizeApiBaseUrl(value) {
  const fallback = "/api";
  if (!value) return fallback;
  return value.replace(/\/+$/, "");
}

export class AuthSessionExpiredError extends Error {
  constructor() {
    super("Supabase session expired.");
    this.name = "AuthSessionExpiredError";
  }
}

export function isAuthSessionExpiredError(error) {
  return error?.name === "AuthSessionExpiredError";
}

let handlingExpiredSession = false;

async function expireFrontendSession() {
  if (!handlingExpiredSession) {
    handlingExpiredSession = true;
    window.dispatchEvent(new CustomEvent("lexio:auth-expired"));
    await supabase.auth.signOut();
    if (window.location.pathname !== "/login") {
      window.location.replace("/login");
    }
  }
  throw new AuthSessionExpiredError();
}

async function requestWithToken(path, options, token) {
  const headers = new Headers(options.headers || {});

  if (!(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  return fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });
}

export async function api(path, options = {}) {
  // Supabase access tokens are short-lived. Always read the latest session
  // immediately before a request instead of caching a token in React state.
  const {
    data: { session },
  } = await supabase.auth.getSession();

  const response = await requestWithToken(path, options, session?.access_token);
  if (response.status !== 401) {
    return response;
  }

  // A 401 can be a token-refresh race, not a real logout. Retry once with a
  // freshly refreshed session before treating the user as signed out.
  const {
    data: { session: refreshedSession },
    error,
  } = await supabase.auth.refreshSession();

  if (error || !refreshedSession?.access_token) {
    await expireFrontendSession();
  }

  const retryResponse = await requestWithToken(path, options, refreshedSession.access_token);
  if (retryResponse.status === 401) {
    await expireFrontendSession();
  }

  return retryResponse;
}
