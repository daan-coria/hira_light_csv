import pandas as pd
from logic.staffing_plan import generate_staffing_plan


def test_generate_staffing_plan_basic():
    """Simple case: single Ratio column, no season labels in census."""
    census_df = pd.DataFrame([
        {"Date": "2025-06-01", "Census": 10},
        {"Date": "2025-06-02", "Census": 15},
    ])
    rules_df = pd.DataFrame([
        {"Role": "RN", "Ratio": 4},
        {"Role": "NA", "Ratio": 6},
    ])

    plan = generate_staffing_plan(census_df, rules_df)

    rn_day1 = plan[(plan["Date"] == "2025-06-01") & (plan["Role"] == "RN")]["Staff_Needed"].iloc[0]
    na_day2 = plan[(plan["Date"] == "2025-06-02") & (plan["Role"] == "NA")]["Staff_Needed"].iloc[0]

    assert rn_day1 == 3   # ceil(10 / 4)
    assert na_day2 == 3   # ceil(15 / 6)


def test_generate_staffing_plan_with_seasons():
    """Seasonal case: census has SeasonLabel, rules_df has Low/Medium/High columns."""
    census_df = pd.DataFrame([
        {"Date": "2025-07-01", "Census": 20, "SeasonLabel": "High"},
        {"Date": "2025-03-01", "Census": 20, "SeasonLabel": "Low"},
        {"Date": "2025-10-01", "Census": 20, "SeasonLabel": "Medium"},
    ])
    rules_df = pd.DataFrame([
        {"Role": "RN", "Low": 6, "Medium": 5, "High": 4},
        {"Role": "NA", "Low": 8, "Medium": 7, "High": 6},
    ])

    plan = generate_staffing_plan(census_df, rules_df)

    rn_high = plan[(plan["Date"] == "2025-07-01") & (plan["Role"] == "RN")]["Staff_Needed"].iloc[0]
    rn_low = plan[(plan["Date"] == "2025-03-01") & (plan["Role"] == "RN")]["Staff_Needed"].iloc[0]
    rn_med = plan[(plan["Date"] == "2025-10-01") & (plan["Role"] == "RN")]["Staff_Needed"].iloc[0]

    # High season → ratio 4 → ceil(20/4) = 5
    assert rn_high == 5
    # Low season → ratio 6 → ceil(20/6) = 4
    assert rn_low == 4
    # Medium season → ratio 5 → ceil(20/5) = 4
    assert rn_med == 4


def test_generate_staffing_plan_fallback_to_ratio():
    """If SeasonLabel exists but rules_df has only 'Ratio', it should ignore seasons."""
    census_df = pd.DataFrame([
        {"Date": "2025-07-01", "Census": 12, "SeasonLabel": "High"},
    ])
    rules_df = pd.DataFrame([
        {"Role": "RN", "Ratio": 4},
    ])

    plan = generate_staffing_plan(census_df, rules_df)

    rn_needed = plan[(plan["Date"] == "2025-07-01") & (plan["Role"] == "RN")]["Staff_Needed"].iloc[0]

    # Only "Ratio" column → should use 4 regardless of season
    assert rn_needed == 3   # ceil(12/4)
