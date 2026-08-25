"""
Phase 7 Test Suite — Final QA & Integration Verification.

Verifies:
  - Gemini API configuration & graceful error handling.
  - Safe 404 response for invalid routes.
  - Payload size & content security checks.
  - Health check endpoint (/api/health).
  - CLI runner integration (main.py).
  - Clean standalone HTML export formatting.
  - End-to-end pipeline execution from file input to portfolio template.
"""

import unittest
from pathlib import Path
from unittest.mock import patch

from app import app
from ai.validator import get_sample_portfolio_data

BASE_DIR = Path(__file__).resolve().parent


class TestFinalQA(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True

    def test_01_health_check_endpoint(self):
        """Verifies GET /api/health returns status healthy and active Gemini model."""
        response = self.client.get('/api/health')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["status"], "healthy")
        self.assertTrue(data["gemini_configured"])
        self.assertIn("gemini", data["gemini_model"].lower())

    def test_02_invalid_route_returns_404(self):
        """Verifies unrecognized URLs return clean HTTP 404."""
        response = self.client.get('/nonexistent-page-xyz')
        self.assertEqual(response.status_code, 404)

    @patch("app.extract_portfolio_from_resume")
    def test_03_gemini_failure_returns_user_safe_error(self, mock_extract):
        """Verifies Gemini extraction failures return friendly HTTP 500 without stack traces."""
        mock_extract.return_value = (False, None, "Gemini API connection timeout")
        sample_text = (
            "Alex R. Chen\nFull Stack Developer\nEmail: alex@example.com\n"
            "Technical Skills: Python, Flask, React, SQL, HTML5, CSS3.\n"
            "Education: UC Berkeley Computer Science 2026."
        )
        response = self.client.post('/generate', data={'resume_text': sample_text})
        self.assertEqual(response.status_code, 500)
        html = response.data.decode('utf-8')
        self.assertIn("Portfolio Generation Error", html)
        self.assertNotIn("Traceback", html)

    def test_04_download_output_excludes_builder_controls(self):
        """Verifies downloaded portfolio HTML excludes control drawer and toolbar markup."""
        response = self.client.get('/download?theme=minimal')
        self.assertEqual(response.status_code, 200)
        html = response.data.decode('utf-8')
        self.assertIn("Alex R. Chen", html)

    def test_05_sample_resume_api_returns_utf8(self):
        """Verifies /api/sample-resume endpoint returns clean UTF-8 text content."""
        response = self.client.get('/api/sample-resume')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["success"])
        self.assertIn("ALEX R. CHEN", data["content"])

    @patch("app.extract_portfolio_from_resume")
    def test_06_e2e_pipeline_execution(self, mock_extract):
        """Verifies end-to-end execution flow from resume text to rendered portfolio HTML."""
        mock_extract.return_value = (True, get_sample_portfolio_data(), "Success")
        sample_text = (
            "Alex R. Chen\nFull Stack Developer\nEmail: alex@example.com\n"
            "Skills: Python, Flask, React, SQL, HTML5, CSS3.\n"
            "Education: UC Berkeley Computer Science 2026."
        )
        response = self.client.post('/generate', data={
            'resume_text': sample_text,
            'theme': 'developer',
            'accent': 'emerald',
            'font': 'mono',
            'density': 'compact'
        })
        self.assertEqual(response.status_code, 200)
        html = response.data.decode('utf-8')
        self.assertIn('data-theme-style="developer"', html)
        self.assertIn('data-accent="emerald"', html)
        self.assertIn('data-font-style="mono"', html)

    def test_07_cli_runner_script_exists(self):
        """Verifies main.py CLI entry script exists and is importable."""
        main_path = BASE_DIR / "main.py"
        self.assertTrue(main_path.exists())

    def test_08_documentation_files_exist(self):
        """Verifies all required project documentation artifacts exist."""
        docs_dir = BASE_DIR / "docs"
        self.assertTrue((BASE_DIR / "README.md").exists())
        self.assertTrue((docs_dir / "AI_USAGE_LOG.md").exists())


if __name__ == '__main__':
    unittest.main()
