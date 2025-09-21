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


def compare_plan_vs_resources(plan_df: pd.DataFrame, resources_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compare staffing plan vs available FTEs from Resource Input.
    Returns table with gaps/surpluses.
    """
    summary = plan_df.groupby(["Date", "Role"], as_index=False)["Staff_Needed"].sum()

    merged = summary.merge(resources_df, on="Role", how="left")
    merged["FTEs"] = merged["FTEs"].fillna(0)
    merged["Gap"] = merged["FTEs"] - merged["Staff_Needed"]

    return merged
