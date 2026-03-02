
import json
import time
from pathlib import Path
import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Loader Screen Demo", layout="wide")

st.markdown(
    """
    <style>
      .block-container { padding-top: 0.6rem; padding-bottom: 0.6rem; padding-left: 1.2rem; padding-right: 1.2rem; max-width: 100% !important; }
      h1, h2, h3 { margin-bottom: 0.35rem !important; }
      .small-muted { color: #6b7280; font-size: 0.9rem; }
      .banner { border-radius: 14px; padding: 16px 18px; text-align: center; color: white; font-weight: 800; font-size: 34px; letter-spacing: 0.2px; margin-bottom: 12px; }
      .section-title { font-size: 30px; font-weight: 800; margin-top: 6px; margin-bottom: 8px; }
      .stMetric { background: #ffffff; border: 1px solid #e5e7eb; border-radius: 12px; padding: 10px 12px; }
      div[data-testid="stDataFrame"] thead tr th { font-size: 14px; }
      div[data-testid="stDataFrame"] tbody tr td { font-size: 16px; }
    </style>
    """,
    unsafe_allow_html=True,
)

DATA_DIR = Path("data")

REFRESH_SECONDS = 5
st_autorefresh(interval=REFRESH_SECONDS * 1000, key="loader_refresh")

SCENARIOS = ["scenario_normal.json", "scenario_incident.json"]

def load_scenario(name: str) -> dict:
    with open(DATA_DIR / name, "r") as f:
        return json.load(f)

def pick_scenario() -> str:
    return SCENARIOS[int(time.time() / 30) % len(SCENARIOS)]

# Display action mapping (from the PDF scenarios)
ACTION_STYLES = {
    "Moved to X":      {"severity": 1, "bg": "#dbeafe", "fg": "black"},
    "Repress Pad":     {"severity": 1, "bg": "#dbeafe", "fg": "black"},
    "Change Cassette": {"severity": 2, "bg": "#fde68a", "fg": "black"},
    "Reboot Drone":    {"severity": 3, "bg": "#fdba74", "fg": "black"},
    "Change Drone":    {"severity": 4, "bg": "#f87171", "fg": "white"},
    "Right Column":    {"severity": 0, "bg": "#f3f4f6", "fg": "black"},
    "Top Bar":         {"severity": 5, "bg": "#b91c1c", "fg": "white"},
}

def banner_from_state(state: dict) -> str:
    alerts = state.get("top_bar_alerts") or []
    if alerts:
        return alerts[int(time.time() / 10) % len(alerts)]

    best = None
    for p in state.get("pads", []):
        display_action = (p.get("display_action") or "").strip()
        if not display_action:
            continue
        sev = ACTION_STYLES.get(display_action, {"severity": 0})["severity"]
        if best is None or sev > best["sev"]:
            best = {
                "sev": sev,
                "pad": p.get("pad", "?"),
                "action": display_action,
                "text": (p.get("next_action") or "").strip(),
            }

    if best is None or best["sev"] <= 0:
        return "Normal Operations"

    action_text = best["text"] if best["text"] else best["action"]
    if best["sev"] >= 4:
        return f"CRITICAL: {action_text} (Pad {best['pad']})"
    if best["sev"] == 3:
        return f"HIGH: {action_text} (Pad {best['pad']})"
    if best["sev"] == 2:
        return f"ATTN: {action_text} (Pad {best['pad']})"
    return f"{action_text} (Pad {best['pad']})"

def banner_color(title: str, state: dict) -> str:
    if state.get("top_bar_alerts"):
        return "#b91c1c"
    t = title.upper()
    if "CRITICAL" in t:
        return "#b91c1c"
    if "HIGH" in t:
        return "#b45309"
    return "#1f3a8a"

scenario_file = pick_scenario()
state = load_scenario(scenario_file)

title = banner_from_state(state)
st.markdown(
    f"<div class='banner' style='background:{banner_color(title, state)};'>{title}</div>",
    unsafe_allow_html=True,
)

left, right = st.columns([1, 3.6], gap="large")

with left:
    st.markdown("<div class='section-title'>Base Status</div>", unsafe_allow_html=True)
    st.metric("At Base", state["base"]["at_base"])
    st.metric("Arriving Soon", state["base"]["arriving_soon"])
    st.metric("Cancelled", state["base"]["cancelled"])
    st.markdown(f"<div class='small-muted'>Last updated: {state['meta']['last_updated']}</div>", unsafe_allow_html=True)

with right:
    st.markdown("<div class='section-title'>Pad Overview</div>", unsafe_allow_html=True)

    df = pd.DataFrame(state["pads"]).copy()
    df = df[["pad", "order", "rt", "next_action", "display_action"]]
    df = df.rename(columns={"pad": "Pad", "order": "Order", "rt": "RT", "next_action": "Next Action"})

    def style_next_action(dataframe: pd.DataFrame):
        styles = pd.DataFrame("", index=dataframe.index, columns=dataframe.columns)
        for i in range(len(dataframe)):
            display_action = str(dataframe.loc[i, "display_action"] or "").strip()
            next_text = str(dataframe.loc[i, "Next Action"] or "").strip()

            # blank or numeric (next order id) should not be highlighted
            if next_text == "" or next_text.isdigit():
                continue

            style = ACTION_STYLES.get(display_action)
            if style:
                styles.loc[i, "Next Action"] = f"background-color:{style['bg']};color:{style['fg']};font-weight:700;"
            else:
                styles.loc[i, "Next Action"] = "background-color:#f3f4f6;color:black;"

        return styles

    styled = df.style.apply(style_next_action, axis=None)
    styled = styled.hide(axis="columns", subset=["display_action"])

    st.dataframe(styled, use_container_width=True, hide_index=True, height=620)
