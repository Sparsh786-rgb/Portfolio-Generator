#!/usr/bin/env python3
"""
Automated GitHub Push Tool using Dulwich (Pure Python Git).
Pushes the NovaFolio AI project directly to https://github.com/mrbharat007/Resume-Builder.git
"""

import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
REPO_URL = "https://github.com/mrbharat007/Resume-Builder.git"

def main():
    print("=" * 65)
    print("   NovaFolio AI — Direct GitHub Push Tool")
    print("=" * 65)
    print(f"Target Repository: {REPO_URL}")
    print("-" * 65)

    if len(sys.argv) > 1:
        token = sys.argv[1].strip()
    else:
        print("\nTo push to GitHub, enter your GitHub Personal Access Token (PAT):")
        print("Tip: Get a token from https://github.com/settings/tokens (classic token with 'repo' scope)")
        try:
            token = input("\nEnter GitHub Token (or press Enter to cancel): ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nCancelled.")
            sys.exit(0)

    if not token:
        print("\n[INFO] No token provided. You can upload files directly via:")
        print("👉 https://github.com/mrbharat007/Resume-Builder")
        sys.exit(0)

    try:
        from dulwich.repo import Repo
        from dulwich import porcelain

        print("\n[INFO] Preparing local Git repository...")
        git_dir = BASE_DIR / ".git"
        if not git_dir.exists():
            repo = Repo.init(str(BASE_DIR))
        else:
            repo = Repo(str(BASE_DIR))

        # Stage files (respecting .gitignore)
        print("[INFO] Staging project files...")
        porcelain.add(repo)

        # Commit
        print("[INFO] Creating commit...")
        try:
            porcelain.commit(
                repo,
                message=b"Deploy NovaFolio AI - Production Ready",
                author=b"Bharat <bharat@example.com>",
                committer=b"Bharat <bharat@example.com>"
            )
            print("[OK] Commit created successfully.")
        except Exception as e:
            print(f"[INFO] Commit status: {e}")

        # Push to remote with token
        auth_url = f"https://{token}@github.com/mrbharat007/Resume-Builder.git"
        print(f"[INFO] Pushing to {REPO_URL}...")
        porcelain.push(repo, auth_url, refspecs=[b"refs/heads/main:refs/heads/main"])
        print("\n" + "=" * 65)
        print("[SUCCESS] Project successfully pushed to GitHub!")
        print("View repository: https://github.com/mrbharat007/Resume-Builder")
        print("=" * 65)

    except Exception as e:
        print(f"\n[ERROR] Push encountered an issue: {e}")
        print("\n[ALTERNATIVE] You can also upload your files directly at:")
        print("👉 https://github.com/mrbharat007/Resume-Builder (Click 'uploading an existing file')")

if __name__ == "__main__":
    main()
