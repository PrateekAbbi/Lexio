import React, { useState } from "react";
import { initialsFromEmail } from "../../utils/formatters.js";
import SessionList from "./SessionList.jsx";
import WorkspaceSettingsMenu from "./WorkspaceSettingsMenu.jsx";

export default function DashboardSidebar({
  activeSessions,
  displayName,
  email,
  error,
  isMobile,
  isOpen,
  loadingSessions,
  onClose,
  onCreateSession,
  onSelectSession,
  onSignOut,
  onWorkspacePreferenceChange,
  selectedSessionId,
  sessions,
  workspacePreferences,
}) {
  const [settingsOpen, setSettingsOpen] = useState(false);
  const workspaceState = sessions.some((item) => item.session_id === selectedSessionId) ? "open" : "ready";

  return (
    <aside className={isOpen ? "sidebar mobile-open" : "sidebar"}>
      <div className="sidebar-top">
        <div className="app-brand">
          <div className="brand-mark">LX</div>
          <div>
            <strong>Lexio</strong>
            <span>Legal research desk</span>
          </div>
        </div>
        {isMobile ? (
          <button type="button" className="sidebar-close-button" onClick={onClose} aria-label="Close navigation">
            ×
          </button>
        ) : null}

        <button type="button" className="new-session-button" onClick={onCreateSession}>
          <span>+</span>
          New Session
        </button>

        <div className="sidebar-stats" aria-label="Session overview">
          <div>
            <strong>{activeSessions}</strong>
            <span>sessions</span>
          </div>
          <div>
            <strong>{workspaceState}</strong>
            <span>workspace</span>
          </div>
        </div>
      </div>

      {error ? <p className="sidebar-error">{error}</p> : null}

      <SessionList
        sessions={sessions}
        selectedSessionId={selectedSessionId}
        loading={loadingSessions}
        onSelectSession={onSelectSession}
      />

      <div className="user-block">
        <div className="avatar">{initialsFromEmail(email)}</div>
        <div className="user-meta">
          <strong title={displayName}>{displayName}</strong>
          <span>{email}</span>
        </div>
        <button
          type="button"
          className={settingsOpen ? "settings-fab active" : "settings-fab"}
          onClick={() => setSettingsOpen((current) => !current)}
          aria-label="Workspace settings"
          aria-expanded={settingsOpen}
        >
          ⚙
        </button>
        {settingsOpen ? (
          <WorkspaceSettingsMenu preferences={workspacePreferences} onPreferenceChange={onWorkspacePreferenceChange} />
        ) : null}
        <button type="button" className="icon-button" onClick={onSignOut} title="Sign out">
          Sign out
        </button>
      </div>
    </aside>
  );
}
