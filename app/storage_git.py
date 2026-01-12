import os, json, subprocess
from pathlib import Path
import pandas as pd
from app.utils_time import now_ist, month_key, week_index_in_month

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"

def ensure_user_dir(user_id: str, chat_id: int, username: str) -> bool:
    DATA_DIR.mkdir(exist_ok=True)
    users = [p for p in DATA_DIR.iterdir() if p.is_dir() and p.name.isdigit()]
    if user_id not in [u.name for u in users] and len(users) >= 5:
        return False

    user_dir = DATA_DIR / user_id
    user_dir.mkdir(parents=True, exist_ok=True)
    cfg = user_dir / "config.json"

    data = {"chat_id": chat_id, "username": username, "budgets": {}}
    if cfg.exists():
        existing = json.loads(cfg.read_text())
        data["budgets"] = existing.get("budgets", {})
    cfg.write_text(json.dumps(data, indent=2))
    return True

def load_config(user_id: str) -> dict:
    cfg = DATA_DIR / user_id / "config.json"
    return json.loads(cfg.read_text())

def save_config(user_id: str, cfg: dict):
    path = DATA_DIR / user_id / "config.json"
    path.write_text(json.dumps(cfg, indent=2))

def write_expense(user_id: str, amount: float, category: str, note: str = ""):
    ts = now_ist()
    mkey = month_key(ts)
    wk = week_index_in_month(ts)

    month_dir = DATA_DIR / user_id / mkey
    month_dir.mkdir(parents=True, exist_ok=True)

    xlsx = month_dir / f"wk_{wk}.xlsx"
    row = {
        "date_ist": ts.isoformat(),
        "amount": amount,
        "category": category,
        "note": note,
    }

    if xlsx.exists():
        df = pd.read_excel(xlsx, engine="openpyxl")
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    else:
        df = pd.DataFrame([row])
    df.to_excel(xlsx, index=False, engine="openpyxl")

def delete_user_data(user_id: str):
    user_dir = DATA_DIR / user_id
    if user_dir.exists():
        for p in user_dir.rglob("*"):
            if p.is_file():
                p.unlink()
        for p in sorted(user_dir.glob("**/*"), reverse=True):
            if p.is_dir():
                p.rmdir()
        user_dir.rmdir()

def git_commit_push(message: str):
    pat = os.getenv("GITHUB_PAT")
    repo = os.getenv("REPO_URL")
    branch = os.getenv("REPO_BRANCH", "main")
    if not pat or not repo:
        return

    subprocess.run(["git", "checkout", "-B", branch], check=False)
    subprocess.run(["git", "add", "data"], check=False)
    subprocess.run(["git", "commit", "-m", message], check=False)

    secure = repo.replace("https://", f"https://{pat}@")
    subprocess.run(["git", "remote", "set-url", "origin", secure], check=False)
    subprocess.run(["git", "pull", "--rebase", "origin", branch], check=False)
    subprocess.run(["git", "push", "origin", branch], check=False)
    subprocess.run(["git", "remote", "set-url", "origin", repo], check=False)
