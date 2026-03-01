
import json
import time
from pathlib import Path

import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Loader Screen Demo", layout="wide")

DATA_DIR = Path("data")

# Auto refresh every 5 seconds
REFRESH_SECONDS = 5
st_autorefresh(interval=REFRESH_SECONDS * 1000, key="loader_refresh")

SCENARIOS = [
    "scenario_normal.json",
    "scenario_incident.json",
]

def load_scenario(name: str) -> dict:
    with open(DATA_DIR / name, "r") as f:
        return json.load(f)

def pick_scenario() -> str:
    idx = int(time.time() / 30) % len(SCENARIOS)
    return SCENARIOS[idx]

scenario_file = pick_scenario()
state = load_scenario(scenario_file)

# Banner
st.markdown(
    f"""
    <div style='background-color:#b91c1c;padding:20px;border-radius:10px;text-align:center;color:white;font-size:32px;font-weight:bold;'>
        {state['banner']['title']}
    </div>
    """,
    unsafe_allow_html=True,
)

st.divider()

status_col, main_col = st.columns([1, 4])

with status_col:
    st.markdown("## Base Status")
    st.metric("At Base", state["base"]["at_base"])
    st.metric("Arriving Soon", state["base"]["arriving_soon"])
    st.metric("Cancelled", state["base"]["cancelled"])
    st.caption(f"Last updated: {state['meta']['last_updated']}")

with main_col:
    st.markdown("## Pad Overview")

    df = pd.DataFrame(state["pads"])
    df = df[["pad", "order", "rt", "next_action", "action_level"]]

    def action_style(level: str) -> str:
        if level == "info":
            return "background-color:#dbeafe;color:black;"
        if level == "warn":
            return "background-color:#fde68a;color:black;"
        if level == "high":
            return "background-color:#fdba74;color:black;"
        if level == "critical":
            return "background-color:#f87171;color:white;"
        return ""

    def style_actions(dataframe: pd.DataFrame):
        styles = pd.DataFrame("", index=dataframe.index, columns=dataframe.columns)
        for i in range(len(dataframe)):
            styles.loc[i, "next_action"] = action_style(str(dataframe.loc[i, "action_level"]))
        return styles

    styled = df.style.apply(style_actions, axis=None)

    st.dataframe(
        styled,
        use_container_width=True,
        hide_index=True,
        height=450,
    )

    st.markdown("## Priority Actions")
    for item in state["priority"]:
        st.markdown(f"**{item['rank']} Pad {item['pad']} — {item['reason']}**")
        st.markdown(f"➡️ {item['action']}")
        st.markdown("---")
