"""
Phase 3 Test Suite — Dynamic Portfolio Rendering, Conditional Sections & Security.

Verifies:
  - All 9 mandatory sections render dynamically when data is present.
  - Empty sections are hidden (Summary, Skills, Education, Experience, Projects, Achievements).
  - Missing contact links/buttons (LinkedIn, GitHub, Project URLs) are hidden.
  - HTML escaping prevents XSS injection from resume/AI text.
  - output/portfolio.html is automatically persisted.
  - /download endpoint serves output/portfolio.html.
"""

import unittest
from pathlib import Path
from unittest.mock import patch
from app import app
from ai.models import PortfolioData
from ai.validator import get_sample_portfolio_data

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"


class TestPortfolioRendering(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True

    def test_full_portfolio_data_renders_all_sections(self):
        """Verifies full portfolio renders Hero, About Me, Skills, Experience, Projects, Education, Achievements, and Contact."""
        response = self.client.get('/portfolio/sample')
        self.assertEqual(response.status_code, 200)

        html = response.data.decode('utf-8')
        self.assertIn("Alex R. Chen", html)
        self.assertIn("About Me", html)
        self.assertIn("Skills", html)
        self.assertIn("Experience", html)
        self.assertIn("Featured Projects", html)
        self.assertIn("Education", html)
        self.assertIn("Achievements", html)
        self.assertIn("alex.chen.dev@example.com", html)

    def test_empty_summary_hides_summary_section(self):
        """Verifies that an empty summary hides the 'About Me' section."""
        data = get_sample_portfolio_data()
        data["summary"] = ""
        portfolio_obj = PortfolioData.model_validate(data)

        with app.test_request_context():
            from flask import render_template
            rendered = render_template("portfolio.html", data=portfolio_obj.to_template_dict())
            self.assertNotIn("About Me", rendered)

    def test_empty_skills_hides_skills_section(self):
        """Verifies that an empty skills list hides the 'Skills & Technologies' section."""
        data = get_sample_portfolio_data()
        data["skills"] = []
        portfolio_obj = PortfolioData.model_validate(data)

        with app.test_request_context():
            from flask import render_template
            rendered = render_template("portfolio.html", data=portfolio_obj.to_template_dict())
            self.assertNotIn("Skills & Technologies", rendered)
            self.assertNotIn("Skills &amp; Technologies", rendered)

    def test_empty_education_hides_education_section(self):
        """Verifies that an empty education list hides the 'Education' section."""
        data = get_sample_portfolio_data()
        data["education"] = []
        portfolio_obj = PortfolioData.model_validate(data)

        with app.test_request_context():
            from flask import render_template
            rendered = render_template("portfolio.html", data=portfolio_obj.to_template_dict())
            self.assertNotIn('<h2 class="p-section-title">Education</h2>', rendered)

    def test_empty_experience_hides_experience_section(self):
        """Verifies that an empty experience list hides the 'Experience' section."""
        data = get_sample_portfolio_data()
        data["experience"] = []
        portfolio_obj = PortfolioData.model_validate(data)

        with app.test_request_context():
            from flask import render_template
            rendered = render_template("portfolio.html", data=portfolio_obj.to_template_dict())
            self.assertNotIn('<h2 class="p-section-title">Experience</h2>', rendered)

    def test_empty_projects_hides_projects_section(self):
        """Verifies that an empty projects list hides the 'Featured Projects' section."""
        data = get_sample_portfolio_data()
        data["projects"] = []
        portfolio_obj = PortfolioData.model_validate(data)

        with app.test_request_context():
            from flask import render_template
            rendered = render_template("portfolio.html", data=portfolio_obj.to_template_dict())
            self.assertNotIn("Featured Projects", rendered)

    def test_empty_achievements_hides_achievements_section(self):
        """Verifies that an empty achievements list hides the 'Achievements & Honors' section."""
        data = get_sample_portfolio_data()
        data["achievements"] = []
        portfolio_obj = PortfolioData.model_validate(data)

        with app.test_request_context():
            from flask import render_template
            rendered = render_template("portfolio.html", data=portfolio_obj.to_template_dict())
            self.assertNotIn("Achievements & Honors", rendered)
            self.assertNotIn("Achievements &amp; Honors", rendered)

    def test_missing_linkedin_hides_linkedin_button(self):
        """Verifies that a missing LinkedIn link hides the LinkedIn contact pill."""
        data = get_sample_portfolio_data()
        data["contact"]["linkedin"] = ""
        portfolio_obj = PortfolioData.model_validate(data)

        with app.test_request_context():
            from flask import render_template
            rendered = render_template("portfolio.html", data=portfolio_obj.to_template_dict())
            self.assertNotIn('aria-label="LinkedIn profile"', rendered)

    def test_missing_github_hides_github_button(self):
        """Verifies that a missing GitHub link hides the GitHub contact pill."""
        data = get_sample_portfolio_data()
        data["contact"]["github"] = ""
        portfolio_obj = PortfolioData.model_validate(data)

        with app.test_request_context():
            from flask import render_template
            rendered = render_template("portfolio.html", data=portfolio_obj.to_template_dict())
            self.assertNotIn('aria-label="GitHub profile"', rendered)

    def test_missing_project_urls_hide_project_buttons(self):
        """Verifies that projects without GitHub or Live links do not render link buttons."""
        data = get_sample_portfolio_data()
        data["projects"] = [
            {
                "title": "No Link Project",
                "description": "Project without links.",
                "technologies": ["Python"],
                "github": "",
                "live_link": ""
            }
        ]
        portfolio_obj = PortfolioData.model_validate(data)

        with app.test_request_context():
            from flask import render_template
            rendered = render_template("portfolio.html", data=portfolio_obj.to_template_dict())
            self.assertIn("No Link Project", rendered)
            self.assertNotIn('class="project-links"', rendered)

    def test_html_escaping_prevents_xss(self):
        """Verifies Jinja HTML auto-escaping prevents script injection."""
        data = get_sample_portfolio_data()
        data["name"] = "<script>alert('XSS-NAME')</script>"
        data["summary"] = "<img src=x onerror=alert('XSS-SUMMARY')>"
        portfolio_obj = PortfolioData.model_validate(data)

        with app.test_request_context():
            from flask import render_template
            rendered = render_template("portfolio.html", data=portfolio_obj.to_template_dict())
            self.assertNotIn("<script>alert('XSS-NAME')</script>", rendered)
            self.assertNotIn("<img src=x onerror=alert('XSS-SUMMARY')>", rendered)
            self.assertIn("&lt;script&gt;", rendered)
            self.assertIn("&lt;img", rendered)

    @patch("main.extract_portfolio_from_resume")
    def test_portfolio_file_generated_successfully(self, mock_extract):
        """Verifies main.py CLI generator creates output/portfolio.html."""
        mock_extract.return_value = (True, get_sample_portfolio_data(), "Success")
        output_file = OUTPUT_DIR / "portfolio.html"
        from main import generate_from_file
        target_resume = BASE_DIR / "resume.txt"
        success = generate_from_file(target_resume, output_file)
        self.assertTrue(success)
        self.assertTrue(output_file.exists())
        self.assertGreater(output_file.stat().st_size, 500)

    def test_download_route_works(self):
        """Verifies the /download Flask route returns portfolio.html file attachment."""
        response = self.client.get('/download')
        self.assertEqual(response.status_code, 200)
        self.assertIn('attachment', response.headers.get('Content-Disposition', ''))
        self.assertIn('portfolio.html', response.headers.get('Content-Disposition', ''))


if __name__ == '__main__':
    unittest.main()
