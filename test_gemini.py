"""
Phase 2 Test Suite — Gemini Integration, Pydantic Validation & Resume Pipeline.

All tests are fully deterministic: no real Gemini API calls are made.
The Gemini API is mocked at the _call_gemini_api level so that:
  - Tests run fast and offline.
  - Tests are reproducible in CI or any environment.

Run with:
    python test_gemini.py
    python -m unittest test_gemini.py
"""

import unittest
import json
from unittest.mock import patch, MagicMock

from ai.validator import validate_resume_text, clean_raw_json_response, normalize_portfolio_data
from ai.cleaner import clean_resume_text
from ai.prompt import get_extraction_prompt, PORTFOLIO_JSON_SCHEMA
from ai.models import (
    PortfolioData,
    EducationEntry,
    ExperienceEntry,
    ProjectEntry,
    AchievementEntry,
    ContactInfo,
)
from ai.gemini import (
    extract_portfolio_from_resume,
    is_gemini_configured,
    _parse_and_validate_response,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

# A minimal but sufficient resume text used across multiple tests
VALID_RESUME = (
    "Jane Smith\n"
    "Full Stack Developer | Python & React\n"
    "Email: jane.smith@example.com | Phone: +1-555-100-2000\n"
    "GitHub: https://github.com/janesmith | LinkedIn: https://linkedin.com/in/janesmith\n\n"
    "PROFESSIONAL SUMMARY\n"
    "Experienced software developer with 3 years building scalable web applications.\n\n"
    "SKILLS\n"
    "Python, React, TypeScript, PostgreSQL, Docker, Git\n\n"
    "EDUCATION\n"
    "B.Sc. Computer Science, MIT, 2021\n\n"
    "EXPERIENCE\n"
    "Software Engineer, Tech Corp, Jan 2022 - Present\n"
    "- Built RESTful APIs with Python and FastAPI.\n"
    "- Led frontend migration to React.\n\n"
    "PROJECTS\n"
    "OpenTrack: Open-source project tracker. "
    "GitHub: https://github.com/janesmith/opentrack\n\n"
    "ACHIEVEMENTS\n"
    "Hackathon Winner - HackMIT 2021"
)

# Realistic Gemini JSON response based on VALID_RESUME above
MOCK_GEMINI_JSON = {
    "name": "Jane Smith",
    "headline": "Full Stack Developer | Python & React",
    "summary": (
        "Experienced software developer with 3 years building scalable web applications "
        "using Python, React, and TypeScript."
    ),
    "skills": ["Python", "React", "TypeScript", "PostgreSQL", "Docker", "Git"],
    "education": [
        {
            "degree": "B.Sc. Computer Science",
            "institution": "MIT",
            "location": "",
            "start_date": "",
            "end_date": "2021",
            "description": ""
        }
    ],
    "experience": [
        {
            "company": "Tech Corp",
            "role": "Software Engineer",
            "location": "",
            "start_date": "Jan 2022",
            "end_date": "Present",
            "description": "",
            "responsibilities": [
                "Built RESTful APIs with Python and FastAPI.",
                "Led frontend migration to React."
            ]
        }
    ],
    "projects": [
        {
            "title": "OpenTrack",
            "description": "Open-source project tracker.",
            "technologies": [],
            "github": "https://github.com/janesmith/opentrack",
            "live_link": ""
        }
    ],
    "achievements": [
        {
            "title": "Hackathon Winner - HackMIT 2021",
            "description": "",
            "date": "2021"
        }
    ],
    "contact": {
        "email": "jane.smith@example.com",
        "phone": "+1-555-100-2000",
        "linkedin": "https://linkedin.com/in/janesmith",
        "github": "https://github.com/janesmith",
        "location": "",
        "other_links": []
    }
}


# ---------------------------------------------------------------------------
# 1. Resume Validation Tests
# ---------------------------------------------------------------------------

class TestResumeValidation(unittest.TestCase):
    """Tests for ai/validator.py — validate_resume_text()"""

    def test_empty_string_rejected(self):
        ok, msg = validate_resume_text("")
        self.assertFalse(ok)
        self.assertIn("empty", msg.lower())

    def test_none_string_rejected(self):
        # Passing None should be treated as empty
        ok, msg = validate_resume_text(None)
        self.assertFalse(ok)

    def test_whitespace_only_rejected(self):
        ok, msg = validate_resume_text("    \n\n  ")
        self.assertFalse(ok)
        # Whitespace-only text strips to 0 chars → reported as "too short (0 characters)"
        self.assertTrue(
            "empty" in msg.lower() or "too short" in msg.lower(),
            f"Unexpected message: {msg}"
        )

    def test_too_short_rejected(self):
        ok, msg = validate_resume_text("Too short")
        self.assertFalse(ok)
        self.assertIn("too short", msg.lower())

    def test_exactly_at_minimum_length_accepted(self):
        text = "A" * 50
        ok, msg = validate_resume_text(text)
        self.assertTrue(ok)

    def test_valid_resume_accepted(self):
        ok, msg = validate_resume_text(VALID_RESUME)
        self.assertTrue(ok)

    def test_too_long_rejected(self):
        # 50001 characters should be rejected
        text = "A" * 50001
        ok, msg = validate_resume_text(text)
        self.assertFalse(ok)
        self.assertIn("maximum", msg.lower())


# ---------------------------------------------------------------------------
# 2. Resume Cleaning Tests
# ---------------------------------------------------------------------------

class TestResumeCleaning(unittest.TestCase):
    """Tests for ai/cleaner.py — clean_resume_text()"""

    def test_empty_returns_empty(self):
        self.assertEqual(clean_resume_text(""), "")
        self.assertEqual(clean_resume_text(None), "")

    def test_strips_leading_trailing_whitespace(self):
        result = clean_resume_text("  \nJohn Doe\n  ")
        self.assertEqual(result, "John Doe")

    def test_collapses_multiple_blank_lines(self):
        text = "Section A\n\n\n\n\nSection B"
        result = clean_resume_text(text)
        # Should have at most one blank line between sections
        self.assertNotIn("\n\n\n", result)

    def test_preserves_single_blank_lines(self):
        text = "Section A\n\nSection B"
        result = clean_resume_text(text)
        self.assertIn("\n\n", result)

    def test_collapses_multiple_internal_spaces(self):
        text = "Python    Flask    Django"
        result = clean_resume_text(text)
        self.assertNotIn("    ", result)
        self.assertIn("Python Flask Django", result)

    def test_preserves_urls_intact(self):
        url = "https://github.com/user/repo"
        text = f"GitHub: {url}"
        result = clean_resume_text(text)
        self.assertIn(url, result)

    def test_preserves_email_intact(self):
        email = "user@example.com"
        text = f"Email: {email}"
        result = clean_resume_text(text)
        self.assertIn(email, result)

    def test_windows_line_endings_normalised(self):
        text = "Line1\r\nLine2\r\nLine3"
        result = clean_resume_text(text)
        self.assertNotIn("\r", result)

    def test_realistic_resume_unchanged_content(self):
        # The cleaner must not remove any factual content
        result = clean_resume_text(VALID_RESUME)
        self.assertIn("Jane Smith", result)
        self.assertIn("jane.smith@example.com", result)
        self.assertIn("https://github.com/janesmith", result)
        self.assertIn("MIT", result)


# ---------------------------------------------------------------------------
# 3. JSON Cleaning & Parsing Tests
# ---------------------------------------------------------------------------

class TestJsonParsing(unittest.TestCase):
    """Tests for clean_raw_json_response and validate_portfolio_json."""

    def test_strips_markdown_code_fence(self):
        raw = "```json\n{\"name\": \"Jane\"}\n```"
        cleaned = clean_raw_json_response(raw)
        self.assertEqual(cleaned, '{"name": "Jane"}')

    def test_strips_bare_code_fence(self):
        raw = "```\n{\"name\": \"Jane\"}\n```"
        cleaned = clean_raw_json_response(raw)
        self.assertIn('"name"', cleaned)

    def test_extracts_json_from_surrounding_text(self):
        raw = 'Here is the JSON: {"name": "Jane"} Thank you.'
        cleaned = clean_raw_json_response(raw)
        self.assertTrue(cleaned.startswith("{"))
        self.assertTrue(cleaned.endswith("}"))

    def test_empty_string_returns_empty(self):
        self.assertEqual(clean_raw_json_response(""), "")
        self.assertEqual(clean_raw_json_response(None), "")


# ---------------------------------------------------------------------------
# 4. Pydantic Model Tests
# ---------------------------------------------------------------------------

class TestPydanticModels(unittest.TestCase):
    """Tests for ai/models.py — Pydantic schema validation."""

    def test_full_valid_portfolio(self):
        portfolio = PortfolioData.model_validate(MOCK_GEMINI_JSON)
        self.assertEqual(portfolio.name, "Jane Smith")
        self.assertIn("Python", portfolio.skills)
        self.assertEqual(len(portfolio.education), 1)
        self.assertEqual(len(portfolio.experience), 1)
        self.assertEqual(len(portfolio.projects), 1)
        self.assertEqual(len(portfolio.achievements), 1)

    def test_missing_fields_default_to_empty(self):
        """A completely empty dict should produce a valid model with empty defaults."""
        portfolio = PortfolioData.model_validate({})
        self.assertEqual(portfolio.name, "")
        self.assertEqual(portfolio.skills, [])
        self.assertEqual(portfolio.education, [])
        self.assertEqual(portfolio.contact.email, "")

    def test_none_fields_coerced_to_empty(self):
        """None values for string fields must be coerced, not raise exceptions."""
        data = {
            "name": None,
            "headline": None,
            "summary": None,
            "skills": None,
            "education": None,
            "experience": None,
            "projects": None,
            "achievements": None,
            "contact": None,
        }
        portfolio = PortfolioData.model_validate(data)
        self.assertEqual(portfolio.name, "")
        self.assertEqual(portfolio.skills, [])
        self.assertIsInstance(portfolio.contact, ContactInfo)

    def test_to_template_dict_returns_clean_dict(self):
        portfolio = PortfolioData.model_validate(MOCK_GEMINI_JSON)
        d = portfolio.to_template_dict()
        self.assertIsInstance(d, dict)
        self.assertIn("name", d)
        self.assertIn("contact", d)
        # contact must be a dict, not a Pydantic model
        self.assertIsInstance(d["contact"], dict)

    def test_to_template_dict_filters_empty_skills(self):
        data = {**MOCK_GEMINI_JSON, "skills": ["Python", "", "  ", "React"]}
        portfolio = PortfolioData.model_validate(data)
        d = portfolio.to_template_dict()
        self.assertNotIn("", d["skills"])
        self.assertNotIn("  ", d["skills"])

    def test_education_entry_missing_fields(self):
        entry = EducationEntry.model_validate({"degree": "BSc"})
        self.assertEqual(entry.institution, "")
        self.assertEqual(entry.location, "")

    def test_experience_responsibilities_from_str(self):
        entry = ExperienceEntry.model_validate({
            "company": "Acme",
            "role": "Dev",
            "responsibilities": "Single item"
        })
        self.assertIsInstance(entry.responsibilities, list)
        self.assertEqual(entry.responsibilities[0], "Single item")

    def test_contact_other_links_from_str(self):
        contact = ContactInfo.model_validate({"other_links": "https://example.com"})
        self.assertIsInstance(contact.other_links, list)
        self.assertEqual(contact.other_links[0], "https://example.com")


# ---------------------------------------------------------------------------
# 5. Parse & Validate Response Tests
# ---------------------------------------------------------------------------

class TestParseAndValidateResponse(unittest.TestCase):
    """Tests for ai/gemini._parse_and_validate_response()"""

    def test_valid_json_succeeds(self):
        raw = json.dumps(MOCK_GEMINI_JSON)
        ok, data, err = _parse_and_validate_response(raw)
        self.assertTrue(ok)
        self.assertEqual(data["name"], "Jane Smith")
        self.assertEqual(err, "")

    def test_json_in_markdown_fence_succeeds(self):
        raw = "```json\n" + json.dumps(MOCK_GEMINI_JSON) + "\n```"
        ok, data, err = _parse_and_validate_response(raw)
        self.assertTrue(ok)
        self.assertIn("name", data)

    def test_invalid_json_syntax_fails(self):
        raw = '{"name": "Jane", "skills": [BROKEN]}'
        ok, data, err = _parse_and_validate_response(raw)
        self.assertFalse(ok)
        self.assertIn("invalid json", err.lower())

    def test_empty_string_fails(self):
        ok, data, err = _parse_and_validate_response("")
        self.assertFalse(ok)
        self.assertNotEqual(err, "")

    def test_non_object_json_fails(self):
        raw = '["not", "an", "object"]'
        ok, data, err = _parse_and_validate_response(raw)
        self.assertFalse(ok)

    def test_partial_json_accepted_with_defaults(self):
        """Partial JSON (missing fields) should succeed with Pydantic filling defaults."""
        partial = {"name": "Partial Person"}
        raw = json.dumps(partial)
        ok, data, err = _parse_and_validate_response(raw)
        self.assertTrue(ok)
        self.assertEqual(data["name"], "Partial Person")
        self.assertEqual(data["skills"], [])
        self.assertEqual(data["contact"]["email"], "")


# ---------------------------------------------------------------------------
# 6. Gemini Configuration Tests
# ---------------------------------------------------------------------------

class TestGeminiConfiguration(unittest.TestCase):
    """Tests for is_gemini_configured() and API key handling."""

    def test_no_api_key_returns_false(self):
        with patch.dict("os.environ", {"GEMINI_API_KEY": ""}, clear=False):
            self.assertFalse(is_gemini_configured())

    def test_placeholder_key_returns_false(self):
        with patch.dict("os.environ", {"GEMINI_API_KEY": "your_gemini_api_key_here"}, clear=False):
            self.assertFalse(is_gemini_configured())

    def test_real_key_returns_true(self):
        with patch.dict("os.environ", {"GEMINI_API_KEY": "AIzaFakeKeyForTesting123"}, clear=False):
            self.assertTrue(is_gemini_configured())

    def test_missing_api_key_with_mock_disabled(self):
        """When use_mock_if_unconfigured=False and no key, extraction should fail cleanly."""
        with patch.dict("os.environ", {"GEMINI_API_KEY": ""}, clear=False):
            ok, data, msg = extract_portfolio_from_resume(
                VALID_RESUME,
                use_mock_if_unconfigured=False
            )
        self.assertFalse(ok)
        self.assertIn("GEMINI_API_KEY", msg)
        self.assertEqual(data, {})

    def test_missing_api_key_with_mock_enabled_returns_sample(self):
        """When no key and use_mock_if_unconfigured=True, should return sample data."""
        with patch.dict("os.environ", {"GEMINI_API_KEY": ""}, clear=False):
            ok, data, msg = extract_portfolio_from_resume(
                VALID_RESUME,
                use_mock_if_unconfigured=True
            )
        self.assertTrue(ok)
        # Returns the sample portfolio (Alex R. Chen)
        self.assertNotEqual(data.get("name"), "")


# ---------------------------------------------------------------------------
# 7. Full Pipeline Tests (mocked Gemini API)
# ---------------------------------------------------------------------------

class TestFullPipelineMocked(unittest.TestCase):
    """
    End-to-end pipeline tests with a mocked Gemini API call.
    These tests verify the complete flow from resume text to portfolio dict
    without making real network requests.
    """

    def _mock_api_success(self, prompt):
        """Returns a successful Gemini API response with the mock JSON."""
        return True, json.dumps(MOCK_GEMINI_JSON), ""

    def _mock_api_empty_response(self, prompt):
        return False, "", "Gemini returned an empty response. Please try again."

    def _mock_api_invalid_json(self, prompt):
        return True, "not-valid-json-{{{", ""

    def _mock_api_network_error(self, prompt):
        return False, "", "Network error while contacting Gemini. Please check your internet connection."

    @patch("ai.gemini._call_gemini_api")
    @patch.dict("os.environ", {"GEMINI_API_KEY": "AIzaFakeKeyForTesting123"})
    def test_successful_extraction(self, mock_call):
        mock_call.side_effect = self._mock_api_success
        ok, data, msg = extract_portfolio_from_resume(VALID_RESUME, use_mock_if_unconfigured=False)
        self.assertTrue(ok)
        self.assertEqual(data["name"], "Jane Smith")
        self.assertIn("Python", data["skills"])
        self.assertEqual(len(data["experience"]), 1)
        self.assertEqual(data["experience"][0]["company"], "Tech Corp")
        self.assertEqual(data["contact"]["email"], "jane.smith@example.com")

    @patch("ai.gemini._call_gemini_api")
    @patch.dict("os.environ", {"GEMINI_API_KEY": "AIzaFakeKeyForTesting123"})
    def test_empty_resume_rejected_before_api_call(self, mock_call):
        """Empty resume should be rejected before ever calling the API."""
        ok, data, msg = extract_portfolio_from_resume("", use_mock_if_unconfigured=False)
        self.assertFalse(ok)
        mock_call.assert_not_called()  # API must NOT be called with invalid input

    @patch("ai.gemini._call_gemini_api")
    @patch.dict("os.environ", {"GEMINI_API_KEY": "AIzaFakeKeyForTesting123"})
    def test_short_resume_rejected_before_api_call(self, mock_call):
        """Short resume should be rejected before calling the API."""
        ok, data, msg = extract_portfolio_from_resume("Too short", use_mock_if_unconfigured=False)
        self.assertFalse(ok)
        mock_call.assert_not_called()

    @patch("ai.gemini._call_gemini_api")
    @patch.dict("os.environ", {"GEMINI_API_KEY": "AIzaFakeKeyForTesting123"})
    def test_empty_api_response_fails_gracefully(self, mock_call):
        mock_call.side_effect = self._mock_api_empty_response
        ok, data, msg = extract_portfolio_from_resume(VALID_RESUME, use_mock_if_unconfigured=False)
        self.assertFalse(ok)
        self.assertIn("empty", msg.lower())

    @patch("ai.gemini._call_gemini_api")
    @patch.dict("os.environ", {"GEMINI_API_KEY": "AIzaFakeKeyForTesting123"})
    def test_invalid_json_fails_gracefully(self, mock_call):
        mock_call.side_effect = self._mock_api_invalid_json
        ok, data, msg = extract_portfolio_from_resume(VALID_RESUME, use_mock_if_unconfigured=False)
        self.assertFalse(ok)
        self.assertIn("json", msg.lower())

    @patch("ai.gemini._call_gemini_api")
    @patch.dict("os.environ", {"GEMINI_API_KEY": "AIzaFakeKeyForTesting123"})
    def test_network_error_fails_gracefully(self, mock_call):
        mock_call.side_effect = self._mock_api_network_error
        ok, data, msg = extract_portfolio_from_resume(VALID_RESUME, use_mock_if_unconfigured=False)
        self.assertFalse(ok)
        self.assertIn("network", msg.lower())

    @patch("ai.gemini._call_gemini_api")
    @patch.dict("os.environ", {"GEMINI_API_KEY": "AIzaFakeKeyForTesting123"})
    def test_partial_json_response_accepted(self, mock_call):
        """A JSON response missing optional fields should still produce a portfolio."""
        partial_response = json.dumps({
            "name": "John Doe",
            "headline": "Developer",
            "summary": "A developer.",
            # All other fields intentionally missing
        })
        mock_call.return_value = (True, partial_response, "")
        ok, data, msg = extract_portfolio_from_resume(VALID_RESUME, use_mock_if_unconfigured=False)
        self.assertTrue(ok)
        self.assertEqual(data["name"], "John Doe")
        self.assertEqual(data["skills"], [])
        self.assertEqual(data["education"], [])

    @patch("ai.gemini._call_gemini_api")
    @patch.dict("os.environ", {"GEMINI_API_KEY": "AIzaFakeKeyForTesting123"})
    def test_none_fields_in_json_handled_safely(self, mock_call):
        """Gemini sometimes returns null (None) — must be coerced to safe defaults."""
        json_with_nulls = {
            "name": "Jane",
            "headline": None,
            "summary": None,
            "skills": None,
            "education": None,
            "experience": None,
            "projects": None,
            "achievements": None,
            "contact": None,
        }
        mock_call.return_value = (True, json.dumps(json_with_nulls), "")
        ok, data, msg = extract_portfolio_from_resume(VALID_RESUME, use_mock_if_unconfigured=False)
        self.assertTrue(ok)
        self.assertEqual(data["name"], "Jane")
        self.assertEqual(data["skills"], [])
        self.assertIsInstance(data["contact"], dict)


# ---------------------------------------------------------------------------
# 8. Flask Route Integration Tests (Phase 1 preserved)
# ---------------------------------------------------------------------------

class TestFlaskRoutes(unittest.TestCase):
    """Verify Phase 1 Flask routes still work correctly after Phase 2 changes."""

    def setUp(self):
        from app import app
        self.client = app.test_client()
        self.client.testing = True

    def test_landing_page(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"NovaFolio", r.data)

    def test_builder_page(self):
        r = self.client.get("/builder")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"Build Your", r.data)

    def test_sample_resume_api(self):
        r = self.client.get("/api/sample-resume")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertTrue(data["success"])

    def test_sample_portfolio_preview(self):
        r = self.client.get("/portfolio/sample")
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"Alex R. Chen", r.data)

    def test_health_check_includes_model(self):
        r = self.client.get("/api/health")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertEqual(data["status"], "healthy")
        self.assertIn("gemini_model", data)

    def test_generate_empty_resume_rejected(self):
        r = self.client.post("/generate", data={"resume_text": ""})
        self.assertEqual(r.status_code, 400)

    def test_generate_short_resume_rejected(self):
        r = self.client.post("/generate", data={"resume_text": "Too short"})
        self.assertEqual(r.status_code, 400)

    @patch("ai.gemini._call_gemini_api")
    @patch.dict("os.environ", {"GEMINI_API_KEY": "AIzaFakeKeyForTesting123"})
    def test_generate_with_mocked_gemini(self, mock_call):
        """Full Flask generate route with mocked Gemini API."""
        mock_call.return_value = (True, json.dumps(MOCK_GEMINI_JSON), "")
        r = self.client.post("/generate", data={"resume_text": VALID_RESUME})
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"Jane Smith", r.data)
        self.assertIn(b"Tech Corp", r.data)


if __name__ == "__main__":
    # Run with verbose output for clear per-test feedback
    unittest.main(verbosity=2)
