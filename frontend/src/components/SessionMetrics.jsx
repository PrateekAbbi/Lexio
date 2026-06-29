import React from "react";
import PanelRail from "./ui/PanelRail.jsx";
import { formatMs, formatPercent, latencyStatus } from "../utils/formatters.js";
import { assistantMessages, topSourceMatch } from "../utils/messages.js";

export default function SessionMetrics({ messages, collapsed, onToggleCollapsed }) {
  const completed = assistantMessages(messages);
  const latest = completed[completed.length - 1] || null;
  const latestMatch = topSourceMatch(latest);
  const latestSourceCount = latest?.sources?.length || 0;
  const history = completed.slice(-5);
  const maxLatency = Math.max(1, ...history.map((message) => message.latency_ms || 0));
  const status = latencyStatus(latest?.latency_ms);

  if (collapsed) {
    return (
      <PanelRail className="session-metrics" label="Session metrics" marker="MET" direction="<" onExpand={onToggleCollapsed} />
    );
  }

  return (
    <aside className="session-metrics" aria-label="Session metrics">
      <div className="session-metrics-header">
        <div>
          <span>Metrics</span>
          <h2>Current session</h2>
        </div>
        <div className="panel-header-actions">
          <strong className={`latency-badge ${status}`}>{status === "neutral" ? "No data" : status}</strong>
          <button type="button" className="panel-toggle-button" onClick={onToggleCollapsed} aria-label="Minimize metrics panel">
            &gt;
          </button>
        </div>
      </div>

      <div className="session-metric-grid">
        <div className="session-metric-card">
          <span>Last Latency</span>
          <strong>{formatMs(latest?.latency_ms)}</strong>
        </div>
        <div className="session-metric-card">
          <span>Top Source Match</span>
          <strong>{formatPercent(latestMatch)}</strong>
        </div>
        <div className="session-metric-card">
          <span>Sources Used</span>
          <strong>{latestSourceCount || "--"}</strong>
        </div>
        <div className="session-metric-card">
          <span>Answers</span>
          <strong>{completed.length}</strong>
        </div>
      </div>

      <div className="session-chart">
        <div className="session-chart-title">
          <h3>Last 5 answers</h3>
          <span>latency</span>
        </div>
        <svg viewBox="0 0 280 116" role="img" aria-label="Last five answer latency chart">
          <line x1="14" y1="92" x2="266" y2="92" className="axis" />
          {history.map((message, index) => {
            const height = Math.max(8, ((message.latency_ms || 0) / maxLatency) * 72);
            const x = 24 + index * 50;
            const y = 92 - height;
            const barStatus = latencyStatus(message.latency_ms);
            return (
              <g key={message.id || `${message.created_at}-${index}`}>
                <rect x={x} y={y} width="30" height={height} rx="4" className={`bar ${barStatus}`} />
                <text x={x + 15} y="108" textAnchor="middle" className="bar-label">
                  {index + 1}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
    </aside>
  );
}
