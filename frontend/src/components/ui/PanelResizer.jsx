import React from "react";

export default function PanelResizer({ className = "", label, onResizeStart }) {
  return (
    <div
      className={`panel-resizer ${className}`.trim()}
      role="separator"
      aria-orientation="vertical"
      aria-label={label}
      onPointerDown={onResizeStart}
    />
  );
}
