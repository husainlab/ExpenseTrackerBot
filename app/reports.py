
# app/reports.py
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"
IST = ZoneInfo("Asia/Kolkata")

def _read_user_month_dir(user_dir: Path, mkey: str) -> pd.DataFrame:
    month_dir = user_dir / mkey
    dfs = []
    if month_dir.exists():
        for xlsx in sorted(month_dir.glob("wk_*.xlsx")):
            try:
                df = pd.read_excel(xlsx, engine="openpyxl")
                if not df.empty:
                    dt = pd.to_datetime(df["date_ist"], errors="coerce")
                    if dt.dt.tz is None:
                        dt = dt.dt.tz_localize(IST)
                    else:
                        dt = dt.dt.tz_convert(IST)
                    df["date_ist"] = dt
                    dfs.append(df[["date_ist", "amount", "category"]])
            except Exception:
                pass
    if dfs:
        return pd.concat(dfs, ignore_index=True)
    return pd.DataFrame(columns=["date_ist", "amount", "category"])

def load_expenses_between(user_key: str, start: datetime, end: datetime) -> pd.DataFrame:
    user_dir = DATA_DIR / user_key
    if not user_dir.exists():
        return pd.DataFrame(columns=["date_ist", "amount", "category"])
    keys = {start.strftime("%Y_%m"), end.strftime("%Y_%m")}
    dfs = [_read_user_month_dir(user_dir, k) for k in keys]
    df = pd.concat([d for d in dfs if not d.empty], ignore_index=True) if any(not d.empty for d in dfs) else pd.DataFrame(columns=["date_ist","amount","category"])
    if df.empty:
        return df
    return df[(df["date_ist"] >= start) & (df["date_ist"] <= end)]
