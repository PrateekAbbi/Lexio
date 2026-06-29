import React from "react";

export default function ChatComposer({ disabled, onChange, onSubmit, onKeyDown, textareaRef, value }) {
  return (
    <div className="chat-input-bar">
      <textarea
        ref={textareaRef}
        value={value}
        onChange={onChange}
        onKeyDown={onKeyDown}
        placeholder="Ask a question or follow up on the previous answer..."
        rows={1}
      />
      <button type="button" className="send-button" onClick={onSubmit} disabled={disabled}>
        Send
      </button>
    </div>
  );
}
