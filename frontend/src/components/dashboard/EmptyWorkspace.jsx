import React from "react";

export default function EmptyWorkspace({ onUploadDocument }) {
  return (
    <div className="empty-state">
      <section className="empty-hero">
        <div className="empty-copy">
          <p className="eyebrow">Workspace ready</p>
          <h1>Start with a legal PDF and keep the evidence beside the answer.</h1>
          <p>Each session keeps the document, conversation, citations, and response metrics in one review surface.</p>
          <button type="button" className="primary-button" onClick={onUploadDocument}>
            Upload document
          </button>
        </div>
        <div className="empty-preview" aria-hidden="true">
          <div className="paper-stack back" />
          <div className="paper-stack front">
            <div className="paper-label">PDF</div>
            <span />
            <span />
            <span />
            <span className="short-line" />
            <div className="answer-card-mini">Cited answer</div>
          </div>
        </div>
      </section>
    </div>
  );
}
