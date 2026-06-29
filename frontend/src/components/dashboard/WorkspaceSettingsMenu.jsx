import React from "react";

export default function WorkspaceSettingsMenu({ preferences, onPreferenceChange }) {
  return (
    <div className="workspace-settings-menu">
      <strong>Workspace panels</strong>
      <label>
        <input
          type="checkbox"
          checked={preferences.documentPreview}
          onChange={(event) => onPreferenceChange("documentPreview", event.target.checked)}
        />
        <span>Enable Document preview</span>
      </label>
      <label>
        <input
          type="checkbox"
          checked={preferences.metrics}
          onChange={(event) => onPreferenceChange("metrics", event.target.checked)}
        />
        <span>Enable metrics</span>
      </label>
    </div>
  );
}
