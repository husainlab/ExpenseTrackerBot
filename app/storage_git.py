
# app/storage_git.py
import os
import json
import subprocess
from pathlib import Path
import pandas as pd
from app.utils_time import now_ist, month_key, week_index_in_month

# Root paths
REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"

def current_users_count() -> int:
    if not DATA_DIR.exists():
        return 0
    return sum(1 for p in DATA_DIR.iterdir() if p.is_dir())

def migrate_username_dir_to_userkey(username: str, user_key: str):
    """If old username folder exists and user_key folder does not, move it."""
    old_dir = DATA_DIR / username
    new_dir = DATA_DIR / user_key
    if old_dir.exists() and not new_dir.exists():
        new_dir.parent.mkdir(parents=True, exist_ok=True)
        old_dir.rename(new_dir)

def ensure_user_dir(user_key: str, chat_id: int, username: str) -> bool:
    """
    Create user directory keyed by stable user_id (as string).
    Enforce max 5 users. Store chat_id + latest username in config.json.
    """
    # One-time migration: move any legacy username folder under user_key
    migrate_username_dir_to_userkey(username, user_key)

    user_path = DATA_DIR / user_key
    if not user_path.exists() and current_users_count() >= 5:
        return False

    user_path.mkdir(parents=True, exist_ok=True)
    cfg = user_path / "config.json"
    data = {"chat_id": chat_id, "username": username, "budgets": {}}
    try:
        if cfg.exists():
            # merge (preserve budgets)
            existing = json.load(cfg.open())
            existing.update({k: v for k, v in data.items() if k != "budgets"})
            data = {**existing, **{"budgets": existing.get("budgets", {})}}
        json.dump(data, cfg.open("w"))
    except Exception:
        # Don't fail the whole request if config write has an issue
        pass
    return True

def write_expense(user_key: str, amount: float, category: str):
    """
    Append one row {date_ist, amount, category} to data/<user_key>/<YYYY_MM>/wk_<1..5>.xlsx
    """
    ts = now_ist()
    mkey = month_key(ts)
    wk = week_index_in_month(ts)

    month_dir = DATA_DIR / user_key / mkey
    month_dir.mkdir(parents=True, exist_ok=True)

    xlsx = month_dir / f"wk_{wk}.xlsx"
    row = {
        "date_ist": ts.isoformat(),  # includes +05:30 offset for IST
        "amount": amount,
        "category": category,
    }

    try:
        if xlsx.exists():
            df = pd.read_excel(xlsx, engine="openpyxl")
            df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
        else:
            df = pd.DataFrame([row])
        df.to_excel(xlsx, index=False, engine="openpyxl")
    except Exception as e:
        # Surface a clear message in logs; handler will report failure to user
        print(f"[write_expense] Failed to write {xlsx}: {e}")
        raise

def git_commit_push(message: str):
    """
    Commit and push changes back to GitHub using PAT stored as Render secret.
    More resilient: add origin if missing, pull before push (avoid non-fast-forward).
    """
    pat = os.getenv("GITHUB_PAT")
    repo_url = os.getenv("REPO_URL")
    branch = os.getenv("REPO_BRANCH", "main")
    if not pat or not repo_url:
        return  # skip if not configured

    # identity
    subprocess.run(["git", "config", "user.email", "expensebot@local"], check=False)
    subprocess.run(["git", "config", "user.name", "ExpenseTrackerBot"], check=False)

    # ensure repo
    inside = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], capture_output=True, text=True)
    if inside.returncode != 0 or inside.stdout.strip() != "true":
        subprocess.run(["git", "init"], check=False)

    # origin remote
    origin_exists = subprocess.run(["git", "remote", "get-url", "origin"], capture_output=True, text=True)
    if origin_exists.returncode != 0:
        subprocess.run(["git", "remote", "add", "origin", repo_url], check=False)

    # stage & commit
    subprocess.run(["git", "add", "data"], check=False)
    subprocess.run(["git", "commit", "-m", message], check=False)

    # secure remote for push
    secure_url = repo_url.replace("https://", f"https://{pat}@")
    subprocess.run(["git", "remote", "set-url", "origin", secure_url], check=False)

    # sync then push (handles non-fast-forward)
    subprocess.run(["git", "fetch", "origin", branch], check=False)
    subprocess.run(["git", "rebase", f"origin/{branch}"], check=False)
    subprocess.run(["git", "push", "origin", branch], check=False)

    # restore clean URL
    subprocess.run(["git", "remote", "set-url", "origin", repo_url], check=False)
