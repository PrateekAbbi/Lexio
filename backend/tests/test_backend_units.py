"""Fast, dependency-light tests for backend service boundaries."""

from pathlib import Path
import unittest

from fastapi.testclient import TestClient

from app.main import app
from app.models import RetrievedChunk
from app.services.chunking import build_chunks_for_page, estimate_tokens, split_sentences
from app.services.pdf import extract_pdf_text
from app.services.qa import build_sources, format_context, format_session_summary, similarity_from_distance


class HealthRouteTests(unittest.TestCase):
    def test_health_route(self) -> None:
        response = TestClient(app).get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})


class ChunkingTests(unittest.TestCase):
    def test_split_sentences_preserves_offsets(self) -> None:
        sentences = split_sentences("First sentence. Second sentence.")

        self.assertEqual([sentence for sentence, _, _ in sentences], ["First sentence.", "Second sentence."])
        self.assertEqual(sentences[0][1:], (0, 15))
        self.assertEqual(sentences[1][1:], (16, 32))

    def test_build_chunks_for_page_returns_citation_metadata(self) -> None:
        chunks = build_chunks_for_page("This is sentence one. This is sentence two.", page_number=3)

        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].page_number, 3)
        self.assertEqual(chunks[0].chunk_index, 0)
        self.assertGreater(estimate_tokens(chunks[0].text), 0)


class PdfExtractionTests(unittest.TestCase):
    def test_extract_sample_pdf_text(self) -> None:
        sample_pdf = Path(__file__).resolve().parents[2] / "sample-docs" / "synthetic_mutual_nda.pdf"
        pages, page_count = extract_pdf_text(sample_pdf.read_bytes())

        self.assertEqual(page_count, len(pages))
        self.assertGreater(page_count, 0)
        self.assertTrue(pages[0].text)


class QuestionAnsweringFormattingTests(unittest.TestCase):
    def test_similarity_clamps_to_expected_range(self) -> None:
        self.assertEqual(similarity_from_distance(-5), 1.0)
        self.assertEqual(similarity_from_distance(5), 0.0)
        self.assertEqual(similarity_from_distance(0.25), 0.75)

    def test_context_and_sources_use_retrieved_metadata(self) -> None:
        chunks = [
            RetrievedChunk(
                text="Confidentiality obligations survive termination.",
                metadata={"page_number": 7, "chunk_index": 2},
                distance=0.2,
            )
        ]

        self.assertIn("[Page 7, Chunk 2]", format_context(chunks))
        self.assertEqual(
            build_sources(chunks)[0],
            {
                "page": 7,
                "chunk_index": 2,
                "text": "Confidentiality obligations survive termination.",
                "text_snippet": "Confidentiality obligations survive termination.",
                "similarity_score": 0.8,
            },
        )

    def test_session_summary_preserves_frontend_shape(self) -> None:
        summary = format_session_summary(
            {
                "id": "session-1",
                "title": "Termination",
                "last_active_at": "2026-06-28T00:00:00+00:00",
                "documents": {"filename": "contract.pdf", "page_count": 10, "chunk_count": 20},
            }
        )

        self.assertEqual(summary["session_id"], "session-1")
        self.assertEqual(summary["filename"], "contract.pdf")
        self.assertIsNone(summary["message_count"])


if __name__ == "__main__":
    unittest.main()
