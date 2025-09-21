import yaml
import pandas as pd

def load_shift_rules(path: str = "config/settings.yaml") -> dict:
    """
    Load role-based shift definitions from settings.yaml.
    Returns dict: { Role: [ {name, start, end, hours}, ... ] }
    """
    with open(path, "r") as f:
        cfg = yaml.safe_load(f)
    return cfg.get("shifts", {})


def expand_shifts_for_role(role: str, path: str = "config/settings.yaml") -> pd.DataFrame:
    """
    Expand shifts for a given role into a DataFrame.
    """
    shifts_cfg = load_shift_rules(path)
    role_shifts = shifts_cfg.get(role, [])
    return pd.DataFrame(role_shifts)
