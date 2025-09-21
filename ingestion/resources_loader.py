from __future__ import annotations
import pandas as pd

# We only accept the initial (A–G) columns. Names can vary; we normalize.
CANDIDATES = {
    "department": {"department", "dept", "cost center", "costcenter"},
    "role":       {"role", "position", "job", "jobtitle"},
    "name":       {"name", "employee", "staff", "resource"},
    "fte":        {"fte", "ftes", "unit fte", "unit ftes"},
    "shift":      {"shift", "shiftname"},
    "start":      {"start", "start time", "starttime", "begin"},
    "end":        {"end", "end time", "endtime", "finish"},
}

def _pick(df: pd.DataFrame, keys: set[str]) -> str | None:
    lower = {c.strip().lower(): c for c in df.columns}
    for k in keys:
        if k in lower:
            return lower[k]
    return None

def load_resources_initial(excel_path: str, sheet_name: str = "Resource Input") -> pd.DataFrame:
    """
    Load only the 'destination' A–G columns (whatever their labels are),
    and normalize them to: Department, Role, Name, FTE, Shift, Start, End.

    Output columns may be a subset if some fields are missing (Shift/Start/End are optional).
    """
    raw = pd.read_excel(excel_path, sheet_name=sheet_name)
    out = pd.DataFrame()

    dep  = _pick(raw, CANDIDATES["department"]);   out["Department"] = raw[dep] if dep else ""
    role = _pick(raw, CANDIDATES["role"]);         out["Role"]       = raw[role] if role else ""
    name = _pick(raw, CANDIDATES["name"]);         out["Name"]       = raw[name] if name else ""
    fte  = _pick(raw, CANDIDATES["fte"]);          out["FTE"]        = pd.to_numeric(raw[fte], errors="coerce") if fte else 0

    shf  = _pick(raw, CANDIDATES["shift"]);        out["Shift"]      = raw[shf] if shf else ""
    st   = _pick(raw, CANDIDATES["start"]);        out["Start"]      = pd.to_numeric(raw[st], errors="coerce") if st else pd.NA
    en   = _pick(raw, CANDIDATES["end"]);          out["End"]        = pd.to_numeric(raw[en], errors="coerce") if en else pd.NA

    # Drop rows without Department or Role if present
    if "Department" in out and "Role" in out:
        out = out[~(out["Department"].astype(str).str.strip() == "") & ~(out["Role"].astype(str).str.strip() == "")]
    return out.reset_index(drop=True)
