import React, { useState } from "react";
import { supabase } from "../supabaseClient.js";

export default function Login() {
  const [error, setError] = useState("");

  async function signInWithGoogle() {
    setError("");
    const { error: signInError } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: `${window.location.origin}/dashboard` },
    });
    if (signInError) {
      setError(signInError.message);
    }
  }

  return (
    <main className="login-screen">
      <section className="login-hero" aria-label="Lexio sign in">
        <div className="login-story">
          <div className="brand-lockup">
            <div className="brand-mark">LX</div>
            <span>Lexio</span>
          </div>
          <div>
            <p className="eyebrow">Legal document intelligence</p>
            <h1>Read contracts with context, citations, and confidence.</h1>
            <p className="login-copy">
              Upload a PDF, ask direct questions, and inspect the evidence behind every answer in a focused review workspace.
            </p>
          </div>
          <div className="login-signal-grid" aria-label="Platform highlights">
            <div>
              <strong>5</strong>
              <span>source matches</span>
            </div>
            <div>
              <strong>PDF</strong>
              <span>native workflow</span>
            </div>
            <div>
              <strong>ms</strong>
              <span>latency tracked</span>
            </div>
          </div>
        </div>

        <div className="login-card">
          <div className="login-preview" aria-hidden="true">
            <div className="preview-toolbar">
              <span />
              <span />
              <span />
            </div>
            <div className="preview-doc">
              <div className="preview-doc-header">
                <small>COMMERCIAL_LEASE.PDF</small>
                <b>What happens if I break the lease?</b>
              </div>
              <div className="preview-answer-lines">
                <span />
                <span />
                <span />
                <span />
              </div>
              <div className="preview-citation">Page 3 - 44% match</div>
            </div>
          </div>

          <div className="login-form">
            <div className="login-mark">LX</div>
            <h2>Welcome back</h2>
            <p>Sign in to continue your document review.</p>
            <button type="button" className="google-button" onClick={signInWithGoogle}>
              <span className="google-dot">G</span>
              Sign in with Google
            </button>
            {error ? <p className="error-text">{error}</p> : null}
          </div>
        </div>
      </section>
    </main>
  );
}
