"""
HIRA Light – Shift-First Staffing Pipeline
- Consolidates staffing by SHIFT (not by hour)
- Uses Nash Analytics season mapping and user override
- Calculates Available FTEs (K–O) with multiple leaves supported
- Fixes type issues for Pylance (Series vs DataFrame, astype, to_numeric, etc.)
"""

from __future__ import annotations
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any, Union
from pandas._libs.tslibs.nattype import NaTType
# ----------------------------
# CONFIG / PATHS
# ----------------------------
WB_PATH = Path("/mnt/data/HIRA Light (IP) v0.12.xlsx")
OUTPUT_DIR = WB_PATH.parent
OUTPUT_XLSX = OUTPUT_DIR / "HIRA_Shift_Plan_Outputs.xlsx"

# ----------------------------
# UTILITIES
# ----------------------------

def _to_datetime(s: Any) -> pd.Timestamp | NaTType:
    return pd.to_datetime(s, errors="coerce")

def _hours_in_span(start_h: Any, end_h: Any) -> List[int]:
    """Return list of hours in a shift span, supports wrap-around."""
    try:
        s, e = int(float(start_h)), int(float(end_h))
    except (TypeError, ValueError):
        return []
    if s < e:
        return list(range(s, e))
    elif s > e:
        return list(range(s, 24)) + list(range(0, e))
    else:
        return list(range(0, 24))  # full day

# ----------------------------
# LOADERS
# ----------------------------

def pq_load_resource_input() -> pd.DataFrame:
    df = pd.read_excel(WB_PATH, sheet_name="Resource Input")
    df.columns = [str(c).strip() for c in df.columns]
    return df

def pq_load_shifts_input() -> pd.DataFrame:
    return pd.read_excel(WB_PATH, sheet_name="Shifts Input")

def pq_load_census_input() -> pd.DataFrame:
    df = pd.read_excel(WB_PATH, sheet_name="Census Input")
    df.columns = [str(c).strip() for c in df.columns]

    if "Unassigned_Date" in df.columns and "Date" not in df.columns:
        df.rename(columns={"Unassigned_Date": "Date"}, inplace=True)

    if "Projected_Census" in df.columns:
        df["Census"] = df["Projected_Census"]

    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    if "Hour" in df.columns:
        df["Hour"] = pd.to_numeric(df["Hour"], errors="coerce").astype("Int64")

    return df

def pq_load_nash_seasons() -> pd.DataFrame:
    df = pd.read_excel(WB_PATH, sheet_name="Nash Seasons Check")
    df.columns = [str(c).strip() for c in df.columns]
    return df

def pq_load_staffing_plan_meta() -> pd.DataFrame:
    return pd.read_excel(WB_PATH, sheet_name="Staffing Plan")

# ----------------------------
# SEASON HANDLING
# ----------------------------

def pq_extract_season_override(plan_meta: Union[pd.DataFrame, pd.Series]) -> Optional[str]:
    """
    Detect 'Recommended Season' from Staffing Plan sheet.
    Handles both Series (1D) and DataFrame (2D) cases.
    """

    # Case 1: Series (1D)
    if isinstance(plan_meta, pd.Series):
        mask_series: pd.Series = plan_meta.apply(
            lambda val: isinstance(val, str) and "Recommended Season" in val
        )
        if bool(mask_series.any()):  # force cast to bool
            idx = mask_series.index[mask_series.to_numpy()][0]
            try:
                return str(plan_meta.iloc[idx + 1])
            except Exception:
                return None
        return None

    # Case 2: DataFrame (2D)
    if isinstance(plan_meta, pd.DataFrame):
        mask_df: pd.DataFrame = plan_meta.astype(str).applymap(
            lambda val: "Recommended Season" in val
        )
        mask_np = mask_df.to_numpy()
        if mask_np.any():  # safe, numpy returns a bool
            r, c = np.argwhere(mask_np)[0]
            try:
                return str(plan_meta.iloc[r, c + 1])
            except Exception:
                return None
        return None

    return None


