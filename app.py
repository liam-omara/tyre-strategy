import streamlit as st
import plotly.express as px
import fastf1

from data.loader import load_race, load_driver_laps
from logic.stints import get_stints
from logic.degradation import degradation, predict_laps, clean_stint, FUEL_EFFECT
from logic.pit_model import pit_window, simulate_pit_now, undercut_analysis


st.set_page_config(
    page_title="Strategy Wall Simulator",
    layout="wide"
)


@st.cache_resource(show_spinner="Loading race data...")
def get_session(year, race):
    return load_race(year, race)


@st.cache_data(show_spinner=False)
def get_race_options(year):
    """All Grand Prix names for a season, e.g. 'Hungarian Grand Prix'."""
    schedule = fastf1.get_event_schedule(year, include_testing=False)
    return schedule["EventName"].tolist()


@st.cache_data(show_spinner=False)
def get_driver_options(year, race):
    """Returns labels like 'VER – Max Verstappen' for everyone in the race."""
    session = get_session(year, race)
    res = session.results[["Abbreviation", "FullName"]].dropna()
    return sorted(f"{r.Abbreviation} – {r.FullName}" for r in res.itertuples())


st.title("🏎️ Strategy Wall Simulator – MVP Dashboard")

# ─────────────────────────────
# Controls
# ─────────────────────────────
col_controls_1, col_controls_2, col_controls_3 = st.columns([1, 1, 1])

with col_controls_1:
    year = st.selectbox("Year", [2022, 2023], index=1)

with col_controls_2:
    try:
        race_options = get_race_options(year)
        default_idx = (
            race_options.index("Hungarian Grand Prix")
            if "Hungarian Grand Prix" in race_options
            else 0
        )
        race = st.selectbox("Race", race_options, index=default_idx)
    except Exception:
        st.warning("Couldn't load the race calendar, type the race name instead.")
        race = st.text_input("Race", "Hungary")

with col_controls_3:
    driver = st.text_input("Driver Code", "HAM")

try:
    driver_options = get_driver_options(year, race)
except Exception:
    driver_options = []
    st.warning(f"Couldn't load the driver list for '{race} {year}'. Check the race name.")

driver2_choice = st.selectbox(
    "Compare With Driver (optional)",
    driver_options,
    index=None,
    placeholder="Type a name or code, e.g. Ve → VER",
)
driver2 = driver2_choice.split(" – ")[0] if driver2_choice else ""

pit_loss = st.number_input(
    "Pit loss (s)", min_value=15.0, max_value=35.0, value=22.0, step=0.5
)

run = st.button("Run Analysis", type="primary")

# Keep results on screen when other widgets cause a rerun
if run:
    st.session_state.ran = True

