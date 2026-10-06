# Strategy Wall Simulator

A Streamlit dashboard for analysing F1 tyre degradation and pit strategy, built on real race data from [FastF1](https://github.com/theOehrly/Fast-F1).

Pick a season, a Grand Prix and a driver, and the app breaks down their final stint: how fast the tyres are wearing, whether a pit stop is worth it, and how they compare to a rival.


## Features

- **Tyre degradation:** linear fit of lap time vs lap number, with in/out laps and slow outliers removed and a fuel-burn correction applied
- **Next-lap predictions:** projects the next five laps from the current trend
- **Pit window indicator:** flags when degradation or tyre age crosses a threshold for the compound
- **Pit now vs stay out:** simulates the next five laps both ways with a cumulative time delta and an adjustable pit loss
- **Full-race stint view:** every stint for the driver, coloured by compound
- **Driver comparison:** side-by-side stint stats and a simple undercut/overcut estimate
- **Searchable dropdowns:** race calendar and driver list load automatically for the chosen season

## Tech stack

Python, Streamlit, FastF1, Pandas, NumPy, Plotly

## Getting started

```bash
git clone https://github.com/liam-omara/tyre-strategy.git
cd tyre-strategy
pip install -r requirements.txt
streamlit run app.py
```

The first time you load a race, FastF1 downloads its data, which can take a minute. It is cached locally in a `cache/` folder after that.

## Project structure

```
app.py                  Streamlit UI
data/loader.py          FastF1 session and lap loading
logic/degradation.py    Stint cleaning, degradation fit, lap predictions
logic/pit_model.py      Pit window rules, pit-now simulation, undercut estimate
logic/stints.py         Per-stint summary for the full-race chart
```

## How it works

1. Load the race session and the selected driver's laps.
2. Take the final stint and remove in/out laps, missing times and slow outliers.
3. Fit a straight line to lap time vs lap number. The slope is the raw trend.
4. Add back a fuel-burn estimate (about 0.035 s/lap) to get tyre degradation alone.
5. Use that trend to predict upcoming laps and to compare staying out against pitting for fresh tyres.

## Limitations

- Analyses the **final stint** of a finished race only; there is no lap selector yet.
- Pit loss (default 22 s), fresh-tyre gain (1.2 s) and the fuel effect are fixed estimates, not fitted per track.
- Degradation is modelled as linear, which ignores the tyre "cliff".
- The undercut estimate compares two cars' pace and ignores traffic, track position and safety cars.

## Ideas for next steps

- Lap slider to simulate decisions mid-race
- Per-track pit loss from historical data
- Safety car and traffic awareness
- Non-linear degradation models
- Full-race strategy optimiser

## Data

Race data comes from FastF1, which pulls from official F1 timing sources. This project is unofficial and not affiliated with Formula 1.
