import pandas as pd

def load_staffing_rules(path="config/staffing_grid.csv"):
    # Expect columns like: CensusMax, RN, Tech (rename to match your sheet if needed)
    return pd.read_csv(path)
