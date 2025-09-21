import math
import pandas as pd


def staff_needed(census: float, ratio: float) -> int:
    """
    Standard staffing formula:
        Staff Needed = ceil(Census / Ratio)
    """
    if pd.isna(census) or pd.isna(ratio) or ratio <= 0:
        return 0
    return math.ceil(census / ratio)


def generate_staffing_plan(
    census_df: pd.DataFrame,
    rules_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Generate staffing plan with optional season-based ratios.

    Parameters
    ----------
    census_df : DataFrame
        Must contain ["Date", "Census"] and optionally ["SeasonLabel"].
    rules_df : DataFrame
        Can be:
          - Wide format with columns ["Role", "Low", "Medium", "High"]
          - Simple format with ["Role", "Ratio"]

    Returns
    -------
    DataFrame with columns:
      [Date, Role, SeasonLabel, Census, RatioUsed, Staff_Needed]
    """
    rules_df = rules_df.rename(columns=lambda c: str(c).strip())

    # Detect if season-specific ratios exist
    has_season_cols = any(col in rules_df.columns for col in ["Low", "Medium", "High"])

    plan_records = []
    for _, c_row in census_df.iterrows():
        date = c_row.get("Date")
        census_val = c_row.get("Census")
        season = c_row.get("SeasonLabel", None)

        for _, r_row in rules_df.iterrows():
            role = str(r_row["Role"]).strip()

            if has_season_cols and season in ["Low", "Medium", "High"]:
                ratio = r_row.get(season, pd.NA)
            else:
                ratio = r_row.get("Ratio", pd.NA)

            needed = staff_needed(float(census_val) if census_val is not None else 0.0,
                                  float(ratio) if ratio is not None else 0.0)

            plan_records.append({
                "Date": date,
                "Role": role,
                "SeasonLabel": season if season else "N/A",
                "Census": census_val,
                "RatioUsed": ratio,
                "Staff_Needed": needed,
            })

    return pd.DataFrame(plan_records)


def build_staffing_plan_from_rules(
    census_df: pd.DataFrame,
    rules_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Wrapper: build plan directly from census + rules.
    """
    return generate_staffing_plan(census_df, rules_df)
