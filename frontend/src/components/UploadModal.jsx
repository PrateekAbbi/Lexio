import React, { useRef, useState } from "react";
import { isAuthSessionExpiredError } from "../api.js";
import { useUploadProgress } from "../hooks/useUploadProgress.js";
import { createSession, uploadDocument } from "../services/sessions.js";
import { normalizeUploadedDocument, validatePdfFile } from "../utils/documents.js";
import { stripPdfExtension } from "../utils/formatters.js";

export default function UploadModal({ onClose, onSessionCreated }) {
  const inputRef = useRef(null);
  const [step, setStep] = useState(1);
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadedDoc, setUploadedDoc] = useState(null);
  const [sessionName, setSessionName] = useState("");
  const [error, setError] = useState("");
  const uploadProgress = useUploadProgress();

  async function uploadFile(file) {
    const validationError = validatePdfFile(file);
    if (validationError) {
      setError(validationError);
      return;
    }

    const formData = new FormData();
    formData.append("file", file);
    setUploading(true);
    uploadProgress.start();
    setError("");

    try {
      const doc = normalizeUploadedDocument(await uploadDocument(formData), file.name);
      setUploadedDoc(doc);
      setSessionName(stripPdfExtension(doc.filename));
      uploadProgress.complete();
      setStep(2);
    } catch (err) {
      if (isAuthSessionExpiredError(err)) return;
      setError(err.message || "Upload failed.");
      uploadProgress.reset();
    } finally {
      uploadProgress.stop();
      setUploading(false);
    }
  }

  async function startSession() {
    if (!uploadedDoc?.doc_id) return;
    setError("");
    try {
      const data = await createSession(uploadedDoc.doc_id);
      onSessionCreated({
        session_id: data.session_id,
        title: sessionName || null,
        filename: uploadedDoc.filename,
        last_active_at: new Date().toISOString(),
        message_count: 0,
      });
    } catch (err) {
      if (isAuthSessionExpiredError(err)) return;
      setError(err.message || "Failed to create session.");
    }
  }

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true">
      <section className="upload-modal">
        <div className="modal-header">
          <div>
            <span>New Session</span>
            <h2>{step === 1 ? "Upload a PDF" : "Start chat session"}</h2>
          </div>
          <button type="button" className="close-button" onClick={onClose}>
            Close
          </button>
        </div>

        {step === 1 ? (
          <>
            <button
              type="button"
              className={isDragging ? "modal-dropzone dragging" : "modal-dropzone"}
              onClick={() => inputRef.current?.click()}
              onDragEnter={(event) => {
                event.preventDefault();
                setIsDragging(true);
              }}
              onDragOver={(event) => event.preventDefault()}
              onDragLeave={() => setIsDragging(false)}
              onDrop={(event) => {
                event.preventDefault();
                setIsDragging(false);
                uploadFile(event.dataTransfer.files?.[0]);
              }}
              disabled={uploading}
            >
              <span className="upload-glyph">PDF</span>
              <strong>{uploading ? "Uploading and embedding..." : "Drop PDF here"}</strong>
              <small>or click to browse</small>
            </button>
            <input ref={inputRef} type="file" accept=".pdf,application/pdf" onChange={(event) => uploadFile(event.target.files?.[0])} hidden />
            <div className="progress-track">
              <div className="progress-bar" style={{ width: `${uploadProgress.progress}%` }} />
            </div>
          </>
        ) : (
          <div className="session-start">
            <div className="doc-metadata">
              <div>
                <span>Filename</span>
                <strong>{uploadedDoc.filename}</strong>
              </div>
              <div>
                <span>Pages</span>
                <strong>{uploadedDoc.page_count || uploadedDoc.pages}</strong>
              </div>
              <div>
                <span>Chunks</span>
                <strong>{uploadedDoc.total_chunks}</strong>
              </div>
              <div>
                <span>Ingest</span>
                <strong>{uploadedDoc.ingest_time_ms} ms</strong>
              </div>
            </div>
            <label className="field-label">
              Session name
              <input value={sessionName} onChange={(event) => setSessionName(event.target.value)} />
            </label>
            <button type="button" className="primary-button" onClick={startSession}>
              Start Session
            </button>
          </div>
        )}

        {error ? <p className="error-text">{error}</p> : null}
      </section>
    </div>
  );
}
