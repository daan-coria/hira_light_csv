"""
Excel loaders tailored for HIRA Light (IP) v0.12.

This version is simplified per new requirements:

- Census Input → only Date, Hour, Census
- Staffing Grid → all department/role/shift rules, ratios by season (High/Medium/Low)
- Shifts Input → optional table of shift definitions
- Resource Input → only A–G columns (core metadata for staff)

All other legacy loaders (RN-only, NA-only, ED-specific) removed.
"""

from typing import List, Optional
import pandas as pd
import numpy as np


# ========= Helpers =========

def _make_unique(names: List[str]) -> List[str]:
    """Make column names unique by appending '__N' to duplicates."""
    seen = {}
    out = []
    for n in names:
        n = "Unnamed" if n is None or str(n).lower() == "nan" else str(n)
        if n in seen:
            seen[n] += 1
            out.append(f"{n}__{seen[n]}")
        else:
            seen[n] = 0
            out.append(n)
    return out


# ========= Census Input =========

def load_census_from_excel(excel_path: str, sheet_name: str = "Census Input") -> pd.DataFrame:
    """
    Parses 'Census Input' with flexible header detection.
    Canonical output: Date (datetime64), Hour (int), Census (float)
    """
    raw = pd.read_excel(excel_path, sheet_name=sheet_name, header=None)

    header_row = None
    for i in range(min(10, raw.shape[0])):  # scan first 10 rows
        row_vals = [str(x).strip().lower() for x in raw.iloc[i].tolist() if pd.notna(x)]
        if any("census" in v for v in row_vals) and any("date" in v or "day" in v for v in row_vals):
            header_row = i
            break

    if header_row is None:
        raise ValueError("Could not detect header row in Census Input sheet")

    # Promote that row to header
    df = pd.read_excel(excel_path, sheet_name=sheet_name, header=header_row)

    # Normalize column names
    cols = {c.strip().lower().replace(" ", ""): c for c in df.columns if isinstance(c, str)}

    date_col = None
    for cand in ["date", "projecteddate", "day"]:
        if cand in cols:
            date_col = cols[cand]
            break

    hour_col = None
    for cand in ["hour", "time"]:
        if cand in cols:
            hour_col = cols[cand]
            break

    census_col = None
    for cand in ["census", "projectedcensus", "originaladtcensus"]:
        if cand in cols:
            census_col = cols[cand]
            break

    if not date_col or not census_col:
        raise ValueError(
            f"Census Input must contain Date and Census. Found: {list(df.columns)}"
        )

    # Extract relevant data
    keep = [c for c in [date_col, hour_col, census_col] if c is not None]
    df = df[keep].copy()

    # Rename to canonical
    rename_map = {}
    if date_col: rename_map[date_col] = "Date"
    if hour_col: rename_map[hour_col] = "Hour"
    if census_col: rename_map[census_col] = "Census"
    df = df.rename(columns=rename_map)

    # Coerce types
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    if "Hour" in df.columns:
        df["Hour"] = pd.to_numeric(df["Hour"], errors="coerce").fillna(0).astype(int)
    else:
        df["Hour"] = 0
    df["Census"] = pd.to_numeric(df["Census"], errors="coerce")

    # Drop blanks
    df = df.dropna(subset=["Date", "Census"]).reset_index(drop=True)

    return df[["Date", "Hour", "Census"]]


# ========= Resource Input (A–G only) =========

def load_resources_from_excel(excel_path: str, sheet_name: str = "Resource Input") -> pd.DataFrame:
    """
    Loads only the first A–G columns of Resource Input.
    Normalizes headers to:
      Department, Role, Name, FTE, Shift, Start, End
    """
    raw = pd.read_excel(excel_path, sheet_name=sheet_name, header=0, usecols="A:G")
    lower = {c.strip().lower(): c for c in raw.columns}

    dep_col  = next((lower[k] for k in ["department", "dept", "cost center"] if k in lower), None)
    role_col = next((lower[k] for k in ["role", "position", "job"] if k in lower), None)
    name_col = next((lower[k] for k in ["name", "employee", "staff"] if k in lower), None)
    fte_col  = next((lower[k] for k in ["fte", "ftes", "unit ftes"] if k in lower), None)
    shift_col= next((lower[k] for k in ["shift"] if k in lower), None)
    start_col= next((lower[k] for k in ["start", "start time"] if k in lower), None)
    end_col  = next((lower[k] for k in ["end", "end time"] if k in lower), None)

    df = pd.DataFrame()
    if dep_col:   df["Department"] = raw[dep_col]
    if role_col:  df["Role"]       = raw[role_col]
    if name_col:  df["Name"]       = raw[name_col]
    if fte_col:   df["FTE"]        = pd.to_numeric(raw[fte_col], errors="coerce")
    if shift_col: df["Shift"]      = raw[shift_col]
    if start_col: df["Start"]      = pd.to_numeric(raw[start_col], errors="coerce")
    if end_col:   df["End"]        = pd.to_numeric(raw[end_col], errors="coerce")

    return df.dropna(how="all").reset_index(drop=True)

def load_staffing_rules_from_excel(excel_path: str, sheet_name: str = "Staffing Grid") -> pd.DataFrame:
    """
    Parses Staffing Grid and extracts Department, Role, Shift and seasonal ratios.
    Expects columns like: Department, Role, Shift, Ratio_High, Ratio_Medium, Ratio_Low
    """
    raw = pd.read_excel(excel_path, sheet_name=sheet_name, header=0)

    # Clean column names
    raw.columns = [str(c).strip() for c in raw.columns]

    required = {"Department", "Role", "Shift", "Ratio_High", "Ratio_Medium", "Ratio_Low"}
    missing = required - set(raw.columns)
    if missing:
        raise ValueError(f"Staffing Grid missing required columns: {missing}")

    return raw[list(required)]

def load_shifts_from_excel(excel_path: str, sheet_name: str = "Shifts Input") -> pd.DataFrame:
    """
    Parses 'Shifts Input' into a clean DataFrame.
    Expected columns: Department, Role, Shift, Start, End, Hours
    """
    df = pd.read_excel(excel_path, sheet_name=sheet_name, header=0)

    # Clean column names
    df.columns = [str(c).strip() for c in df.columns]

    required = {"Department", "Role", "Shift", "Start", "End", "Hours"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Shifts Input missing required columns: {missing}")

    return df[list(required)]
