import random
from dataclasses import dataclass
import streamlit as st
import pandas as pd
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Loader Screen Demo", layout="wide")

# -----------------------------
# UI tuning (MAXIMISE TABLE SIZE)
# -----------------------------
st.markdown(
    """
    <style>
      .block-container {
        padding-top: 0.3rem;
        padding-bottom: 0.3rem;
        padding-left: 0.8rem;
        padding-right: 0.8rem;
        max-width: 100% !important;
      }

      .banner {
        border-radius: 18px;
        padding: 20px;
        text-align:center;
        color:white;
        font-weight:900;
        font-size:50px;
        margin-bottom:18px;
      }

      .section-title {
        font-size: 40px;
        font-weight: 900;
        margin-bottom: 10px;
      }

      /* MASSIVE TABLE TEXT */
      div[data-testid="stDataFrame"] thead tr th {
          font-size: 26px !important;
          padding-top: 14px !important;
          padding-bottom: 14px !important;
      }

      div[data-testid="stDataFrame"] tbody tr td {
          font-size: 34px !important;
          padding-top: 18px !important;
          padding-bottom: 18px !important;
      }

      .stMetric {
        font-size: 28px !important;
      }

    </style>
    """,
    unsafe_allow_html=True,
)

TICK_SECONDS = 2
st_autorefresh(interval=TICK_SECONDS * 1000, key="loader_refresh")

# -----------------------------
# Simple realistic model (ground-only faults)
# -----------------------------

ACTION_STYLES = {
    "": {"severity": 0, "bg": None, "fg": None},
    "Moved to B": {"severity": 1, "bg": "#dbeafe", "fg": "black"},
    "Repress Pad": {"severity": 1, "bg": "#dbeafe", "fg": "black"},
    "Change Cassette": {"severity": 2, "bg": "#fde68a", "fg": "black"},
    "Reboot Drone": {"severity": 3, "bg": "#fdba74", "fg": "black"},
    "Change Drone": {"severity": 4, "bg": "#f87171", "fg": "white"},
}

PHASE_LABEL = {
    "FLIGHT": "In flight",
    "LANDING": "Landing",
    "LOADING": "Loading",
    "FIXING": "Fixing",
}

FLIGHT_MIN = 120
FLIGHT_MAX = 300
LANDING = 10
LOADING = 60
FIXING = 30

@dataclass
class Pad:
    pad: str
    order: int
    phase: str
    t: int
    action: str
    fault: bool

def next_order(n):
    return 100 if n+3 > 999 else n+3

def rand_flight():
    return random.randint(FLIGHT_MIN, FLIGHT_MAX)

def init():
    pads = []
    o = 100
    for i in range(8):
        pads.append(Pad(chr(65+i), o, "FLIGHT", random.randint(20, rand_flight()), "", False))
        o = next_order(o)
    return pads

if "pads" not in st.session_state:
    st.session_state.pads = init()

pads = st.session_state.pads

# --- SIM STEP ---
for p in pads:
    p.t = max(0, p.t - TICK_SECONDS)

    if p.phase == "FLIGHT" and p.t == 0:
        p.phase = "LANDING"
        p.t = LANDING

    elif p.phase == "LANDING" and p.t == 0:
        p.phase = "LOADING"
        p.t = LOADING
        p.action = str(next_order(p.order))

    elif p.phase == "LOADING":
        # Ground-only fault chance
        if not p.fault and random.random() < 0.04:
            p.fault = True
            p.phase = "FIXING"
            p.t = FIXING
            p.action = random.choice(["Repress Pad","Change Cassette","Reboot Drone","Change Drone"])

        if p.t == 0 and not p.fault:
            p.phase = "FLIGHT"
            p.order = next_order(p.order)
            p.t = rand_flight()
            p.action = ""

    elif p.phase == "FIXING" and p.t == 0:
        p.phase = "FLIGHT"
        p.order = next_order(p.order)
        p.t = rand_flight()
        p.action = ""
        p.fault = False

# -----------------------------
# Banner
# -----------------------------
critical = None
for p in pads:
    sev = ACTION_STYLES.get(p.action, {"severity":0})["severity"]
    if sev >= 3:
        critical = (p.action, p.pad)
        break

if critical:
    text = f"HIGH: {critical[0]} (Pad {critical[1]})"
    colour = "#b45309"
else:
    text = "RPP: 2 mins"
    colour = "#1f3a8a"

st.markdown(f"<div class='banner' style='background:{colour};'>{text}</div>", unsafe_allow_html=True)

left, right = st.columns([1,4], gap="large")

with left:
        at_base = sum(1 for p in pads if p.phase in ("LANDING","LOADING","FIXING"))
    arriving = sum(1 for p in pads if p.phase=="FLIGHT")
    st.metric("At Base", at_base)
    st.metric("Arriving Soon", arriving)
    st.metric("Cancelled", 0)

with right:
    
    rows = []
    actions = []
    for p in pads:
        rt = "" if p.phase in ("LANDING","LOADING","FIXING") else p.t
        rows.append({
            "Pad": p.pad,
            "Order": p.order,
            "RT (s)": rt,
            "Next Action": p.action,
        })
        actions.append(p.action)

    df = pd.DataFrame(rows)

    def style(df):
        styles = pd.DataFrame("", index=df.index, columns=df.columns)
        for i, a in enumerate(actions):
            if a in ACTION_STYLES and ACTION_STYLES[a]["bg"]:
                styles.loc[i, "Next Action"] = f"background:{ACTION_STYLES[a]['bg']};color:{ACTION_STYLES[a]['fg']};font-weight:900;"
        return styles

    styled = df.style.apply(style, axis=None)

    # VERY TALL GRID
    st.dataframe(styled, use_container_width=True, hide_index=True, height=1000)
