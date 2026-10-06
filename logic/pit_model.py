import pandas as pd

limits = {'SOFT': 15, 'MEDIUM': 25, 'HARD': 40}
FUEL_EFFECT = 0.035

def pit_window(tyre_age, tyre_deg, compound):
    if tyre_deg > 0.08:
        return True
    return tyre_age > limits.get(compound, 30)

def simulate_pit_now(base_next, slope, pit_loss=22.0, fresh_gain=1.2, laps_ahead=5):
    """base_next = predicted lap time for the next lap on the current tyres."""
    fresh_slope = -FUEL_EFFECT                 # new tyres: only fuel burn, no wear
    new_base = base_next - fresh_gain

    stay_out = [base_next + slope * i for i in range(laps_ahead)]
    pit_now = [(pit_loss if i == 0 else 0.0) + new_base + fresh_slope * i
               for i in range(laps_ahead)]

    df = pd.DataFrame({
        'LapAhead': range(1, laps_ahead + 1),
        'StayOut': stay_out,
        'PitNow': pit_now,
    })
    df['Delta (cumulative)'] = (df['PitNow'] - df['StayOut']).cumsum()  # negative = pitting is ahead
    return df

def undercut_analysis(my_base, rival_base, pit_loss=22.0, fresh_gain=1.2):
    """my_base / rival_base = predicted next-lap time on current tyres."""
    gain_per_lap = rival_base - (my_base - fresh_gain)
    if gain_per_lap <= 0:
        return gain_per_lap, None
    return gain_per_lap, pit_loss / gain_per_lap