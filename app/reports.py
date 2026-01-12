
# app/reports.py
from __future__ import annotations
from pathlib import Path
from datetime import datetime
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"

def _read_user_month_dir(user_dir: Path, mkey: str) -> pd.DataFrame:
    month_dir = user_dir / mkey
    dfs = []
    if month_dir.exists():
        for xlsx in sorted(month_dir.glob("wk_*.xlsx")):
            try:
                df = pd.read_excel(xlsx, engine="openpyxl")
                if not df.empty:
                    df["date_ist"] = pd.to_datetime(df["date_ist"])
                    dfs.append(df)
            except Exception:
                # skip corrupt files silently
                pass
    if dfs:
        return pd.concat(dfs, ignore_index=True)
    return pd.DataFrame(columns=["date_ist", "amount", "category"])

def load_expenses_between(username: str, start: datetime, end: datetime) -> pd.DataFrame:
    """
    Load all expenses for username in [start, end] (inclusive), scanning relevant month folders.
    """
    user_dir = DATA_DIR / username
    if not user_dir.exists():
        return pd.DataFrame(columns=["date_ist", "amount", "category"])

    # scan months around the range (start..end)
    keys = {start.strftime("%Y_%m"), end.strftime("%Y_%m")}
    dfs = [ _read_user_month_dir(user_dir, k) for k in keys ]
    df = pd.concat([d for d in dfs if not d.empty], ignore_index=True) if any(not d.empty for d in dfs) else pd.DataFrame(columns=["date_ist","amount","category"])
    if df.empty:
        return df
    return df[(df["date_ist"] >= start) & (df["date_ist"] <= end)]

def summarize_by_category(df: pd.DataFrame) -> str:
    if df.empty:
        return "No expenses for the selected period."
    totals = df.groupby("category")["amount"].sum().sort_values(ascending=False)
    lines = ["*Summary (₹ per category)*"]
    for cat, amt in totals.items():
        lines.append(f"- {cat}: ₹{amt:.2f}")
    return "\n".join(lines)
