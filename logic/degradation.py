import numpy as np
import pandas as pd

FUEL_EFFECT = 0.035  # s/lap that cars get faster purely from burning fuel

def clean_stint(stint):
    """Drop NaN laps, in/out laps and slow outliers (SC, traffic, etc.)."""
    s = stint.dropna(subset=['LapTime']).copy()
    s = s[s['PitInTime'].isna() & s['PitOutTime'].isna()]
    s['t'] = s['LapTime'].dt.total_seconds()
    if len(s) >= 4:
        s = s[s['t'] < s['t'].median() * 1.07]
    return s

def degradation(stint):
    s = clean_stint(stint)
    if len(s) < 3:
        raise ValueError("Not enough clean laps in this stint to fit a trend.")
    slope, intercept = np.polyfit(s['LapNumber'].values, s['t'].values, 1)
    return float(slope), float(intercept)

def predict_laps(last_lap, slope, intercept, n=5):
    future = np.arange(last_lap + 1, last_lap + n + 1)
    times = slope * future + intercept
    return pd.DataFrame({'Lap': future, 'Predicted': times})