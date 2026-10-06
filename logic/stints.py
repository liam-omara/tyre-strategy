import pandas as pd
from logic.degradation import clean_stint 

def get_stints(laps):
    stints = laps.groupby('Stint')
    info = []

    for stint_id, stint in stints:
        info.append({
            'stint_id': int(stint_id),
            'compound': stint['Compound'].iloc[0],
            'start_lap': int(stint['LapNumber'].min()),
            'end_lap': int(stint['LapNumber'].max()),
            'tyre_age': int(stint['TyreLife'].max()),
            'mean_lap_time': clean_stint(stint)['t'].mean() 
        })

    return pd.DataFrame(info)
