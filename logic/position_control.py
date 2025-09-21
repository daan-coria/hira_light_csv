import pandas as pd


def build_position_control(resources_df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize position control data (from Resource Input).
    Uses 'Position' as Role, 'Unit FTEs' as FTEs, and 'Availibility' if present.
    """
    df = resources_df.copy()
    df = df.rename(columns=lambda c: str(c).strip())

    # Map headers
    role_col = None
    fte_col = None
    avail_col = None

    for c in df.columns:
        lc = c.lower()
        if lc in ("role", "position"):  # accept both
            role_col = c
        elif "fte" in lc and "unit" in lc:  # "Unit FTEs"
            fte_col = c
        elif "avail" in lc:  # matches "Availibility"
            avail_col = c

    if not role_col or not fte_col:
        raise ValueError("Resource Input must contain Position/Role + Unit FTEs.")

    out = df[[role_col, fte_col] + ([avail_col] if avail_col else [])].dropna(how="all")
    out = out.rename(columns={role_col: "Role", fte_col: "FTEs"})
    if avail_col:
        out = out.rename(columns={avail_col: "Availability"})

    # Keep only RN + NA
    out = out[out["Role"].isin(["RN", "NA"])].reset_index(drop=True)

    return out

import pandas as pd

def compare_plan_vs_resources(plan_df: pd.DataFrame, resources_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compare staffing plan (needed staff) vs available FTEs from Resource Input.
    Returns a DataFrame with Gap, Shortage, Surplus.
    """
    # Normalize resource column names
    ren_map = {c.lower().strip(): c for c in resources_df.columns}
    fte_col = None
    for cand in ["unit ftes", "unit fte", "ftes", "fte"]:
        if cand in ren_map:
            fte_col = ren_map[cand]
            break
    if not fte_col:
        raise ValueError(f"Resource Input is missing an FTE column (saw: {list(resources_df.columns)})")

    # Aggregate planned staff needed
    needed = (
        plan_df.groupby(["Date", "Role"], as_index=False)
        .agg({"Staff_Needed": "sum"})
        .rename(columns={"Staff_Needed": "Needed"})
    )

    # Aggregate available staff by Role
    available = (
        resources_df.groupby("Role", as_index=False)
        .agg({fte_col: "sum"})
        .rename(columns={fte_col: "Available"})
    )

    # Merge
    comp = needed.merge(available, on="Role", how="left").fillna(0)

    # Calculate Gap, Shortage, Surplus
    comp["Gap"] = comp["Available"] - comp["Needed"]
    comp["Shortage"] = (comp["Needed"] - comp["Available"]).clip(lower=0)
    comp["Surplus"] = (comp["Available"] - comp["Needed"]).clip(lower=0)

    return comp


