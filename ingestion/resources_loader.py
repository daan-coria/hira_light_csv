import pandas as pd

def normalize_resources(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns=lambda c: str(c).strip())
    # Calculate effective FTE (columns K–O logic)
    df["Effective FTE"] = df["Unit FTEs"] - df["FTE on Leave (Weekdays)"] - df["FTE on Leave (Weekends)"]
    return df
