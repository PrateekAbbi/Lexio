import React, { useState } from "react";
import EvidenceSourceModal from "./EvidenceSourceModal.jsx";
import PanelRail from "../ui/PanelRail.jsx";
import { sourcePercent } from "../../utils/formatters.js";

export default function DocumentEvidencePanel({ selectedSession, sources, collapsed, onToggleCollapsed }) {
  const [selectedSource, setSelectedSource] = useState(null);
  const topSources = sources.slice(0, 5);
  const pageCount = selectedSession?.page_count || selectedSession?.pages;
  const chunkCount = selectedSession?.chunk_count || selectedSession?.total_chunks;

  if (collapsed) {
    return (
      <PanelRail
        className="document-panel"
        label="Document preview"
        marker="PDF"
        direction=">"
        onExpand={onToggleCollapsed}
      />
    );
  }

  return (
    <aside className="document-panel" aria-label="Document preview">
      <div className="document-panel-header">
        <div>
          <span>Evidence Panel</span>
          <h2 title={selectedSession?.filename}>{selectedSession?.filename || "Legal document"}</h2>
        </div>
        <div className="panel-header-actions">
          <strong>PDF</strong>
          <button type="button" className="panel-toggle-button" onClick={onToggleCollapsed} aria-label="Minimize document preview">
            &lt;
          </button>
        </div>
      </div>

      <div className="document-facts">
        <div>
          <span>Pages</span>
          <strong>{pageCount || "--"}</strong>
        </div>
        <div>
          <span>Chunks</span>
          <strong>{chunkCount || "--"}</strong>
        </div>
      </div>

      <div className="pdf-page-preview">
        <div className="pdf-page-top">
          <span />
          <span />
          <span />
        </div>
        {topSources.length ? (
          topSources.slice(0, 3).map((source) => (
            <button type="button" className="pdf-snippet pdf-snippet-button" key={source.key} onClick={() => setSelectedSource(source)}>
              <strong>
                Page {source.page} - {sourcePercent(source)}
              </strong>
              <p>{source.text_snippet}</p>
            </button>
          ))
        ) : (
          <div className="pdf-placeholder">
            <span />
            <span />
            <span />
            <span />
            <p>Cited excerpts appear here after the first answer.</p>
          </div>
        )}
      </div>

      <div className="source-rail">
        <div className="source-rail-title">
          <h3>Evidence</h3>
          <span>{topSources.length ? `${topSources.length} matches` : "No matches yet"}</span>
        </div>
        {topSources.length ? (
          topSources.map((source) => (
            <button type="button" className="source-card source-card-button" key={source.key} onClick={() => setSelectedSource(source)}>
              <strong>Page {source.page}</strong>
              <span>{sourcePercent(source)} match</span>
            </button>
          ))
        ) : (
          <p className="muted">Ask a question to populate cited pages and source confidence.</p>
        )}
      </div>
      <EvidenceSourceModal source={selectedSource} onClose={() => setSelectedSource(null)} />
    </aside>
  );
}
