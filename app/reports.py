from pathlib import Path
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"

def load_expenses_between(user_id: str, start: datetime, end: datetime) -> pd.DataFrame:
    user_dir = DATA_DIR / user_id
    if not user_dir.exists():
        return pd.DataFrame()

    dfs = []
    for month in user_dir.iterdir():
        if month.is_dir():
            for xlsx in month.glob("wk_*.xlsx"):
                df = pd.read_excel(xlsx)
                if not df.empty:
                    dt = pd.to_datetime(df["date_ist"]).dt.tz_convert(IST)
                    df["date_ist"] = dt
                    dfs.append(df)

    if not dfs:
        return pd.DataFrame()

    df = pd.concat(dfs, ignore_index=True)
    return df[(df["date_ist"] >= start) & (df["date_ist"] <= end)]

def summarize_by_category(df: pd.DataFrame) -> str:
    if df.empty:
        return "_No expenses_"
    g = df.groupby("category")["amount"].sum().sort_values(ascending=False)
    return "\n".join(f"{k}: ₹{v:.0f}" for k, v in g.items())
