
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
    Safe approach:
      - set user.name/email
      - update remote URL to include PAT for this push (HTTPS)
      - push HEAD to the default branch
    """
    pat = os.getenv("GITHUB_PAT")
    repo_url = os.getenv("REPO_URL")  # e.g., https://github.com/husainlab/ExpenseTrackerBot2.git
    if not pat or not repo_url:
        return  # silently skip if not configured

    # minimal git identity
    subprocess.run(["git", "config", "user.email", "expensebot@local"], check=False)
    subprocess.run(["git", "config", "user.name", "ExpenseTrackerBot"], check=False)

    # add & commit
    subprocess.run(["git", "add", "data"], check=False)  # only data changes
    subprocess.run(["git", "commit", "-m", message], check=False)

    # inject PAT into remote URL (avoid printing PAT)
    secure_url = repo_url.replace("https://", f"https://{pat}@")
    subprocess.run(["git", "remote", "set-url", "origin", secure_url], check=False)

    # push HEAD (Render typically builds from main; HEAD push is fine)
    subprocess.run(["git", "push", "origin", "HEAD"], check=False)

    # restore origin to clean URL (optional)
    subprocess.run(["git", "remote", "set-url", "origin", repo_url], check=False)
