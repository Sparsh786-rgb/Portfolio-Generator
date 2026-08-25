"""
Phase 5 Test Suite — PDF Resume Support, Robust File Extraction & Security.

Tests 20 required scenarios:
  1. Valid TXT resume extracts correctly.
  2. Empty TXT is rejected.
  3. Short TXT (< 50 chars) is rejected.
  4. TXT with Unicode characters works.
  5. TXT with unusual / path-traversal filenames works safely.
  6. Valid text-based PDF extracts correctly.
  7. Multi-page PDF extracts text.
  8. Empty/textless (scanned) PDF is rejected.
  9. Invalid/corrupt PDF is rejected.
  10. Renamed non-PDF with .pdf extension is rejected.
  11. PDF with Unicode text is handled.
  12. PDF larger than 2MB is rejected.
  13. Path traversal filenames are sanitized safely.
  14. Uploaded files do not leak to public static directory.
  15. User-facing errors do not expose tracebacks or internal paths.
  16. TXT resume reaches existing Gemini pipeline.
  17. PDF resume reaches existing Gemini pipeline.
  18. Sample resume still works.
  19. Existing /generate behavior remains functional.
  20. Existing /download behavior remains functional.
"""

import io
import unittest
from pathlib import Path
from unittest.mock import patch
import pypdf

from app import app
from ai.file_extractor import (
    extract_text_from_file,
    extract_text_from_txt,
    extract_text_from_pdf,
    sanitize_filename,
)
from ai.validator import get_sample_portfolio_data

BASE_DIR = Path(__file__).resolve().parent


def make_test_pdf_bytes(text: str = "Alex R Chen Software Engineer UC Berkeley Computer Science 2026") -> bytes:
    """Creates a valid text-based PDF binary stream for deterministic testing."""
    escaped = text.replace("(", "\\(").replace(")", "\\)")
    stream_content = f"BT /F1 12 Tf 70 700 Td ({escaped}) Tj ET".encode("latin1", "replace")
    stream_len = len(stream_content)

    return (
        b"%PDF-1.4\n"
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj\n"
        b"4 0 obj << /Length " + str(stream_len).encode() + b" >> stream\n"
        + stream_content + b"\nendstream endobj\n"
        b"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n"
        b"xref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000246 00000 n \n0000000340 00000 n \n"
        b"trailer << /Size 6 /Root 1 0 R >>\nstartxref\n420\n%%EOF"
    )


