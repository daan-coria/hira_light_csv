import yaml
import pandas as pd

MONTH_NAME_TO_NUM = {
    'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
    'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12
}

FACTOR_CANDIDATES = {
    "seasonfactor","season_factor","factor","adjustment","adjustment%","adjustment_%",
    "adj","adj%","adj_%","adjpercent","adj_percent","index","multiplier","seasonality"
}
MONTH_CANDIDATES = {"month","month_num","monthnumber","month_number"}
WEEKDAY_CANDIDATES = {"weekday","dayofweek","dow"}  # optional


def _coerce_month(series: pd.Series) -> pd.Series:
    s = series.copy()
    if s.dtype == object:
        s = s.astype(str).str.strip().str.lower().map(MONTH_NAME_TO_NUM).fillna(series)
    s = pd.to_numeric(s, errors="coerce").astype("Int64")
    return s


def _to_multiplier(x):
    """
    Convert a value to a multiplier:
    - "5%" -> 1.05
    - 0.05  -> 1.05
    - 1.05  -> 1.05
    - "1.05" -> 1.05
    """
    if pd.isna(x):
        return pd.NA
    if isinstance(x, str):
        xs = x.strip().replace(" ", "")
        if xs.endswith("%"):
            try:
                val = float(xs[:-1]) / 100.0
                return 1.0 + val
            except Exception:
                return pd.NA
        try:
            x = float(xs)
        except Exception:
            return pd.NA

    try:
        xf = float(x)
    except Exception:
        return pd.NA

    if -0.99 <= xf <= 0.99:  # treat as delta
        return 1.0 + xf
    return xf


def load_season_rules(path: str = "config/settings.yaml") -> list[dict]:
    """
    Load season rules from settings.yaml.
    Returns a list of dicts with months, weekdays, and season labels.
    """
    with open(path, "r") as f:
        cfg = yaml.safe_load(f)
    return cfg.get("seasons", [])


def apply_nash_seasonality(census_df: pd.DataFrame, rules: list[dict]) -> pd.DataFrame:
    """
    Enrich census_df with SeasonLabel and SeasonFactor.
    - If no match, defaults to Medium/1.0.
    """
    df = census_df.copy()
    df["Month"] = df["Date"].dt.month
    df["Weekday"] = df["Date"].dt.dayofweek  # 0=Mon

    def map_label(row):
        for rule in rules:
            if row["Month"] in rule["months"] and row["Weekday"] in rule["weekdays"]:
                return rule["season"]
        return "Medium"

    df["SeasonLabel"] = df.apply(map_label, axis=1)

    # Assign SeasonFactor based on label
    def label_to_factor(label: str) -> float:
        if label == "High":
            return 1.1
        if label == "Low":
            return 0.9
        return 1.0

    df["SeasonFactor"] = df["SeasonLabel"].apply(label_to_factor)
    return df