from __future__ import annotations
import pandas as pd


def build_position_control(resources_df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize Resource Input (cols A–G) and aggregate available FTEs.
    Output columns:
      Department | Role | Shift | AvailableFTE
    """
    df = resources_df.copy()

    # Ensure required columns exist
    for col in ["Department", "Role", "Shift"]:
        if col not in df.columns:
            df[col] = ""
    if "FTE" not in df.columns:
        df["FTE"] = 0.0

    # Missing shift → treat as 'All' (catch-all capacity)
    df["Shift"] = df["Shift"].fillna("").replace("", "All")

    # Aggregate by Dept/Role/Shift
    out = (
        df.groupby(["Department", "Role", "Shift"], as_index=False)
          .agg({"FTE": "sum"})
          .rename(columns={"FTE": "AvailableFTE"})
    )
    return out


def compare_plan_vs_resources(plan_df: pd.DataFrame, pos_ctrl_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compare staffing plan vs available FTEs:
      • Plan is per Date/Hour/Dept/Role/Shift (granular).
      • Resources are Dept/Role/Shift aggregates (with 'All' fallback).
    Output columns:
      Date | Hour | Department | Role | Shift | Needed | AvailableFTE | Gap | Shortage | Surplus
    """
    # Aggregate needed staff by Date/Hour/Dept/Role/Shift
    need = (
        plan_df.groupby(["Date", "Hour", "Department", "Role", "Shift"], as_index=False)
               .agg({"Staff_Needed": "sum"})
               .rename(columns={"Staff_Needed": "Needed"})
    )

    # Exact merge first
    comp = need.merge(pos_ctrl_df, on=["Department", "Role", "Shift"], how="left")

    # Fallback: if no exact match, pull from 'All' shift for that Dept/Role
    mask = comp["AvailableFTE"].isna()
    if mask.any():
        fallback = (
            pos_ctrl_df[pos_ctrl_df["Shift"].eq("All")]
            [["Department", "Role", "AvailableFTE"]]
            .rename(columns={"AvailableFTE": "AvailableFTE_All"})
        )
        comp = comp.merge(fallback, on=["Department", "Role"], how="left")
        comp.loc[mask, "AvailableFTE"] = comp.loc[mask, "AvailableFTE_All"]
        comp = comp.drop(columns=["AvailableFTE_All"])

    # Replace any remaining NaNs with 0
    comp["AvailableFTE"] = comp["AvailableFTE"].fillna(0)

    # Staffing balance
    comp["Gap"]      = comp["AvailableFTE"] - comp["Needed"]
    comp["Shortage"] = (comp["Needed"] - comp["AvailableFTE"]).clip(lower=0)
    comp["Surplus"]  = (comp["AvailableFTE"] - comp["Needed"]).clip(lower=0)

    return comp
