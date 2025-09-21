import pandas as pd
from ingestion.excel_v010 import load_census_from_excel
from ingestion.seasons_loader import load_season_rules, apply_nash_seasonality


def _label_from_factor(factor: float) -> str:
    """
    Derive a season label from a numeric factor.
    - Factor < 1.0  -> "Low"
    - Factor == 1.0 -> "Medium"
    - Factor > 1.0  -> "High"
    """
    if pd.isna(factor):
        return "Medium"
    if factor < 1.0:
        return "Low"
    if factor > 1.0:
        return "High"
    return "Medium"


def load_census_with_season(
    excel_path: str,
    sheet_name: str = "Census Input",
    settings_path: str = "config/settings.yaml"
) -> pd.DataFrame:
    """
    Load census from Excel and enrich with Nash Analytics seasonality.
    Adds both SeasonLabel (Low/Medium/High) and SeasonFactor (numeric).
    """
    census_df = load_census_from_excel(excel_path, sheet_name=sheet_name)
    rules = load_season_rules(settings_path)
    return apply_nash_seasonality(census_df, rules)