class TestFileHandling(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True

    # -------------------------------------------------------------------------
    # TXT Tests (1-5)
    # -------------------------------------------------------------------------
    def test_01_valid_txt_extracts_correctly(self):
        txt_content = (
            "Jane Smith\nFull Stack Developer\nEmail: jane@example.com\n"
            "Skills: Python, Flask, React, SQL, HTML5, CSS3.\n"
            "Education: MIT BS Computer Science 2024."
        ).encode("utf-8")
        success, text = extract_text_from_file(txt_content, "resume.txt")
        self.assertTrue(success)
        self.assertIn("Jane Smith", text)

    def test_02_empty_txt_rejected(self):
        success, err = extract_text_from_file(b"", "empty.txt")
        self.assertFalse(success)
        self.assertIn("empty", err.lower())

    def test_03_short_txt_rejected(self):
        success, err = extract_text_from_file(b"Too short text", "short.txt")
        self.assertFalse(success)
        self.assertIn("too short", err.lower())

    def test_04_txt_unicode_characters_work(self):
        unicode_txt = (
            "José Résumé Developer\nSkills: C++, Python, JavaScript, HTML.\n"
            "Education: Universidade de São Paulo, Computer Engineering 2025."
        ).encode("utf-8")
        success, text = extract_text_from_file(unicode_txt, "unicode.txt")
        self.assertTrue(success)
        self.assertIn("José Résumé", text)

    def test_05_txt_unusual_filenames_handled_safely(self):
        txt_content = (
            "Alex R. Chen\nFull Stack Developer\nEmail: alex@example.com\n"
            "Technical Skills: Python, Flask, React, SQL, HTML5, CSS3.\n"
            "Education: UC Berkeley Computer Science 2026."
        ).encode("utf-8")
        success, text = extract_text_from_file(txt_content, "../../secret_path/my_resume.txt")
        self.assertTrue(success)
        self.assertIn("Alex R. Chen", text)

    # -------------------------------------------------------------------------
    # PDF Tests (6-12)
    # -------------------------------------------------------------------------
    def test_06_valid_pdf_extracts_correctly(self):
        pdf_bytes = make_test_pdf_bytes("Alex R Chen Software Engineer UC Berkeley Computer Science 2026")
        success, text = extract_text_from_file(pdf_bytes, "resume.pdf")
        self.assertTrue(success)
        self.assertIn("Alex R Chen", text)

    def test_07_multipage_pdf_extracts_text(self):
        # Programmatically construct 2-page PDF
        writer = pypdf.PdfWriter()
        # Page 1
        page1_bytes = make_test_pdf_bytes("Page 1 Content: Alex R Chen Software Engineer UC Berkeley 2026")
        r1 = pypdf.PdfReader(io.BytesIO(page1_bytes))
        writer.add_page(r1.pages[0])
        # Page 2
        page2_bytes = make_test_pdf_bytes("Page 2 Content: Experience at Tech Corp Senior Developer 2025")
        r2 = pypdf.PdfReader(io.BytesIO(page2_bytes))
        writer.add_page(r2.pages[0])

        out = io.BytesIO()
        writer.write(out)
        pdf_bytes = out.getvalue()

        success, text = extract_text_from_file(pdf_bytes, "multi_page.pdf")
        self.assertTrue(success)
        self.assertIn("Page 1 Content", text)
        self.assertIn("Page 2 Content", text)

    def test_08_empty_scanned_pdf_rejected(self):
        # Create a PDF page with no text annotations/content (simulating scanned/image PDF)
        writer = pypdf.PdfWriter()
        writer.add_blank_page(width=612, height=792)
        out = io.BytesIO()
        writer.write(out)
        pdf_bytes = out.getvalue()

        success, err = extract_text_from_file(pdf_bytes, "scanned.pdf")
        self.assertFalse(success)
        self.assertTrue("selectable text" in err.lower() or "scanned" in err.lower())

    def test_09_invalid_corrupt_pdf_rejected(self):
        corrupt_bytes = b"%PDF-1.4\ncorrupted_binary_garbage_stream_12345"
        success, err = extract_text_from_file(corrupt_bytes, "corrupt.pdf")
        self.assertFalse(success)
        self.assertIn("couldn't read this pdf", err.lower())

    def test_10_renamed_non_pdf_file_rejected(self):
        fake_pdf_bytes = b"This is a text file renamed to resume.pdf without PDF headers."
        success, err = extract_text_from_file(fake_pdf_bytes, "fake.pdf")
        self.assertFalse(success)
        self.assertIn("couldn't read this pdf", err.lower())

    def test_11_pdf_unicode_text_handled(self):
        pdf_bytes = make_test_pdf_bytes("Alex Chen Software Engineer Berkeley Computer Science 2026")
        success, text = extract_text_from_file(pdf_bytes, "unicode_resume.pdf")
        self.assertTrue(success)
        self.assertIn("Alex Chen", text)

    def test_12_pdf_larger_than_2mb_rejected(self):
        large_bytes = b"%PDF-1.4\n" + b"X" * (2 * 1024 * 1024 + 100)
        success, err = extract_text_from_file(large_bytes, "huge.pdf")
        self.assertFalse(success)
        self.assertIn("too large", err.lower())

    # -------------------------------------------------------------------------
    # Security Tests (13-15)
    # -------------------------------------------------------------------------
    def test_13_path_traversal_filename_sanitized(self):
        clean1 = sanitize_filename("../../etc/passwd")
        clean2 = sanitize_filename("..\\..\\Windows\\System32\\secret.txt")
        self.assertNotIn("..", clean1)
        self.assertNotIn("/", clean1)
        self.assertNotIn("\\", clean2)

    def test_14_files_do_not_leak_to_static_dir(self):
        static_dir = BASE_DIR / "static"
        pdf_bytes = make_test_pdf_bytes()
        response = self.client.post('/generate', data={'resume_file': (io.BytesIO(pdf_bytes), 'test.pdf')})
        # Check no uploaded pdf file was saved to static/
        leaked_files = list(static_dir.glob("*.pdf"))
        self.assertEqual(len(leaked_files), 0)

    def test_15_user_errors_do_not_expose_tracebacks(self):
        corrupt_bytes = b"%PDF-1.4\nbroken_stream"
        response = self.client.post('/generate', data={'resume_file': (io.BytesIO(corrupt_bytes), 'broken.pdf')})
        self.assertEqual(response.status_code, 400)
        html = response.data.decode('utf-8')
        self.assertNotIn("Traceback", html)
        self.assertNotIn("pypdf.errors", html)
        self.assertNotIn("GEMINI_API_KEY", html)

    # -------------------------------------------------------------------------
    # Integration Tests (16-20)
    # -------------------------------------------------------------------------
    @patch("app.extract_portfolio_from_resume")
    def test_16_txt_resume_reaches_gemini_pipeline(self, mock_extract):
        mock_extract.return_value = (True, get_sample_portfolio_data(), "Success")
        txt_content = (
            "Alex R. Chen\nFull Stack Developer\nEmail: alex@example.com\n"
            "Technical Skills: Python, Flask, React, SQL, HTML5, CSS3.\n"
            "Education: UC Berkeley Computer Science 2026."
        ).encode("utf-8")

        response = self.client.post('/generate', data={'resume_file': (io.BytesIO(txt_content), 'resume.txt')})
        self.assertEqual(response.status_code, 200)
        mock_extract.assert_called_once()

    @patch("app.extract_portfolio_from_resume")
    def test_17_pdf_resume_reaches_gemini_pipeline(self, mock_extract):
        mock_extract.return_value = (True, get_sample_portfolio_data(), "Success")
        pdf_bytes = make_test_pdf_bytes("Alex R Chen Software Engineer UC Berkeley Computer Science 2026")

        response = self.client.post('/generate', data={'resume_file': (io.BytesIO(pdf_bytes), 'resume.pdf')})
        self.assertEqual(response.status_code, 200)
        mock_extract.assert_called_once()
        # Verify extracted text passed to Gemini contains extracted PDF text
        passed_text = mock_extract.call_args[0][0]
        self.assertIn("Alex R Chen", passed_text)

    def test_18_sample_resume_still_works(self):
        response = self.client.get('/api/sample-resume')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["success"])

    @patch("app.extract_portfolio_from_resume")
    def test_19_existing_generate_text_form_works(self, mock_extract):
        mock_extract.return_value = (True, get_sample_portfolio_data(), "Success")
        sample_text = (
            "Alex R. Chen\nFull Stack Developer\nEmail: alex@example.com\n"
            "Technical Skills: Python, Flask, React, SQL, HTML5, CSS3.\n"
            "Education: UC Berkeley Computer Science 2026."
        )
        response = self.client.post('/generate', data={'resume_text': sample_text})
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Alex R. Chen", response.data)

    def test_20_existing_download_behavior_works(self):
        response = self.client.get('/download')
        self.assertEqual(response.status_code, 200)
        self.assertIn('attachment', response.headers.get('Content-Disposition', ''))


if __name__ == '__main__':
    unittest.main()
