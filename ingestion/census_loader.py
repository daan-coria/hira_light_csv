from __future__ import annotations
import pandas as pd

REQUIRED = {"date", "hour", "census"}

def load_census_minimal(excel_path: str, sheet_name: str = "Census Input") -> pd.DataFrame:
    """
    Read only the external census source with these required columns:
      - Date (date or datetime)
      - Hour (0..23)
      - Census (float/int)
    Output columns: Date (date), Hour (int), Census (float)
    """
    raw = pd.read_excel(excel_path, sheet_name=sheet_name)
    cols = {c.strip().lower(): c for c in raw.columns}
    missing = [c for c in REQUIRED if c not in cols]
    if missing:
        raise ValueError(f"Census sheet must contain {sorted(REQUIRED)}. Found: {list(raw.columns)}")

    df = raw[[cols["date"], cols["hour"], cols["census"]]].copy()
    df.columns = ["Date", "Hour", "Census"]

    df["Date"]   = pd.to_datetime(df["Date"], errors="coerce").dt.date
    df["Hour"]   = pd.to_numeric(df["Hour"], errors="coerce").astype("Int64")
    df["Census"] = pd.to_numeric(df["Census"], errors="coerce")
    df = df.dropna(subset=["Date", "Hour", "Census"]).reset_index(drop=True)

    # Keep 0..23 only
    df = df[(df["Hour"] >= 0) & (df["Hour"] <= 23)].reset_index(drop=True)
    return df
