"""
Excel loaders tailored for HIRA Light (ED) v0.02.xlsx.

- Cleans duplicate headers and normalizes column names.
- Extracts canonical inputs for Census, Staffing Rules (RN/NA), Shifts, and Resources.
- Standardizes output schema for downstream logic.
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


def _find_first(df: pd.DataFrame, base: str) -> Optional[str]:
    """
    Return the first column label whose name equals `base` or starts with `base__`.
    Works with frames whose columns were made unique via _make_unique.
    """
    for c in df.columns:
        nm = str(c).strip()
        if nm == base or nm.startswith(base + "__"):
            return c
    return None


# ========= Census Input =========

def load_census_from_excel(excel_path: str, sheet_name: str = "Census Input") -> pd.DataFrame:
    """
    Parses 'Census Input'.
    Canonical output columns: Date (datetime64), Census (float)
    """
    raw = pd.read_excel(excel_path, sheet_name=sheet_name, header=None)
    if raw.shape[0] < 3:
        raise ValueError("Census sheet too small to promote headers.")

    # Promote row 1 to header; make names unique; take data from row 2+
    header = _make_unique([str(h) for h in raw.iloc[1].tolist()])
    df = raw.iloc[2:].copy()
    df.columns = header

    # Choose first occurrences
    date_src_col = _find_first(df, "Date") or _find_first(df, "Projected_Date")
    census_src_col = _find_first(df, "Census") or _find_first(df, "Projected_Census")

    if not date_src_col or not census_src_col:
        raise ValueError(f"Census Input missing required columns. Columns seen: {list(df.columns)}")

    # Normalize
    df = df.rename(columns={date_src_col: "Date", census_src_col: "Census"})
    df["Date"] = pd.to_datetime(np.asarray(df["Date"].to_numpy()), errors="coerce")
    df["Census"] = pd.to_numeric(np.asarray(df["Census"].to_numpy()), errors="coerce")

    df = df.dropna(subset=["Date", "Census"]).reset_index(drop=True)
    return df[["Date", "Census"]]


# ========= Staffing Rules (RN + NA only) =========

def load_staffing_rules_from_excel(excel_path: str, sheet_name: str = "Staffing Grid") -> pd.DataFrame:
    """
    Parses 'Staffing Grid' (IP v0.12) to extract RN + NA staffing ratios.
    Returns DataFrame with columns: Role, Ratio
    """
    raw = pd.read_excel(excel_path, sheet_name=sheet_name, header=None)

    roles = []
    ratios = []

    for idx, row in raw.iterrows():
        row_vals = [str(x).strip() for x in row.tolist() if pd.notna(x)]
        if not row_vals:
            continue

        # Look for RN or NA in row
        if "RN" in row_vals or "NA" in row_vals:
            for role in ["RN", "NA"]:
                if role in row_vals:
                    # Try to find a numeric ratio in the same row
                    for val in row_vals:
                        try:
                            ratio = int(float(val))
                            roles.append(role)
                            ratios.append(ratio)
                            break
                        except Exception:
                            continue

    if not roles:
        raise ValueError(f"No RN/NA ratios found in {sheet_name} sheet")

    df = pd.DataFrame({"Role": roles, "Ratio": ratios}).drop_duplicates("Role")
    return df.reset_index(drop=True)

# ========= Shifts Input =========

def load_shifts_from_excel(excel_path: str, sheet_name: str = "Shifts Input") -> pd.DataFrame:
    """
    Parses 'Shifts Input'.
    Returns columns: Shift Group, Shift, Shift Block, Start Time, End Time, Hours, Label
    """
    raw = pd.read_excel(excel_path, sheet_name=sheet_name, header=None)

    def parse_block(start_pos: int) -> pd.DataFrame:
        header = _make_unique([str(h) for h in raw.iloc[start_pos].tolist()])
        df = raw.iloc[start_pos + 1:].copy()
        df.columns = header
        keep = [c for c in df.columns if c in ("Shift", "Shift Block", "Start Time", "End Time", "Hours", "Label")]
        if not keep:
            return pd.DataFrame()
        df = df[keep].dropna(subset=["Shift", "Shift Block"], how="any").reset_index(drop=True)
        return df

    header_positions: List[int] = []
    for pos in range(raw.shape[0]):
        if raw.iloc[pos].astype(str).str.strip().eq("Shift Block").any():
            header_positions.append(pos)

    blocks = []
    for pos in header_positions:
        block = parse_block(pos)
        if block.empty:
            continue
        # infer group name a few rows above (e.g., "Weekday Shift Plan")
        group = None
        for j in range(3):
            r = pos - (j + 1)
            if r >= 0:
                val = raw.iloc[r, 0]
                if isinstance(val, str) and "Shift Plan" in val:
                    group = val.strip()
                    break
        block.insert(0, "Shift Group", group or "Shifts")
        blocks.append(block)

    if not blocks:
        return pd.DataFrame(columns=["Shift Group", "Shift", "Shift Block", "Start Time", "End Time", "Hours", "Label"])
    return pd.concat(blocks, ignore_index=True)


# ========= Resource Input =========

def load_resources_from_excel(excel_path: str, sheet_name: str = "Resource Input") -> pd.DataFrame:
    """
    Light normalization for Resource Input sheet.
    Keeps all columns but normalizes common header typos.
    """
    df = pd.read_excel(excel_path, sheet_name=sheet_name, header=0)
    ren = {}
    for c in df.columns:
        lc = str(c).strip().lower()
        if lc == "unit ftes":
            ren[c] = "Unit FTEs"
        elif lc == "availibility":  # observed typo
            ren[c] = "Availability"
    return df.rename(columns=ren)
