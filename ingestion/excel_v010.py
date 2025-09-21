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
    Parses 'Census Input'.
    Canonical output: Date (datetime64), Hour (int), Census (float)
    """
    raw = pd.read_excel(excel_path, sheet_name=sheet_name)

    # Normalize column names
    cols = {c.strip().lower().replace(" ", ""): c for c in raw.columns if isinstance(c, str)}

    # Detect date column
    date_col = None
    for cand in ["date", "projecteddate", "day"]:
        if cand in cols:
            date_col = cols[cand]
            break

    # Detect hour column
    hour_col = None
    for cand in ["hour", "time"]:
        if cand in cols:
            hour_col = cols[cand]
            break

    # Detect census column
    census_col = None
    for cand in ["census", "projectedcensus", "originaladtcensus"]:
        if cand in cols:
            census_col = cols[cand]
            break

    if not date_col or not census_col:
        raise ValueError(
            f"Census Input must contain Date and Census (optionally Hour). Found: {list(raw.columns)}"
        )

    # Extract relevant data
    df = raw[[c for c in [date_col, hour_col, census_col] if c is not None]].copy()

    # Rename to canonical
    rename_map = {}
    if date_col: rename_map[date_col] = "Date"
    if hour_col: rename_map[hour_col] = "Hour"
    if census_col: rename_map[census_col] = "Census"
    df = df.rename(columns=rename_map)

    # Clean types
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    if "Hour" in df.columns:
        df["Hour"] = pd.to_numeric(df["Hour"], errors="coerce").fillna(0).astype(int)
    else:
        df["Hour"] = 0  # fallback: single shift
    df["Census"] = pd.to_numeric(df["Census"], errors="coerce")

    # Drop invalid rows
    df = df.dropna(subset=["Date", "Census"]).reset_index(drop=True)

    return df[["Date", "Hour", "Census"]]


# ========= Staffing Grid =========

def load_staffing_rules_from_excel(excel_path: str, sheet_name: str = "Staffing Grid") -> pd.DataFrame:
    """
    Parses 'Staffing Grid' (blue tables).
    Expected columns (flexible names):
      Department | Role | Shift | Ratio (or Ratio_High/Medium/Low)

    Output columns:
      Department, Role, Shift, Ratio_High, Ratio_Medium, Ratio_Low
    """
    df = pd.read_excel(excel_path, sheet_name=sheet_name, header=0)
    lower = {c.strip().lower(): c for c in df.columns}

    dept_col  = next((lower[k] for k in ["department", "dept", "cost center", "costcenter"] if k in lower), None)
    role_col  = next((lower[k] for k in ["role", "position", "job", "jobtitle"] if k in lower), None)
    shift_col = next((lower[k] for k in ["shift", "shiftname"] if k in lower), None)

    ratio_high   = next((lower[k] for k in ["ratio_high", "high"] if k in lower), None)
    ratio_medium = next((lower[k] for k in ["ratio_medium", "medium"] if k in lower), None)
    ratio_low    = next((lower[k] for k in ["ratio_low", "low"] if k in lower), None)
    ratio_single = next((lower[k] for k in ["ratio", "staff ratio"] if k in lower), None)

    if not (dept_col and role_col and shift_col):
        raise ValueError("Staffing Grid must contain Department, Role, Shift and at least one ratio column.")

    out = pd.DataFrame({
        "Department": df[dept_col].astype(str).str.strip(),
        "Role":       df[role_col].astype(str).str.strip(),
        "Shift":      df[shift_col].astype(str).str.strip(),
    })

    def _num(x): return pd.to_numeric(x, errors="coerce")

    if ratio_single:
        out["Ratio_High"]   = _num(df[ratio_single])
        out["Ratio_Medium"] = _num(df[ratio_single])
        out["Ratio_Low"]    = _num(df[ratio_single])
    else:
        out["Ratio_High"]   = _num(df[ratio_high]) if ratio_high else np.nan
        out["Ratio_Medium"] = _num(df[ratio_medium]) if ratio_medium else np.nan
        out["Ratio_Low"]    = _num(df[ratio_low]) if ratio_low else np.nan

    return out.dropna(subset=["Department", "Role", "Shift"]).reset_index(drop=True)


# ========= Shifts Input (optional/manual) =========

def load_shifts_from_excel(excel_path: str, sheet_name: str = "Shifts Input") -> pd.DataFrame:
    """
    Parses 'Shifts Input' if present.
    Returns columns: Shift, Start, End, Hours, Label
    """
    try:
        df = pd.read_excel(excel_path, sheet_name=sheet_name, header=0)
    except Exception:
        return pd.DataFrame(columns=["Shift", "Start", "End", "Hours", "Label"])

    keep = [c for c in df.columns if c.strip().lower() in {"shift", "start", "end", "hours", "label"}]
    if not keep:
        return pd.DataFrame(columns=["Shift", "Start", "End", "Hours", "Label"])
    df = df[keep].copy()
    df.columns = [c.strip().title() for c in df.columns]
    return df.dropna(subset=["Shift"]).reset_index(drop=True)


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
