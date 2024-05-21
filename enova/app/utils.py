import pandas as pd


def compute_actual_duration(value, unit):
    return int(pd.Timedelta(f"{value}{unit}").total_seconds())