def pq_apply_nash_season(census: pd.DataFrame,
                         seasons_tbl: pd.DataFrame,
                         season_override: Optional[str]) -> pd.DataFrame:
    out = census.copy()
    if "Date" in out.columns:
        out["Month"] = out["Date"].dt.month
        out["DayOfWeek"] = out["Date"].dt.day_name()

    season_map = {}
    if "Month" in seasons_tbl.columns:
        for _, r in seasons_tbl.iterrows():
            m = str(r.get("Month", "")).strip()
            s = str(r.get("Nash Season", "")).strip()
            if m:
                season_map[m.lower()] = s

    def season_from_month(m: Any) -> Optional[str]:
        try:
            month_name = pd.Timestamp(year=2025, month=int(m), day=1).month_name()
            return season_map.get(month_name.lower())
        except Exception:
            return None

    if "Month" in out.columns:
        out["Nash_Season"] = out["Month"].apply(season_from_month)

    if season_override:
        out["Nash_Season"] = season_override.strip()

    return out

# ----------------------------
# SHIFT DEFINITIONS
# ----------------------------

def _safe_int(val: Any, default: int = 0) -> int:
    """Convert value to int safely, return default if None/NaN/invalid."""
    try:
        if pd.isna(val) or val is None:
            return default
        return int(float(val))
    except (TypeError, ValueError):
        return default


def pq_parse_shift_blocks(shifts_df: pd.DataFrame) -> Dict[str, List[Tuple[str, int, int]]]:
    df = shifts_df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    idx_weekday = df.index[df.iloc[:, 0].astype(str).str.contains("Weekday", na=False)]
    idx_weekend = df.index[df.iloc[:, 0].astype(str).str.contains("Weekend", na=False)]

    def collect_blocks(start_idx: int) -> List[Tuple[str, int, int]]:
        blocks: List[Tuple[str, int, int]] = []
        i = start_idx + 1
        # find header row
        while i < len(df) and "Shift Block" not in df.iloc[i, :].astype(str).tolist():
            i += 1
        i += 1  # first data row after headers
        while i < len(df):
            row = df.iloc[i, :]
            if pd.isna(row).all():
                break
            label = str(row.get("Label", "")).strip()
            start_h = _safe_int(row.get("Start Time"))
            end_h = _safe_int(row.get("End Time"))
            if start_h or end_h:  # only append if we got something valid
                blocks.append((label, start_h, end_h))
            i += 1
        return blocks

    return {
        "weekday": collect_blocks(int(idx_weekday[0])) if len(idx_weekday) else [],
        "weekend": collect_blocks(int(idx_weekend[0])) if len(idx_weekend) else [],
    }


# ----------------------------
# AVAILABLE FTEs
# ----------------------------

def pq_calc_available_ftes(resource_df: pd.DataFrame, planning_weeks:int=6) -> pd.DataFrame:
    df = resource_df.copy()

    last = df["Last Name"].fillna("").astype(str).str.strip()
    first = df["First Name"].fillna("").astype(str).str.strip()
    df["Person"] = last + ", " + first

    df["Unit FTEs"] = pd.to_numeric(df["Unit FTEs"], errors="coerce").fillna(0.0)
    df["Availibility"] = df["Availibility"].fillna("").astype(str).str.strip().str.title()
    df["Weekend"] = df["Weekend"].fillna("").astype(str).str.strip()

    leave_days_frac: List[float] = []
    for _, r in df.iterrows():
        ls, le = r.get("Leave Start"), r.get("Leave End")
        if pd.isna(ls) or pd.isna(le):
            leave_days_frac.append(0.0)
            continue
        ls, le = _to_datetime(ls), _to_datetime(le)
        if pd.isna(ls) or pd.isna(le) or le < ls:
            leave_days_frac.append(0.0)
        else:
            days = (le - ls).days + 1
            total_cycle_days = 7 * planning_weeks
            leave_days_frac.append(min(1.0, days / total_cycle_days))
    df["LeaveFrac"] = leave_days_frac

    agg = (df.groupby("Person")
             .agg(Unit_FTEs=("Unit FTEs","max"),
                  Availibility=("Availibility","last"),
                  Weekend=("Weekend","last"),
                  LeaveFrac=("LeaveFrac","sum"))
             .reset_index())
    agg["LeaveFrac"] = agg["LeaveFrac"].clip(0,1)
    agg["Available FTE"] = agg["Unit_FTEs"] * (1 - agg["LeaveFrac"])
    agg["Available FTE (Weekday)"] = agg["Available FTE"] * (5/7)
    agg["Available FTE (Weekend)"] = agg["Available FTE"] * (2/7)
    agg["FTE on Leave (Weekdays)"] = agg["Unit_FTEs"] * agg["LeaveFrac"] * (5/7)
    agg["FTE on Leave (Weekends)"] = agg["Unit_FTEs"] * agg["LeaveFrac"] * (2/7)

    return df.drop_duplicates("Person").merge(agg, on="Person", how="left")

