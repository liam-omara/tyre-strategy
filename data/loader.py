import os
import fastf1

os.makedirs('cache', exist_ok=True)
fastf1.Cache.enable_cache('cache')

def load_race(year, gp, session_type='R'):
    session = fastf1.get_session(year, gp, session_type)
    session.load(telemetry=False, weather=False, messages=False)  # much faster
    return session

def load_driver_laps(session, driver_code):
    laps = session.laps.pick_drivers(driver_code.strip().upper())
    return laps.reset_index(drop=True)