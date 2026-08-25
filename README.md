# ⚡ NovaFolio AI — AI-Assisted Resume Portfolio Studio

A college group capstone project for the AIML bootcamp. This application automatically parses a student's resume (TXT or PDF), applies strict JSON schema validation via Google Gemini AI under zero-hallucination guardrails, and generates a modern, responsive developer portfolio website with 3 professional themes and appearance customizations.

---

## 🌟 Key Features

- **Dual Format Resume Input:** Supports plain text (`.txt`) and text-based Portable Document Format (`.pdf`) resumes up to 2MB.
- **3 Visual Portfolio Themes:** Includes **✨ Aurora** (Dark Glassmorphism), **📄 Minimal** (Clean Resume Light), and **💻 Developer** (Terminal Monospace).
- **Appearance Customization Drawer:** Live client-side customization of accent colors (Indigo, Cyan, Emerald, Amber, Rose), font families (Inter, Outfit, Monospace), layout density (Compact, Comfortable, Spacious), and section visibility toggles with zero Gemini API re-requests.
- **Strict Structured JSON Extraction:** Uses Google Gemini API (`gemini-3.6-flash`) with anti-hallucination guardrails.
- **Zero-Hallucination Policy:** Never invents unmentioned skills, companies, dates, projects, or URLs.
- **Interactive Builder Workspace:** File drag & drop, 2MB size enforcement, %PDF- signature verification, quick sample loader, character counter, disabled/loading CTA, and animated processing stepper.
- **Standalone HTML Export & Print PDF:** One-click download of clean standalone HTML files without builder toolbars, and print-ready PDF stylesheet rules (`@media print`).
- **Safe & Secure:** Zero API key exposure to frontend scripts; API calls happen strictly server-side.

---

## 🛠️ Technology Stack

- **Backend Web Server:** Python 3.10+, Flask
- **PDF Text Extraction:** `pypdf` (v4.2.0)
- **AI Integration:** Google Gemini API (`google-genai` SDK)
- **Validation & Schemas:** Python `pydantic` v2 & JSON schema normalization
- **Frontend:** Vanilla HTML5, CSS3 (Glassmorphism & CSS Custom Properties), Vanilla JavaScript (ES6+)
- **Testing Framework:** Python `unittest` (135 automated tests passing)

---

## 📂 Project Structure

```text
portfolio builder/
├── app.py                     # Flask web server and routing entry point
├── main.py                    # CLI / terminal portfolio generation runner
├── resume.txt                 # Safe sample student resume for testing
├── requirements.txt           # Python dependencies
├── .env.example               # Environment variables template
├── .gitignore                 # Git ignore configuration
├── README.md                  # Main project overview and setup guide
│
├── ai/                        # AI processing, extraction & validation layer
│   ├── __init__.py            # Package exports
│   ├── gemini.py              # Gemini API client & model configuration
│   ├── prompt.py              # Strict JSON schema & anti-hallucination prompt
│   ├── validator.py           # Content validation & safe sample data
│   ├── cleaner.py              # Resume text whitespace normaliser
│   ├── file_extractor.py      # Unified TXT & PDF text extractor via pypdf
│   ├── models.py              # Pydantic v2 PortfolioData schema
│   └── theme_validator.py     # Customization whitelist validator
│
├── templates/                 # Jinja2 HTML templates
│   ├── index.html             # Landing page with Theme Showcase
│   ├── builder.html           # Interactive builder workspace with 3-stage flow
│   └── portfolio.html         # Multi-theme portfolio renderer & control drawer
│
├── static/                    # Frontend static assets
│   ├── css/
│   │   ├── style.css          # Application design system & layout styles
│   │   └── portfolio.css      # Scoped multi-theme CSS (Aurora, Minimal, Developer)
│   └── js/
│       └── app.js             # Client controller (drag-drop, validation, stepper)
│
├── output/                    # Generated portfolio HTML destination
│   └── portfolio.html         # Standalone generated portfolio output
│
├── docs/                      # Comprehensive project documentation
│   ├── AI_USAGE_LOG.md        # Academic AI usage log
│   ├── ARCHITECTURE.md        # Architecture overview & data flows
│   ├── TESTING.md             # Test suite documentation & QA matrix
│   ├── DEMO_GUIDE.md          # 3-minute evaluator presentation script
│   └── FINAL_PROJECT_CHECKLIST.md # Definition of Done checklist
│
└── test_*.py                  # 7 automated test suites (135 tests)
```

---

## 🚀 Getting Started

### 1. Prerequisites
Ensure you have Python 3.10 or higher installed.

### 2. Install Dependencies
```bash
python -m pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Open `.env` and configure your Gemini API key:
```text
GEMINI_API_KEY=your_actual_gemini_api_key_here
GEMINI_MODEL=gemini-3.6-flash
```

### 4. Run the Web Application
```bash
python app.py
```
Navigate to: `http://127.0.0.1:5000`

### 5. Run CLI Generation
To test the pipeline directly in the terminal:
```bash
python main.py resume.txt
```

---

## 🧪 Testing

Run all 135 automated unit tests:

```bash
python -m unittest discover -p "test_*.py"
```

Current automated test baseline: **135/135 PASS (100%)**.

---

## 💡 Current Limitations & Future Improvements

- **Scanned / Image-Only PDFs:** Scanned image resumes without embedded font layers are detected and rejected with a friendly message (OCR is not implemented).
- **Future Improvements:** Saved portfolio user accounts, GitHub OAuth integration, cloud hosting deployment, and OCR support for scanned resumes.
