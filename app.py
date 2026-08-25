"""
AI-Assisted Resume Portfolio Generator
Flask Web Application Entry Point
"""

import os
import logging
from pathlib import Path
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from dotenv import load_dotenv

from ai.validator import validate_resume_text, get_sample_portfolio_data
from ai.gemini import extract_portfolio_from_resume, is_gemini_configured, get_model_name
from ai.cleaner import clean_resume_text

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

app = Flask(
    __name__,
    static_folder=str(BASE_DIR / "static"),
    template_folder=str(BASE_DIR / "templates"),
    static_url_path="/static"
)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "college-project-dev-key-12345")


@app.route("/")
def index():
    """
    Landing Page Route.
    """
    return render_template("index.html")


@app.route("/builder")
def builder():
    """
    Resume Builder Workspace Route.
    """
    return render_template("builder.html", error=None, info=None, resume_text="")


@app.route("/api/sample-resume")
def sample_resume():
    """
    API endpoint returning safe sample resume text for instant testing.
    """
    sample_path = BASE_DIR / "resume.txt"
    if sample_path.exists():
        content = sample_path.read_text(encoding="utf-8")
        return jsonify({"success": True, "content": content})
    return jsonify({"success": False, "content": "", "error": "Sample resume file not found."}), 404


@app.route("/portfolio/sample")
def portfolio_sample():
    """
    Renders sample portfolio template directly with verified foundation data.
    Supports optional query parameters: theme, accent, font, density.
    """
    from ai.theme_validator import validate_theme_options
    theme = request.args.get("theme")
    accent = request.args.get("accent")
    font = request.args.get("font")
    density = request.args.get("density")

    opts = validate_theme_options(theme, accent, font, density)
    sample_data = get_sample_portfolio_data()
    return render_template(
        "portfolio.html",
        data=sample_data,
        theme=opts["theme"],
        accent=opts["accent"],
        font=opts["font"],
        density=opts["density"]
    )


@app.route("/generate", methods=["POST"])
def generate():
    """
    Full pipeline route:
      1. Receive resume input (file upload or form text).
      2. If file uploaded, extract text securely (handles TXT and PDF formats, size check, pypdf extraction).
      3. Validate length and content.
      4. Clean whitespace / normalise formatting.
      5. Send to Gemini API for structured JSON extraction.
      6. Validate the returned JSON against the Pydantic schema.
      7. Validate theme customization parameters.
      8. Render and save the portfolio HTML.
    """
    from ai.file_extractor import extract_text_from_file
    from ai.theme_validator import validate_theme_options

    uploaded_file = request.files.get("resume_file")
    resume_text = ""

    if uploaded_file and uploaded_file.filename and uploaded_file.filename.strip():
        filename = uploaded_file.filename
        file_bytes = uploaded_file.read()

        logger.info("[INFO] Uploaded file received: %s (%d bytes)", filename, len(file_bytes))
        success, text_or_err = extract_text_from_file(file_bytes, filename)
        if not success:
            logger.warning("[VALIDATION] File extraction failed: %s", text_or_err)
            return render_template(
                "builder.html",
                error=text_or_err,
                resume_text=""
            ), 400
        resume_text = text_or_err
    else:
        resume_text = request.form.get("resume_text", "").strip()

    # Step 1: Input Validation
    logger.info("[INFO] Validating resume input...")
    is_valid, validation_msg = validate_resume_text(resume_text)
    if not is_valid:
        return render_template(
            "builder.html",
            error=validation_msg,
            resume_text=resume_text
        ), 400

    # Step 2: Clean the resume text (preprocessing before Gemini)
    logger.info("[INFO] Cleaning resume text...")
    cleaned_text = clean_resume_text(resume_text)

    # Step 3: AI Extraction & Pydantic Validation
    logger.info("[INFO] Sending to Gemini API...")
    success, portfolio_data, message = extract_portfolio_from_resume(cleaned_text)
    if not success:
        logger.error("[ERROR] Extraction failed: %s", message)
        return render_template(
            "builder.html",
            error=f"Portfolio Generation Error: {message}",
            resume_text=resume_text
        ), 500

    # Step 4: Validate Theme Parameters
    theme_param = request.form.get("theme") or request.args.get("theme")
    accent_param = request.form.get("accent") or request.args.get("accent")
    font_param = request.form.get("font") or request.args.get("font")
    density_param = request.form.get("density") or request.args.get("density")
    opts = validate_theme_options(theme_param, accent_param, font_param, density_param)

    logger.info("[SUCCESS] Portfolio data validated. Rendering template with theme: %s", opts["theme"])

    # Step 5: Persist output/portfolio.html to disk (background save)
    try:
        rendered_html = render_template(
            "portfolio.html",
            data=portfolio_data,
            theme=opts["theme"],
            accent=opts["accent"],
            font=opts["font"],
            density=opts["density"]
        )
        output_file = OUTPUT_DIR / "portfolio.html"
        output_file.write_text(rendered_html, encoding="utf-8")
        logger.info("[INFO] Portfolio saved to %s", output_file)
    except Exception as e:
        logger.warning("[WARN] Could not persist output/portfolio.html: %s", str(e))

    return render_template(
        "portfolio.html",
        data=portfolio_data,
        theme=opts["theme"],
        accent=opts["accent"],
        font=opts["font"],
        density=opts["density"]
    )


@app.route("/download")
def download():
    """
    Downloads the generated output/portfolio.html file.
    Optionally re-renders with selected theme/accent/font/density query params if provided.
    """
    from flask import send_from_directory
    from ai.theme_validator import validate_theme_options

    theme_param = request.args.get("theme")
    accent_param = request.args.get("accent")
    font_param = request.args.get("font")
    density_param = request.args.get("density")

    opts = validate_theme_options(theme_param, accent_param, font_param, density_param)
    output_file = OUTPUT_DIR / "portfolio.html"

    if not output_file.exists() or theme_param or accent_param or font_param or density_param:
        sample_data = get_sample_portfolio_data()
        rendered_html = render_template(
            "portfolio.html",
            data=sample_data,
            theme=opts["theme"],
            accent=opts["accent"],
            font=opts["font"],
            density=opts["density"]
        )
        output_file.write_text(rendered_html, encoding="utf-8")

    return send_from_directory(
        directory=str(OUTPUT_DIR),
        path="portfolio.html",
        as_attachment=True,
        download_name="portfolio.html"
    )


@app.route("/api/health")
def health():
    """
    API Health Check & Configuration Status.
    """
    return jsonify({
        "status": "healthy",
        "gemini_configured": is_gemini_configured(),
        "gemini_model": get_model_name(),
        "version": "1.0.0"
    })


@app.errorhandler(404)
def not_found(e):
    """
    Friendly 404 error page handler.
    """
    return render_template(
        "builder.html",
        error="The requested page was not found (404).",
        resume_text=""
    ), 404


@app.errorhandler(500)
def server_error(e):
    """
    Friendly 500 error handler to prevent exposing raw stack traces to users.
    """
    return render_template(
        "builder.html",
        error="An internal server error occurred while processing your request. Please try again.",
        resume_text=""
    ), 500


if __name__ == "__main__":
    import sys
    if sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "True").lower() in ("true", "1", "yes")
    print(f"[*] AI Resume Portfolio Generator starting at http://127.0.0.1:{port}")
    app.run(host="0.0.0.0", port=port, debug=debug)
