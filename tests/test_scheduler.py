import pandas as pd
from logic.scheduler import assign_staff_to_shifts


def test_scheduler_with_excel_shifts(tmp_path):
    """Assign staff using Excel-defined shifts (shifts_df passed in)."""
    # Staffing plan: 4 staff needed for RN Day, High season
    plan_df = pd.DataFrame([
        {"Date": "2025-06-01", "Role": "RN", "SeasonLabel": "High", "Staff_Needed": 4}
    ])

    # Simulate Excel "Shifts Input"
    shifts_df = pd.DataFrame([
        {"Shift": "Day", "Start Time": "07:00", "End Time": "19:00", "Hours": 12},
        {"Shift": "Night", "Start Time": "19:00", "End Time": "07:00", "Hours": 12},
    ])

    schedule = assign_staff_to_shifts(plan_df, shifts_df)

    # Check distribution
    assert schedule["Assigned"].sum() == 4
    assert all(schedule["ShiftSource"] == "Excel")


def test_scheduler_with_yaml_fallback(tmp_path):
    """Assign staff using YAML-defined shifts (no shifts_df passed)."""
    # Staffing plan: 3 staff needed for RN, Medium season
    plan_df = pd.DataFrame([
        {"Date": "2025-06-02", "Role": "RN", "SeasonLabel": "Medium", "Staff_Needed": 3}
    ])

    # Fallback to config/settings.yaml
    schedule = assign_staff_to_shifts(plan_df, shifts_df=None, yaml_path="config/settings.yaml")

    assert schedule["Assigned"].sum() == 3
    assert all(schedule["ShiftSource"] == "YAML")
    # YAML config has Day/Night for RN, so we expect 2 rows
    assert set(schedule["Shift"]) == {"Day", "Night"}


def test_scheduler_even_distribution_excel():
    """Check even distribution across Excel shifts."""
    plan_df = pd.DataFrame([
        {"Date": "2025-06-03", "Role": "RN", "SeasonLabel": "Low", "Staff_Needed": 5}
    ])

    # Two shifts → staff should be split 3 + 2
    shifts_df = pd.DataFrame([
        {"Shift": "Day", "Start Time": "07:00", "End Time": "19:00", "Hours": 12},
        {"Shift": "Night", "Start Time": "19:00", "End Time": "07:00", "Hours": 12},
    ])

    schedule = assign_staff_to_shifts(plan_df, shifts_df)

    assigned_counts = schedule.set_index("Shift")["Assigned"].to_dict()
    assert assigned_counts["Day"] == 3
    assert assigned_counts["Night"] == 2
