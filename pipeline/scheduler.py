import pandas as pd
from typing import Optional
from ingestion.shifts_loader import load_shift_rules

def assign_staff_to_shifts(plan_df: pd.DataFrame, shifts_df: Optional[pd.DataFrame] = None,
                           yaml_path: str = "config/settings.yaml") -> pd.DataFrame:
    """
    Assign staff from staffing plan into shifts.
    - Uses Excel shifts_df if provided and not empty.
    - Falls back to YAML config if Excel shifts_df is missing or empty.
    Adds a 'ShiftSource' column for traceability.
    """
    out_records = []

    use_yaml = shifts_df is None or shifts_df.empty
    if use_yaml:
        shifts_cfg = load_shift_rules(yaml_path)

    # 🔑 Use SeasonLabel (from staffing_plan)
    for (date, role, season), grp in plan_df.groupby(["Date", "Role", "SeasonLabel"]):
        staff_needed = int(grp["Staff_Needed"].sum())

        if staff_needed == 0:
            continue

        if use_yaml:
            role_shifts = shifts_cfg.get(role, [])
            role_shifts = pd.DataFrame(role_shifts)
            source = "YAML"
        else:
            if shifts_df is not None:
                role_shifts = shifts_df.copy()
            else:
                role_shifts = pd.DataFrame()
            source = "Excel"

        if role_shifts.empty:
            continue

        n_shifts = len(role_shifts)
        base = staff_needed // n_shifts
        remainder = staff_needed % n_shifts

        role_shifts = role_shifts.reset_index(drop=True)
        for i, s_row in enumerate(role_shifts.reset_index(drop=True).iterrows()):
            idx, s_row = s_row
            assigned = base + (1 if i < remainder else 0)

            out_records.append({
                "Date": date,
                "Role": role,
                "SeasonLabel": season,
                "Shift": s_row.get("Shift") or s_row.get("name"),
                "Start": s_row.get("Start Time") or s_row.get("start"),
                "End": s_row.get("End Time") or s_row.get("end"),
                "Hours": s_row.get("Hours") or s_row.get("hours"),
                "Assigned": assigned,
                "ShiftSource": source,
            })

    return pd.DataFrame(out_records)
