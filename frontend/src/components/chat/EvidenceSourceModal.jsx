import React, { useEffect } from "react";
import { sourcePercent } from "../../utils/formatters.js";

function sourceText(source) {
  return source?.text || source?.text_snippet || "";
}

function compactText(value = "") {
  return value.replace(/\s+/g, " ").trim();
}

function splitNumberedPoints(text) {
  const normalized = compactText(text);
  const starts = [];
  const markerPattern = /(^|\s)(\d{1,3}\.)\s+(?=[A-Z])/g;
  let match = markerPattern.exec(normalized);

  while (match) {
    starts.push(match.index + match[1].length);
    match = markerPattern.exec(normalized);
  }

  return starts.map((start, index) => {
    const end = starts[index + 1] ?? normalized.length;
    return compactText(normalized.slice(start, end));
  });
}

function splitParagraphs(text) {
  return text
    .split(/\n{2,}/)
    .map(compactText)
    .filter(Boolean);
}

function sourceWords(text) {
  return new Set(
    compactText(text)
      .toLowerCase()
      .split(/[^a-z0-9]+/)
      .filter((word) => word.length > 3),
  );
}

function scoreCandidate(candidate, matchText) {
  const candidateText = compactText(candidate).toLowerCase();
  const normalizedMatch = compactText(matchText).toLowerCase();

  if (!candidateText) return 0;
  if (normalizedMatch.includes(candidateText)) return candidateText.length * 2;
  if (candidateText.includes(normalizedMatch)) return normalizedMatch.length * 2;

  const candidateWords = sourceWords(candidateText);
  return [...sourceWords(normalizedMatch)].reduce((score, word) => {
    return score + (candidateWords.has(word) ? word.length : 0);
  }, 0);
}

function bestCandidate(candidates, matchText) {
  return candidates.reduce(
    (best, candidate) => {
      const score = scoreCandidate(candidate, matchText);
      return score > best.score ? { text: candidate, score } : best;
    },
    { text: candidates[0] || "", score: -1 },
  ).text;
}

function sourcePassage(source) {
  const fullText = sourceText(source);
  const matchText = source?.text_snippet || fullText;
  const numberedPoints = splitNumberedPoints(fullText);

  if (numberedPoints.length) {
    return {
      kind: "Matched Point",
      text: bestCandidate(numberedPoints, matchText),
    };
  }

  const paragraphs = splitParagraphs(fullText);
  return {
    kind: "Matched Paragraph",
    text: paragraphs.length > 1 ? bestCandidate(paragraphs, matchText) : compactText(fullText),
  };
}

function highlightText(passageText, matchText) {
  const text = compactText(passageText);
  const match = compactText(matchText);
  const textLower = text.toLowerCase();
  const matchLower = match.toLowerCase();

  let highlight = "";
  if (textLower.includes(matchLower)) {
    highlight = text.slice(textLower.indexOf(matchLower), textLower.indexOf(matchLower) + match.length);
  } else if (matchLower.includes(textLower)) {
    highlight = text;
  }

  const matchIndex = highlight ? textLower.indexOf(highlight.toLowerCase()) : -1;

  if (!text || matchIndex === -1) {
    return <mark>{text}</mark>;
  }

  const before = text.slice(0, matchIndex);
  const marked = text.slice(matchIndex, matchIndex + highlight.length);
  const after = text.slice(matchIndex + highlight.length);

  return (
    <>
      {before}
      <mark>{marked}</mark>
      {after}
    </>
  );
}

export default function EvidenceSourceModal({ source, onClose }) {
  useEffect(() => {
    function handleKeyDown(event) {
      if (event.key === "Escape") onClose();
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  if (!source) return null;
  const passage = sourcePassage(source);

  return (
    <div className="modal-backdrop evidence-modal-backdrop" role="dialog" aria-modal="true">
      <section className="evidence-modal" aria-label={`Source from page ${source.page}`}>
        <div className="modal-header evidence-modal-header">
          <div>
            <span>{passage.kind}</span>
            <h2>
              Page {source.page} - {sourcePercent(source)} match
            </h2>
          </div>
          <button type="button" className="close-button" onClick={onClose}>
            Close
          </button>
        </div>

        <article className="pdf-snippet evidence-modal-snippet">
          <strong>
            Page {source.page}
            {Number.isFinite(source.chunk_index) ? `, Chunk ${source.chunk_index}` : ""} - {sourcePercent(source)}
          </strong>
          <p>{highlightText(passage.text, source.text_snippet || passage.text)}</p>
        </article>
      </section>
    </div>
  );
}