# ─────────────────────────────
# Main logic
# ─────────────────────────────
if st.session_state.get("ran"):
    driver = driver.strip().upper()
    driver2 = driver2.strip().upper()

    session = get_session(year, race)
    laps = load_driver_laps(session, driver)

    if laps.empty:
        st.error(f"No laps found for driver '{driver}'.")
        st.stop()

    # Current stint for main driver (final stint of the race)
    current_stint_id = laps['Stint'].dropna().iloc[-1]
    stint = laps[laps['Stint'] == current_stint_id]
    clean = clean_stint(stint)

    if len(clean) < 3:
        st.warning("Not enough clean laps in the final stint to analyse.")
        st.stop()

    compound = stint['Compound'].iloc[0]
    tyre_age = (
        int(stint['TyreLife'].max())
        if stint['TyreLife'].notna().any()
        else len(stint)
    )
    stint_length = int(stint['LapNumber'].max() - stint['LapNumber'].min() + 1)
    mean_lap = clean['t'].mean()

    slope, intercept = degradation(stint)      # raw lap-time trend (includes fuel burn)
    tyre_deg = slope + FUEL_EFFECT             # fuel-corrected tyre degradation
    last_lap = stint['LapNumber'].max()
    base_next = slope * (last_lap + 1) + intercept

    pred = predict_laps(last_lap, slope, intercept)
    pit_open = pit_window(tyre_age, tyre_deg, compound)
    compare = simulate_pit_now(base_next, slope, pit_loss)

    # ─────────────────────────
    # Top summary card
    # ─────────────────────────
    st.markdown("### Tyre & Strategy Summary")

    summary_card = st.container()
    with summary_card:
        col_a, col_b, col_c = st.columns([1.2, 1, 1.2])

        with col_a:
            st.markdown(
                f"""
                <div style="padding: 1rem; border-radius: 0.75rem; background-color: #111827; color: #F9FAFB;">
                    <div style="font-size: 0.8rem; text-transform: uppercase; opacity: 0.7;">Compound</div>
                    <div style="font-size: 1.8rem; font-weight: 700; margin-top: 0.25rem;">{compound}</div>
                    <div style="font-size: 0.9rem; margin-top: 0.5rem;">Driver: <b>{driver}</b></div>
                    <div style="font-size: 0.9rem;">Race: <b>{race} {year}</b></div>
                </div>
                """,
                unsafe_allow_html=True
            )

        with col_b:
            st.markdown(
                f"""
                <div style="padding: 1rem; border-radius: 0.75rem; background-color: #111827; color: #F9FAFB; text-align: center;">
                    <div style="font-size: 0.8rem; text-transform: uppercase; opacity: 0.7;">Tyre Age</div>
                    <div style="font-size: 2.2rem; font-weight: 700; margin-top: 0.25rem;">{tyre_age}</div>
                    <div style="font-size: 0.9rem; margin-top: 0.25rem;">laps on this set</div>
                    <div style="font-size: 0.8rem; opacity: 0.7;">Stint length: {stint_length} laps</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        with col_c:
            trend_arrow = "↑" if tyre_deg > 0 else "↓"
            trend_text = "slowing" if tyre_deg > 0 else "improving"
            trend_color = "#F97316" if tyre_deg > 0 else "#22C55E"

            pit_text = "OPEN" if pit_open else "CLOSED"
            pit_color = "#22C55E" if not pit_open else "#EF4444"
            pit_desc = (
                "Tyres still performing – stay out."
                if not pit_open
                else "Tyres degrading / old – pit window active."
            )

            st.markdown(
                f"""
                <div style="padding: 1rem; border-radius: 0.75rem; background-color: #111827; color: #F9FAFB;">
                    <div style="font-size: 0.8rem; text-transform: uppercase; opacity: 0.7;">Degradation (fuel-corrected)</div>
                    <div style="font-size: 1.6rem; font-weight: 700; margin-top: 0.25rem; color: {trend_color};">
                        {trend_arrow} {tyre_deg:.3f} s/lap
                    </div>
                    <div style="font-size: 0.9rem; margin-top: 0.25rem;">Trend: {trend_text}</div>
                    <div style="margin-top: 0.75rem; font-size: 0.8rem; text-transform: uppercase; opacity: 0.7;">Pit Window</div>
                    <div style="font-size: 1.1rem; font-weight: 700; color: {pit_color};">{pit_text}</div>
                    <div style="font-size: 0.85rem; margin-top: 0.25rem;">{pit_desc}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

    # ─────────────────────────
    # Current stint + predictions
    # ─────────────────────────
    st.markdown("### Stint Detail & Predictions")

    col_left, col_right = st.columns([1.1, 1.2])

    with col_left:
        st.subheader("Current Stint (Raw Numbers)")
        st.write({
            "Compound": f"{compound} — tyre type currently fitted",
            "Tyre Age": f"{tyre_age} laps — how long the tyre has been used",
            "Stint Length": f"{stint_length} laps in this stint",
            "Degradation (s/lap)": f"{tyre_deg:.3f} — positive = getting slower, negative = getting faster",
            "Mean Lap Time (s)": round(mean_lap, 3),
        })

        st.subheader("Pit Now Simulation")
        st.dataframe(compare, use_container_width=True)

    with col_right:
        # Degradation scatter + trend
        st.subheader("Degradation Trend (Lap Times vs Lap Number)")
        lap_nums = clean['LapNumber']
        lap_times = clean['t']

        fig_deg = px.scatter(
            x=lap_nums,
            y=lap_times,
            trendline="ols",
            labels={"x": "Lap Number", "y": "Lap Time (s)"},
            template="plotly_dark",
        )
        fig_deg.update_layout(height=350, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig_deg, use_container_width=True)

        # Predicted laps
        st.subheader("Predicted Next Laps")
        st.dataframe(pred, use_container_width=True)

        fig_pred = px.line(
            pred,
            x="Lap",
            y="Predicted",
            markers=True,
            labels={"Lap": "Lap Number", "Predicted": "Predicted Lap Time (s)"},
            template="plotly_dark",
        )
        fig_pred.update_layout(height=300, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig_pred, use_container_width=True)

    # ─────────────────────────
    # Stint visualisation (full race)
    # ─────────────────────────
    st.markdown("### Full Race Stint Visualisation")

    stints_df = get_stints(laps)
    if not stints_df.empty:
        fig_stints = px.bar(
            stints_df,
            x="stint_id",
            y="mean_lap_time",
            color="compound",
            labels={
                "stint_id": "Stint",
                "mean_lap_time": "Avg Lap Time (s)",
                "compound": "Compound",
            },
            template="plotly_dark",
        )
        fig_stints.update_xaxes(type="category")
        fig_stints.update_layout(height=350, margin=dict(l=10, r=10, t=30, b=10))
        st.plotly_chart(fig_stints, use_container_width=True)
    else:
        st.info("No stint data available for this driver.")

    # ─────────────────────────
    # Multi-driver comparison + undercut/overcut
    # ─────────────────────────
    st.markdown("### Multi‑Driver Comparison & Undercut / Overcut")

    if driver2:
        try:
            laps2 = load_driver_laps(session, driver2)
            if laps2.empty:
                raise ValueError("no laps found for that driver")

            current_stint_id_2 = laps2['Stint'].dropna().iloc[-1]
            stint2 = laps2[laps2['Stint'] == current_stint_id_2]
            clean2 = clean_stint(stint2)

            compound2 = stint2['Compound'].iloc[0]
            tyre_age2 = (
                int(stint2['TyreLife'].max())
                if stint2['TyreLife'].notna().any()
                else len(stint2)
            )
            mean_lap2 = clean2['t'].mean()
            slope2, intercept2 = degradation(stint2)
            tyre_deg2 = slope2 + FUEL_EFFECT
            base_next2 = slope2 * (stint2['LapNumber'].max() + 1) + intercept2

            comp_df = {
                "Driver": [driver, driver2],
                "Compound": [compound, compound2],
                "Tyre Age": [tyre_age, tyre_age2],
                "Deg (s/lap)": [round(tyre_deg, 3), round(tyre_deg2, 3)],
                "Mean Lap (s)": [round(mean_lap, 3), round(mean_lap2, 3)],
            }

            col_comp_left, col_comp_right = st.columns([1.1, 1.2])

            with col_comp_left:
                st.subheader("Stint Comparison")
                st.dataframe(comp_df, use_container_width=True)

                # Undercut / overcut
                st.subheader("Undercut / Overcut Analysis")

                gain_per_lap, laps_to_recover = undercut_analysis(
                    base_next, base_next2, pit_loss
                )

                st.write({
                    "Your next lap (old tyres)": round(base_next, 3),
                    "Rival next lap (old tyres)": round(base_next2, 3),
                    "Fresh-tyre gain vs rival (s/lap)": round(gain_per_lap, 3),
                    "Laps to recover pit loss": (
                        round(laps_to_recover, 1) if laps_to_recover else "never"
                    ),
                })

                if laps_to_recover is not None and laps_to_recover <= 10:
                    st.success("Undercut looks viable: fresh tyres recover the pit loss quickly.")
                else:
                    st.info("Staying out may be better (overcut potential).")

            with col_comp_right:
                st.subheader("Degradation Comparison")
                fig_compare = px.bar(
                    comp_df,
                    x="Driver",
                    y="Deg (s/lap)",
                    color="Driver",
                    template="plotly_dark",
                )
                fig_compare.update_layout(height=350, margin=dict(l=10, r=10, t=30, b=10))
                st.plotly_chart(fig_compare, use_container_width=True)

        except Exception as e:
            st.error(f"Could not load comparison driver '{driver2}': {e}")
    else:
        st.info("Enter a second driver code to enable multi‑driver and undercut/overcut analysis.")

    # ─────────────────────────
    # Explanations
    # ─────────────────────────
    with st.expander("What do these numbers and charts mean?"):
        st.markdown(
            """
            **Tyre Compound**  
            The rubber type currently on the car (Soft, Medium, Hard). Softer tyres are faster but degrade quicker.

            **Tyre Age**  
            How many laps the tyre has been used. Higher age usually means slower lap times.

            **Degradation (s/lap)**  
            The rate at which lap times change over the stint, corrected for the car getting lighter as fuel burns.  
            - Positive value → tyres are getting slower each lap  
            - Negative value → tyres are improving (warm‑up phase or track evolution)

            **Predicted Lap Times**  
            A projection of the next few laps based on the current lap-time trend.

            **Stay Out vs Pit Now**  
            A comparison of expected lap times if the driver continues versus if they pit immediately.  
            - *Stay Out*: expected pace on current tyres  
            - *Pit Now*: pit loss (first lap only) + pace on fresh tyres  
            - *Delta (cumulative)*: negative means pitting is ahead of staying out

            **Pit Window**  
            A simple indicator of whether a pit stop is likely beneficial soon.

            **Undercut / Overcut**  
            - *Undercut*: you pit earlier, gain time on fresh tyres while rival stays out  
            - *Overcut*: you stay out while rival pits, hoping your pace + track position offset their fresh‑tyre advantage
            """
        )
else:
    st.info("Set year, race, driver (and optional comparison driver), then click **Run Analysis**.")