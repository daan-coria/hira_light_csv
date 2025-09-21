import math

def staff_needed(census: int, ratio: int) -> int:
    return math.ceil(census / ratio)
