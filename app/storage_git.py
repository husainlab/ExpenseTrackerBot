
# app/storage_git.py
import os
import json
import subprocess
from pathlib import Path
import pandas as pd
from app.utils_time import now_ist, month_key, week_index_in_month

# Render checks out the repo under /opt/render/project/src
REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"

def current_users_count() -> int:
    if not DATA_DIR.exists():
        return 0
    return sum(1 for p in DATA_DIR.iterdir() if p.is_dir())

def ensure_user_dir(username: str, chat_id: int) -> bool:
    """
    Create user directory if needed.
    Enforce max 5 users: if creating a new user would exceed the cap, return False.
    """
    user_path = DATA_DIR / username
    if not user_path.exists() and current_users_count() >= 5:
        return False

    user_path.mkdir(parents=True, exist_ok=True)
    cfg = user_path / "config.json"
    if not cfg.exists():
        json.dump({"chat_id": chat_id, "budgets": {}}, cfg.open("w"))
    return True

def write_expense(username: str, amount: float, category: str):
    """
    Append one row {date_ist, amount, category} into the appropriate week file
    under data/<username>/<YYYY_MM>/wk_<1..5>.xlsx
    """
    ts = now_ist()
    mkey = month_key(ts)
    wk = week_index_in_month(ts)
    month_dir = DATA_DIR / username / mkey
    month_dir.mkdir(parents=True, exist_ok=True)

    xlsx = month_dir / f"wk_{wk}.xlsx"
    row = {
        "date_ist": ts.strftime("%Y-%m-%d %H:%M:%S"),
        "amount": amount,
        "category": category,
    }

    if xlsx.exists():
        df = pd.read_excel(xlsx, engine="openpyxl")
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    else:
        df = pd.DataFrame([row])

    df.to_excel(xlsx, index=False, engine="openpyxl")


def git_commit_push(message: str):
    """
    Commit and push changes back to GitHub using the PAT stored as Render secret.
    Handles cases where the repository has no 'origin' remote (detached HEAD).
    """
    pat = os.getenv("GITHUB_PAT")
    repo_url = os.getenv("REPO_URL")  # e.g., https://github.com/husainlab/ExpenseTrackerBot2.git
    if not pat or not repo_url:
        return  # silently skip if not configured

    # Minimal git identity
    subprocess.run(["git", "config", "user.email", "expensebot@local"], check=False)
    subprocess.run(["git", "config", "user.name", "ExpenseTrackerBot"], check=False)

    # Ensure we are inside a git work-tree
    inside = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"],
                            capture_output=True, text=True)
    if inside.returncode != 0 or inside.stdout.strip() != "true":
        # initialize a git repo if needed (rare on Render, but defensive)
        subprocess.run(["git", "init"], check=False)

    # Check if 'origin' exists
    origin_exists = subprocess.run(["git", "remote", "get-url", "origin"],
                                   capture_output=True, text=True)
    if origin_exists.returncode != 0:
        # Add origin if missing
        subprocess.run(["git", "remote", "add", "origin", repo_url], check=False)

    # Stage & commit just the data directory to keep noise low
    subprocess.run(["git", "add", "data"], check=False)
    # Allow commit to fail if nothing changed
    subprocess.run(["git", "commit", "-m", message], check=False)

    # Temporarily inject PAT for push
    secure_url = repo_url.replace("https://", f"https://{pat}@")
    subprocess.run(["git", "remote", "set-url", "origin", secure_url], check=False)

    # Determine default branch (‘main’ is most common)
    # Push HEAD to main; if your repo uses 'master', set REPO_BRANCH env var and use it here.
    branch = os.getenv("REPO_BRANCH", "main")
    # Create branch if detached
    subprocess.run(["git", "branch", "-f", branch, "HEAD"], check=False)

    # Push
    subprocess.run(["git", "push", "origin", f"{branch}:{branch}"], check=False)

    # Restore non-secret remote URL
    subprocess.run(["git", "remote", "set-url", "origin", repo_url], check=False)
