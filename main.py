"""
AI-Assisted Resume Portfolio Generator - CLI & Local Pipeline Runner.

Enables terminal-based portfolio generation directly from a resume file.
This is useful for:
  - Local testing without starting the Flask web server.
  - Automated batch generation.
  - Evaluator/grader verification.

Usage:
    python main.py                      # Uses resume.txt in current directory
    python main.py path/to/resume.txt   # Uses a specified file

Requirements:
    GEMINI_API_KEY must be set in the .env file (or environment).
    See .env.example for the required format.
"""

import sys
import logging
from pathlib import Path

# Ensure UTF-8 output on Windows consoles (emoji-safe logging)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from dotenv import load_dotenv

load_dotenv()

# Set up structured logging (file + console)
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",  # Keep output readable in terminal
)
logger = logging.getLogger(__name__)

from jinja2 import Environment, FileSystemLoader

from ai.validator import validate_resume_text
from ai.cleaner import clean_resume_text
from ai.gemini import extract_portfolio_from_resume, is_gemini_configured, get_model_name

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


def generate_from_file(
    resume_path: Path,
    output_path: Path = None,
) -> bool:
    """
    Full pipeline: read resume → validate → clean → Gemini → validate JSON
    → render HTML template → write output/portfolio.html.

    Returns True on success, False on any failure.
    """
    if output_path is None:
        output_path = OUTPUT_DIR / "portfolio.html"

    # ------------------------------------------------------------------
    print(f"[INFO] Reading resume from: {resume_path}")
    # ------------------------------------------------------------------
    if not resume_path.exists():
        print(f"[ERROR] Resume file not found: {resume_path}", file=sys.stderr)
        print(
            "       Please ensure resume.txt exists in the project root, "
            "or pass a file path as an argument.",
            file=sys.stderr,
        )
        return False

    try:
        resume_text = resume_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"[ERROR] Could not read resume file: {e}", file=sys.stderr)
        return False

    # ------------------------------------------------------------------
    print("[INFO] Validating resume content...")
    # ------------------------------------------------------------------
    is_valid, validation_msg = validate_resume_text(resume_text)
    if not is_valid:
        print(f"[ERROR] Resume validation failed: {validation_msg}", file=sys.stderr)
        return False

    # ------------------------------------------------------------------
    print("[INFO] Cleaning resume text...")
    # ------------------------------------------------------------------
    cleaned = clean_resume_text(resume_text)
    print(f"[INFO] Cleaned resume: {len(cleaned)} characters.")

    # ------------------------------------------------------------------
    print("[INFO] Checking Gemini API configuration...")
    # ------------------------------------------------------------------
    if not is_gemini_configured():
        print(
            "[ERROR] GEMINI_API_KEY is not configured.\n"
            "        Please set GEMINI_API_KEY in your .env file.\n"
            "        See .env.example for the required format.",
            file=sys.stderr,
        )
        print("\n[HINT] To configure your API key:")
        print("       1. Copy .env.example to .env")
        print("       2. Replace 'your_gemini_api_key_here' with your actual key")
        print("       3. Get a key from: https://aistudio.google.com/")
        return False

    print(f"[INFO] Using Gemini model: {get_model_name()}")

    # ------------------------------------------------------------------
    print("[INFO] Sending resume to Gemini API...")
    # ------------------------------------------------------------------
    success, portfolio_data, message = extract_portfolio_from_resume(
        resume_text,
        use_mock_if_unconfigured=False,  # CLI always requires a real key
    )

    if not success:
        print(f"[ERROR] Portfolio generation failed: {message}", file=sys.stderr)
        return False

    # ------------------------------------------------------------------
    print("[INFO] Rendering portfolio HTML template...")
    # ------------------------------------------------------------------
    try:
        env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
        # Provide a stub url_for for standalone rendering (no Flask context)
        env.globals["url_for"] = lambda endpoint, filename="": f"../static/{filename}"
        template = env.get_template("portfolio.html")
        rendered_html = template.render(data=portfolio_data)
    except Exception as e:
        print(f"[ERROR] Template rendering failed: {e}", file=sys.stderr)
        return False

    # ------------------------------------------------------------------
    print(f"[INFO] Writing output to: {output_path}")
    # ------------------------------------------------------------------
    try:
        output_path.write_text(rendered_html, encoding="utf-8")
    except Exception as e:
        print(f"[ERROR] Could not write output file: {e}", file=sys.stderr)
        return False

    print(f"[SUCCESS] Portfolio generated successfully at: {output_path}")
    print(f"[INFO] Name extracted: {portfolio_data.get('name', '(not found)')}")
    print(f"[INFO] Skills extracted: {len(portfolio_data.get('skills', []))}")
    print(f"[INFO] Projects extracted: {len(portfolio_data.get('projects', []))}")
    return True


if __name__ == "__main__":
    # Determine resume path from arguments or fall back to default
    if len(sys.argv) > 1:
        target_resume = Path(sys.argv[1])
    else:
        target_resume = BASE_DIR / "resume.txt"

    print("=" * 60)
    print("  AI Resume Portfolio Generator — CLI Mode")
    print("=" * 60)

    success = generate_from_file(target_resume)
    sys.exit(0 if success else 1)
