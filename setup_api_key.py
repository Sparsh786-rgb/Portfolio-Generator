#!/usr/bin/env python3
"""
Automated Gemini API Key Setup & Validation Tool.
Helps the user easily configure and test their Gemini API key in the .env file.
"""

import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"
ENV_EXAMPLE = BASE_DIR / ".env.example"

def get_input(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except (KeyboardInterrupt, EOFError):
        print("\n\nOperation cancelled.")
        sys.exit(0)

def update_env_file(api_key: str, model_name: str = "gemini-3.6-flash"):
    """Updates or creates the .env file with the provided API key and model."""
    env_content = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env_content[k.strip()] = v.strip()

    env_content["GEMINI_API_KEY"] = api_key
    env_content["GEMINI_MODEL"] = model_name
    if "FLASK_APP" not in env_content:
        env_content["FLASK_APP"] = "app.py"
    if "FLASK_ENV" not in env_content:
        env_content["FLASK_ENV"] = "development"
    if "FLASK_DEBUG" not in env_content:
        env_content["FLASK_DEBUG"] = "1"
    if "SECRET_KEY" not in env_content:
        env_content["SECRET_KEY"] = "college-project-secret-key-2026"
    if "PORT" not in env_content:
        env_content["PORT"] = "5000"

    lines = [
        "# ==========================================================================",
        "# Gemini AI Portfolio Generator - Environment Configuration",
        "# ==========================================================================",
        f"GEMINI_API_KEY={env_content['GEMINI_API_KEY']}",
        f"GEMINI_MODEL={env_content.get('GEMINI_MODEL', 'gemini-3.6-flash')}",
        "",
        "# Flask Application Settings",
        f"FLASK_APP={env_content.get('FLASK_APP', 'app.py')}",
        f"FLASK_ENV={env_content.get('FLASK_ENV', 'development')}",
        f"FLASK_DEBUG={env_content.get('FLASK_DEBUG', '1')}",
        f"SECRET_KEY={env_content.get('SECRET_KEY', 'college-project-secret-key-2026')}",
        f"PORT={env_content.get('PORT', '5000')}",
        ""
    ]

    ENV_FILE.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n[OK] Configuration successfully saved to: {ENV_FILE}")

def test_api_key(api_key: str, model_name: str = "gemini-3.6-flash"):
    """Tests the Gemini API key with a quick test prompt."""
    print(f"\n[INFO] Validating API key with model '{model_name}'...")
    try:
        import google.genai as genai
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model_name,
            contents="Say 'API Connected Successfully!' in 4 words."
        )
        output = response.text if hasattr(response, 'text') else str(response)
        print(f"[SUCCESS] Gemini API Response: {output.strip()}")
        print("[SUCCESS] Your API key is 100% verified and active!")
        return True
    except Exception as e:
        print(f"[WARN] Test request encountered an issue: {e}")
        print("[NOTE] Key was saved to .env, but please check if your key or quota is valid.")
        return False

def main():
    print("=" * 65)
    print("   PortfolioCraft AI - Gemini API Key Configuration Tool")
    print("=" * 65)
    print("Get your free Gemini API key from: https://aistudio.google.com/")
    print("-" * 65)

    if len(sys.argv) > 1:
        api_key = sys.argv[1].strip()
        model_name = sys.argv[2].strip() if len(sys.argv) > 2 else "gemini-3.6-flash"
    else:
        api_key = get_input("Enter your GEMINI_API_KEY: ")
        if not api_key:
            print("[ERROR] No API key entered. Exiting.")
            sys.exit(1)

        print("\nSelect Gemini Model:")
        print("  1. gemini-3.6-flash (Recommended - Latest & Fast)")
        print("  2. gemini-2.5-flash (Standard Stable)")
        print("  3. gemini-2.0-flash (Next Gen)")
        print("  4. gemini-1.5-flash (Legacy)")
        model_choice = get_input("Choose model [1-4, Default=1]: ")
        model_map = {
            "1": "gemini-3.6-flash",
            "2": "gemini-2.5-flash",
            "3": "gemini-2.0-flash",
            "4": "gemini-1.5-flash"
        }
        model_name = model_map.get(model_choice, "gemini-3.6-flash")

    update_env_file(api_key, model_name)
    test_api_key(api_key, model_name)

    print("\n[READY] You can now start the application with: python app.py")
    print("=" * 65)

if __name__ == "__main__":
    main()
