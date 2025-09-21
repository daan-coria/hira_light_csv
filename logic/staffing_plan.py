from __future__ import annotations
import math
import pandas as pd

SEASON_KEYS = {"High": "Ratio_High", "Medium": "Ratio_Medium", "Low": "Ratio_Low"}

def _ceil_div(census: float, ratio: float) -> int:
    if pd.isna(census) or pd.isna(ratio) or ratio <= 0:
        return 0
    return int(math.ceil(float(census) / float(ratio)))

def build_staffing_plan(
    census_df: pd.DataFrame,
    grid_df: pd.DataFrame,
    season: str = "Medium",
) -> pd.DataFrame:
    """
    Build staffing plan:
      Inputs: Census (Date, Hour, Census) + Staffing Grid (Dept/Role/Shift + season ratios).
      Season is selected manually and chooses which ratio column to use.
    Output: Date, Hour, Department, Role, Shift, Census, RatioUsed, Staff_Needed
    """
    season = str(season).title()
    if season not in SEASON_KEYS:
        raise ValueError(f"Season must be one of {list(SEASON_KEYS)}.")
    ratio_col = SEASON_KEYS[season]
    if ratio_col not in grid_df.columns:
        raise ValueError(f"Staffing Grid missing {ratio_col}")

    # cartesian product: (Date,Hour,Census) × (Dept,Role,Shift)
    census_df = census_df[["Date", "Hour", "Census"]].copy()
    rules = grid_df[["Department", "Role", "Shift", ratio_col]].copy().rename(columns={ratio_col: "RatioUsed"})

    census_df["key"] = 1
    rules["key"] = 1
    merged = census_df.merge(rules, on="key", how="inner").drop(columns=["key"])

    merged["Staff_Needed"] = merged.apply(lambda r: _ceil_div(r["Census"], r["RatioUsed"]), axis=1)

    cols = ["Date", "Hour", "Department", "Role", "Shift", "Census", "RatioUsed", "Staff_Needed"]
    return merged[cols].sort_values(["Date", "Hour", "Department", "Role", "Shift"]).reset_index(drop=True)
