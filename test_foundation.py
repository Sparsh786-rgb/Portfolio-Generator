"""
Basic Unit & Route Testing for Foundation Phase
"""

import unittest
from unittest.mock import patch
from app import app

class FoundationTestCase(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True

    def test_landing_page(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"NovaFolio", response.data)
        self.assertIn(b"Build My Portfolio", response.data)

    def test_builder_page(self):
        response = self.client.get('/builder')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Build Your", response.data)
        self.assertIn(b"Sample Resume", response.data)

    def test_sample_api(self):
        response = self.client.get('/api/sample-resume')
        self.assertEqual(response.status_code, 200)
        json_data = response.get_json()
        self.assertTrue(json_data['success'])
        self.assertIn("ALEX R. CHEN", json_data['content'])

    def test_sample_portfolio_preview(self):
        response = self.client.get('/portfolio/sample')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Alex R. Chen", response.data)
        self.assertIn(b"DevPulse", response.data)

    def test_health_check(self):
        response = self.client.get('/api/health')
        self.assertEqual(response.status_code, 200)
        json_data = response.get_json()
        self.assertEqual(json_data['status'], 'healthy')

    def test_validation_empty_resume(self):
        response = self.client.post('/generate', data={'resume_text': ''})
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"Resume content is empty", response.data)

    def test_validation_short_resume(self):
        response = self.client.post('/generate', data={'resume_text': 'Too short resume.'})
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"too short", response.data)

    @patch("app.extract_portfolio_from_resume")
    def test_generation_with_valid_text(self, mock_extract):
        from ai.validator import get_sample_portfolio_data
        mock_extract.return_value = (True, get_sample_portfolio_data(), "Success")
        sample_text = (
            "Alex R. Chen\n"
            "Full Stack Developer\n"
            "Email: alex@example.com\n"
            "Technical Skills: Python, Flask, JavaScript, HTML, CSS.\n"
            "Education: UC Berkeley Computer Science 2026.\n"
            "Experience: Software Engineer Intern at Tech Corp."
        )
        response = self.client.post('/generate', data={'resume_text': sample_text})
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Alex R. Chen", response.data)

if __name__ == '__main__':
    unittest.main()