# ----------------------------
# DEMAND TO SHIFTS
# ----------------------------

def pq_build_hourly_demand(census: pd.DataFrame,
                           ratio_per_census: Dict[str,float],
                           resource_type: str) -> pd.DataFrame:
    df = census.copy()
    ratio = ratio_per_census.get(resource_type)
    if not ratio or ratio <= 0:
        raise ValueError(f"No valid census ratio for {resource_type}")
    df["Hourly_FTE_Needed"] = df["Census"] / ratio
    return df

def pq_consolidate_to_shifts(hourly_need: pd.DataFrame,
                             shift_blocks: Dict[str, List[Tuple[str,int,int]]]) -> pd.DataFrame:
    df = hourly_need.copy()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["DayOfWeek"] = df["Date"].dt.day_name()
    df["IsWeekend"] = df["DayOfWeek"].isin(["Saturday","Sunday"])

    rows: List[dict[str,Any]] = []
    for _, r in df.iterrows():
        hr = int(r["Hour"]) if pd.notna(r["Hour"]) else None
        blocks = shift_blocks["weekend"] if bool(r["IsWeekend"]) else shift_blocks["weekday"]
        for label, s, e in blocks:
            if hr in _hours_in_span(s, e):
                rows.append({
                    "Date": r["Date"],
                    "DayOfWeek": r["DayOfWeek"],
                    "IsWeekend": r["IsWeekend"],
                    "ShiftLabel": label,
                    "ShiftStart": s,
                    "ShiftEnd": e,
                    "Hourly_FTE_Needed": float(r["Hourly_FTE_Needed"])
                })
                break
    return pd.DataFrame(rows).groupby(
        ["Date","DayOfWeek","IsWeekend","ShiftLabel","ShiftStart","ShiftEnd"], as_index=False
    ).sum()

# ----------------------------
# MAIN PIPELINE
# ----------------------------

def run_pipeline(resource_type: str = "RN",
                 ratio_per_census: Optional[Dict[str,float]] = None,
                 planning_weeks:int=6) -> Dict[str,pd.DataFrame]:

    if ratio_per_census is None:
        ratio_per_census = {"RN": 5.0, "NA": 8.0}

    res_in   = pq_load_resource_input()
    shifts   = pq_load_shifts_input()
    census   = pq_load_census_input()
    seasons  = pq_load_nash_seasons()
    planmeta = pq_load_staffing_plan_meta()

    season_override = pq_extract_season_override(planmeta)
    census2 = pq_apply_nash_season(census, seasons, season_override)

    res_ftes = pq_calc_available_ftes(res_in, planning_weeks=planning_weeks)
    shift_blocks = pq_parse_shift_blocks(shifts)
    hourly_need = pq_build_hourly_demand(census2, ratio_per_census, resource_type)
    need_by_shift = pq_consolidate_to_shifts(hourly_need, shift_blocks)

    outputs = {
        "Available_FTEs": res_ftes,
        "Shift_Need_By_Day": need_by_shift,
    }

    for name, df in outputs.items():
        df.to_csv(OUTPUT_DIR / f"{name}.csv", index=False)

    with pd.ExcelWriter(OUTPUT_XLSX, engine="xlsxwriter") as xw:
        for name, df in outputs.items():
            df.to_excel(xw, sheet_name=name[:31], index=False)

    return outputs

if __name__ == "__main__":
    run_pipeline("RN")
