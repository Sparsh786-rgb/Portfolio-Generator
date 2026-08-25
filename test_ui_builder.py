"""
Phase 4 Test Suite — Builder Workspace UI/UX & Navigation Integration.

Verifies:
  - Landing page (/) loads successfully with hero CTAs.
  - Builder workspace (/builder) loads with required UI components.
  - Flow stepper header (01 Upload, 02 AI Processing, 03 Portfolio Ready) is present.
  - Drag-and-drop upload zone and CTA button exist.
  - /generate POST route processes inputs and returns portfolio render.
  - /download route returns downloadable file attachment.
  - /portfolio/sample route loads verified sample.
  - Error responses remain user-safe without exposing keys or stack traces.
"""

import unittest
from pathlib import Path
from unittest.mock import patch
from app import app
from ai.validator import get_sample_portfolio_data

BASE_DIR = Path(__file__).resolve().parent


class TestUIBuilder(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True

    def test_landing_page_loads(self):
        """Verifies landing page / loads with hero titles and navigation."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        html = response.data.decode('utf-8')
        self.assertIn("NovaFolio", html)
        self.assertIn("Build My Portfolio", html)
        self.assertIn("Try Sample", html)
        self.assertIn("How It Works", html)

    def test_builder_page_loads(self):
        """Verifies /builder workspace loads with 3-stage flow header, dropzone, and CTA button."""
        response = self.client.get('/builder')
        self.assertEqual(response.status_code, 200)
        html = response.data.decode('utf-8')
        self.assertIn("Build Your", html)
        self.assertIn("Upload", html)
        self.assertIn("AI Processing", html)
        self.assertIn("Portfolio Ready", html)
        self.assertIn("Drop your resume here", html)
        self.assertIn("Generate My Portfolio", html)
        self.assertIn("Use Sample Resume", html)

    def test_sample_resume_api_endpoint(self):
        """Verifies /api/sample-resume returns content."""
        response = self.client.get('/api/sample-resume')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["success"])
        self.assertIn("ALEX R. CHEN", data["content"])

    def test_sample_portfolio_preview_endpoint(self):
        """Verifies /portfolio/sample renders sample portfolio."""
        response = self.client.get('/portfolio/sample')
        self.assertEqual(response.status_code, 200)
        html = response.data.decode('utf-8')
        self.assertIn("Alex R. Chen", html)
        self.assertIn("DevPulse", html)

    @patch("app.extract_portfolio_from_resume")
    def test_generate_endpoint_works(self, mock_extract):
        """Verifies /generate POST route handles valid resume text and returns portfolio render."""
        mock_extract.return_value = (True, get_sample_portfolio_data(), "Success")
        sample_text = (
            "Alex R. Chen\nFull Stack Engineer\nEmail: alex@example.com\n"
            "Technical Skills: Python, Flask, React, SQL, HTML5, CSS3.\n"
            "Education: BS Computer Science UC Berkeley 2026."
        )
        response = self.client.post('/generate', data={'resume_text': sample_text})
        self.assertEqual(response.status_code, 200)
        html = response.data.decode('utf-8')
        self.assertIn("Alex R. Chen", html)

    def test_download_endpoint_works(self):
        """Verifies /download returns portfolio.html attachment."""
        response = self.client.get('/download')
        self.assertEqual(response.status_code, 200)
        self.assertIn('attachment', response.headers.get('Content-Disposition', ''))

    def test_error_response_remains_user_safe(self):
        """Verifies input validation errors return friendly user messages without tracebacks."""
        response = self.client.post('/generate', data={'resume_text': 'Short'})
        self.assertEqual(response.status_code, 400)
        html = response.data.decode('utf-8')
        self.assertIn("too short", html.lower())
        self.assertNotIn("Traceback", html)
        self.assertNotIn("GEMINI_API_KEY", html)


if __name__ == '__main__':
    unittest.main()
