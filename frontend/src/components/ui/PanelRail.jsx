import React from "react";

export default function PanelRail({ className, label, marker, direction, onExpand }) {
  return (
    <aside className={`${className} panel-collapsed`} aria-label={`${label} collapsed`}>
      <button type="button" className="panel-rail-button" onClick={onExpand} aria-label={`Expand ${label}`}>
        <span>{marker}</span>
        <strong>{direction}</strong>
      </button>
    </aside>
  );
}
