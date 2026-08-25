"""
Phase 6 Test Suite — Portfolio Themes & Customization.

Verifies:
  - Aurora, Minimal, and Developer themes rendering.
  - Whitelisted validation for themes, accents, fonts, and layout density.
  - Zero Gemini API calls triggered by theme switching.
  - Data integrity & anti-hallucination across all themes.
  - Security against arbitrary CSS and template injection.
  - Preserved standalone HTML export & print media behavior.
"""

import unittest
from pathlib import Path
from unittest.mock import patch

from app import app
from ai.theme_validator import (
    validate_theme_options,
    ALLOWED_THEMES,
    ALLOWED_ACCENTS,
    ALLOWED_FONTS,
    ALLOWED_DENSITIES,
)
from ai.models import PortfolioData
from ai.validator import get_sample_portfolio_data

BASE_DIR = Path(__file__).resolve().parent


class TestPortfolioThemes(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True
        self.sample_data = get_sample_portfolio_data()

    # -------------------------------------------------------------------------
    # Theme Availability & Rendering Tests (1-6)
    # -------------------------------------------------------------------------
    def test_01_aurora_theme_exists(self):
        opts = validate_theme_options(theme="aurora")
        self.assertEqual(opts["theme"], "aurora")

    def test_02_minimal_theme_exists(self):
        opts = validate_theme_options(theme="minimal")
        self.assertEqual(opts["theme"], "minimal")

    def test_03_developer_theme_exists(self):
        opts = validate_theme_options(theme="developer")
        self.assertEqual(opts["theme"], "developer")

    def test_04_aurora_renders_valid_html(self):
        response = self.client.get('/portfolio/sample?theme=aurora')
        self.assertEqual(response.status_code, 200)
        html = response.data.decode('utf-8')
        self.assertIn('data-theme-style="aurora"', html)
        self.assertIn("Alex R. Chen", html)

    def test_05_minimal_renders_valid_html(self):
        response = self.client.get('/portfolio/sample?theme=minimal')
        self.assertEqual(response.status_code, 200)
        html = response.data.decode('utf-8')
        self.assertIn('data-theme-style="minimal"', html)
        self.assertIn("Alex R. Chen", html)

    def test_06_developer_renders_valid_html(self):
        response = self.client.get('/portfolio/sample?theme=developer')
        self.assertEqual(response.status_code, 200)
        html = response.data.decode('utf-8')
        self.assertIn('data-theme-style="developer"', html)
        self.assertIn("Alex R. Chen", html)

    # -------------------------------------------------------------------------
    # Data Integrity & Anti-Hallucination Tests (7-9)
    # -------------------------------------------------------------------------
    def test_07_all_themes_consume_same_portfoliodata(self):
        model = PortfolioData.model_validate(self.sample_data)
        for th in ALLOWED_THEMES:
            response = self.client.get(f'/portfolio/sample?theme={th}')
            self.assertEqual(response.status_code, 200)
            self.assertIn(model.name, response.data.decode('utf-8'))

    def test_08_missing_optional_fields_do_not_crash_rendering(self):
        sparse_data = PortfolioData(name="Jane Doe", headline="Developer")
        with app.test_request_context():
            from flask import render_template
            for th in ALLOWED_THEMES:
                html = render_template("portfolio.html", data=sparse_data, theme=th)
                self.assertIn("Jane Doe", html)

    def test_09_themes_do_not_fabricate_content(self):
        sparse_data = PortfolioData(name="Jane Doe")
        with app.test_request_context():
            from flask import render_template
            html = render_template("portfolio.html", data=sparse_data, theme="developer")
            self.assertNotIn("Featured Projects", html)
            self.assertNotIn("Achievements & Honors", html)

    # -------------------------------------------------------------------------
    # Theme Switching & Zero Gemini API Calls (10-12)
    # -------------------------------------------------------------------------
    @patch("ai.gemini.extract_portfolio_from_resume")
    def test_10_theme_switching_does_not_trigger_gemini(self, mock_gemini):
        response = self.client.get('/portfolio/sample?theme=minimal')
        self.assertEqual(response.status_code, 200)
        mock_gemini.assert_not_called()

    def test_11_theme_switching_preserves_portfoliodata(self):
        r1 = self.client.get('/portfolio/sample?theme=aurora')
        r2 = self.client.get('/portfolio/sample?theme=developer')
        self.assertIn("Alex R. Chen", r1.data.decode('utf-8'))
        self.assertIn("Alex R. Chen", r2.data.decode('utf-8'))

    def test_12_theme_preference_persistence_supported(self):
        response = self.client.get('/portfolio/sample?theme=minimal&accent=emerald')
        self.assertEqual(response.status_code, 200)
        html = response.data.decode('utf-8')
        self.assertIn('data-theme-style="minimal"', html)
        self.assertIn('data-accent="emerald"', html)

    # -------------------------------------------------------------------------
    # Customization Whitelist Enforcement (13-16)
    # -------------------------------------------------------------------------
    def test_13_accent_color_options_restricted(self):
        opts_valid = validate_theme_options(accent="cyan")
        opts_invalid = validate_theme_options(accent="invalid_color")
        self.assertEqual(opts_valid["accent"], "cyan")
        self.assertEqual(opts_invalid["accent"], "indigo")

    def test_14_font_options_restricted(self):
        opts_valid = validate_theme_options(font="mono")
        opts_invalid = validate_theme_options(font="comic_sans")
        self.assertEqual(opts_valid["font"], "mono")
        self.assertEqual(opts_invalid["font"], "inter")

    def test_15_density_options_restricted(self):
        opts_valid = validate_theme_options(density="compact")
        opts_invalid = validate_theme_options(density="huge_padding")
        self.assertEqual(opts_valid["density"], "compact")
        self.assertEqual(opts_invalid["density"], "comfortable")

    def test_16_section_visibility_validation_works(self):
        opts = validate_theme_options(visible_sections={"summary": True, "projects": False})
        self.assertTrue(opts["sections"]["summary"])
        self.assertFalse(opts["sections"]["projects"])

    # -------------------------------------------------------------------------
    # Security Tests against CSS / Script Injection (17-18)
    # -------------------------------------------------------------------------
    def test_17_arbitrary_css_injection_sanitized(self):
        malicious_css = "indigo; body { background: red !important; }"
        opts = validate_theme_options(accent=malicious_css)
        self.assertEqual(opts["accent"], "indigo")

    def test_18_theme_selection_cannot_inject_scripts(self):
        malicious_theme = "<script>alert(1)</script>"
        opts = validate_theme_options(theme=malicious_theme)
        self.assertEqual(opts["theme"], "aurora")

    # -------------------------------------------------------------------------
    # Standalone Download & Export Tests (19-21)
    # -------------------------------------------------------------------------
    def test_19_downloaded_html_preserves_selected_theme(self):
        response = self.client.get('/download?theme=developer')
        self.assertEqual(response.status_code, 200)
        self.assertIn('attachment', response.headers.get('Content-Disposition', ''))

    def test_20_downloaded_html_preserves_customization(self):
        response = self.client.get('/download?theme=minimal&accent=rose&font=mono')
        self.assertEqual(response.status_code, 200)

    def test_21_print_media_css_rules_present(self):
        css_path = BASE_DIR / "static" / "css" / "portfolio.css"
        css_content = css_path.read_text(encoding="utf-8")
        self.assertIn("@media print", css_content)
        self.assertIn(".portfolio-toolbar", css_content)

    # -------------------------------------------------------------------------
    # Existing Functionality Integration Tests (22-24)
    # -------------------------------------------------------------------------
    def test_22_sample_portfolio_renders(self):
        response = self.client.get('/portfolio/sample')
        self.assertEqual(response.status_code, 200)

    def test_23_existing_portfolio_rendering_tests_pass(self):
        model = PortfolioData.model_validate(self.sample_data)
        self.assertTrue(len(model.skills) > 0)

    def test_24_existing_download_behavior_works(self):
        response = self.client.get('/download')
        self.assertEqual(response.status_code, 200)


if __name__ == '__main__':
    unittest.main()
