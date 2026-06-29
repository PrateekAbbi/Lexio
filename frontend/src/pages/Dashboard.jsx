import React, { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import ChatThread from "../components/ChatThread.jsx";
import UploadModal from "../components/UploadModal.jsx";
import DashboardSidebar from "../components/dashboard/DashboardSidebar.jsx";
import EmptyWorkspace from "../components/dashboard/EmptyWorkspace.jsx";
import PanelResizer from "../components/ui/PanelResizer.jsx";
import { isAuthSessionExpiredError } from "../api.js";
import { useAuth } from "../auth/AuthProvider.jsx";
import { useLocalStorageState } from "../hooks/useLocalStorageState.js";
import { useMediaQuery } from "../hooks/useMediaQuery.js";
import { useResizablePanel } from "../hooks/useResizablePanel.js";
import { fetchSessions } from "../services/sessions.js";
import { supabase } from "../supabaseClient.js";

const DEFAULT_WORKSPACE_PREFS = {
  documentPreview: true,
  metrics: true,
};

const MOBILE_WORKSPACE_PREFS = {
  documentPreview: false,
  metrics: false,
};

export default function Dashboard() {
  const { user } = useAuth();
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const isMobile = useMediaQuery("(max-width: 880px)");
  const sidebar = useResizablePanel(320, { min: 260, max: 430 });
  const [sessions, setSessions] = useState([]);
  const [loadingSessions, setLoadingSessions] = useState(true);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [desktopWorkspacePrefs, setDesktopWorkspacePrefs] = useLocalStorageState("lexio-workspace-prefs", DEFAULT_WORKSPACE_PREFS);
  const [mobileWorkspacePrefs, setMobileWorkspacePrefs] = useLocalStorageState("lexio-mobile-workspace-prefs", MOBILE_WORKSPACE_PREFS);
  const [error, setError] = useState("");

  async function loadSessions() {
    setLoadingSessions(true);
    setError("");
    try {
      setSessions(await fetchSessions());
    } catch (err) {
      if (isAuthSessionExpiredError(err)) return;
      setError(err.message || "Failed to load sessions.");
    } finally {
      setLoadingSessions(false);
    }
  }

  useEffect(() => {
    loadSessions();
  }, []);

  const selectedSession = useMemo(() => {
    return sessions.find((item) => item.session_id === sessionId) || null;
  }, [sessions, sessionId]);

  async function signOut() {
    await supabase.auth.signOut();
    navigate("/login", { replace: true });
  }

  function handleSessionCreated(session) {
    setSessions((current) => [session, ...current.filter((item) => item.session_id !== session.session_id)]);
    setShowUploadModal(false);
    navigate(`/session/${session.session_id}`);
    setMobileSidebarOpen(false);
  }

  function updateWorkspacePref(key, value) {
    const update = (current) => ({ ...current, [key]: value });
    if (isMobile) setMobileWorkspacePrefs(update);
    else setDesktopWorkspacePrefs(update);
  }

  const displayName = user?.user_metadata?.full_name || user?.email || "Signed in user";
  const activeSessions = sessions.length;
  const workspacePrefs = isMobile ? mobileWorkspacePrefs : desktopWorkspacePrefs;

  function selectSession(id) {
    navigate(`/session/${id}`);
    setMobileSidebarOpen(false);
  }

  function openUploadModal() {
    setShowUploadModal(true);
    setMobileSidebarOpen(false);
  }

  return (
    <main className="dashboard-shell" style={{ gridTemplateColumns: `${sidebar.width}px 10px minmax(0, 1fr)` }}>
      <button
        type="button"
        className="mobile-menu-button"
        onClick={() => setMobileSidebarOpen(true)}
        aria-label="Open navigation"
      >
        ☰
      </button>
      {mobileSidebarOpen ? (
        <button
          type="button"
          className="mobile-sidebar-backdrop"
          onClick={() => setMobileSidebarOpen(false)}
          aria-label="Close navigation"
        />
      ) : null}
      <DashboardSidebar
        activeSessions={activeSessions}
        displayName={displayName}
        email={user?.email}
        error={error}
        isMobile={isMobile}
        isOpen={mobileSidebarOpen}
        loadingSessions={loadingSessions}
        onClose={() => setMobileSidebarOpen(false)}
        onCreateSession={openUploadModal}
        onSelectSession={selectSession}
        onSignOut={signOut}
        onWorkspacePreferenceChange={updateWorkspacePref}
        selectedSessionId={sessionId}
        sessions={sessions}
        workspacePreferences={workspacePrefs}
      />
      <PanelResizer className="sidebar-resizer" label="Resize sidebar" onResizeStart={sidebar.startResize} />

      <section className="main-panel">
        {sessionId ? (
          <ChatThread
            key={sessionId}
            isMobile={isMobile}
            sessionId={sessionId}
            selectedSession={selectedSession}
            onSessionUpdated={loadSessions}
            workspacePrefs={workspacePrefs}
          />
        ) : (
          <EmptyWorkspace onUploadDocument={() => setShowUploadModal(true)} />
        )}
      </section>

      {showUploadModal ? (
        <UploadModal onClose={() => setShowUploadModal(false)} onSessionCreated={handleSessionCreated} />
      ) : null}
    </main>
  );
}
