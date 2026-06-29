import React from "react";

const INLINE_MARKDOWN_PATTERN = /(\*\*[^*]+\*\*|\[Page\s+\d+\])/g;

function renderToken(token, index) {
  if (token.startsWith("**") && token.endsWith("**")) {
    return <strong key={`${token}-${index}`}>{token.slice(2, -2)}</strong>;
  }

  if (/^\[Page\s+\d+\]$/.test(token)) {
    return (
      <mark className="message-citation" key={`${token}-${index}`}>
        {token}
      </mark>
    );
  }

  return <React.Fragment key={`${token}-${index}`}>{token}</React.Fragment>;
}

export default function FormattedMessage({ text }) {
  return String(text || "")
    .split(INLINE_MARKDOWN_PATTERN)
    .filter(Boolean)
    .map(renderToken);
}
