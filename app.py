import random
import time
from dataclasses import dataclass, asdict
import streamlit as st
import pandas as pd
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Loader Screen Demo", layout="wide")

# -----------------------------
# UI tuning (bigger text + full width)
# -----------------------------
st.markdown(
    """
    <style>
      .block-container { padding-top: 0.5rem; padding-bottom: 0.6rem; padding-left: 1.0rem; padding-right: 1.0rem; max-width: 100% !important; }
      h1, h2, h3 { margin-bottom: 0.2rem !important; }
      .banner { border-radius: 18px; padding: 18px 18px; text-align:center; color:white; font-weight:900; font-size:42px; letter-spacing:0.2px; margin-bottom:14px; }
      .section-title { font-size: 34px; font-weight: 900; margin-top: 6px; margin-bottom: 10px; }
      .small-muted { color:#6b7280; font-size: 1.05rem; }
      .stMetric { background: #ffffff; border: 1px solid #e5e7eb; border-radius: 14px; padding: 14px 14px; }
      /* Dataframe font sizes */
      div[data-testid="stDataFrame"] thead tr th { font-size: 18px !important; }
      div[data-testid="stDataFrame"] tbody tr td { font-size: 22px !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

# Auto-refresh: feels "live" on a monitor
TICK_SECONDS = 2
st_autorefresh(interval=TICK_SECONDS * 1000, key="loader_refresh")

# -----------------------------
# Simulation model
# -----------------------------
ACTION_STYLES = {
    "": {"severity": 0, "bg": None, "fg": None},
    "Moved to B": {"severity": 1, "bg": "#dbeafe", "fg": "black"},
    "Repress Pad": {"severity": 1, "bg": "#dbeafe", "fg": "black"},
    "Change Cassette": {"severity": 2, "bg": "#fde68a", "fg": "black"},
    "Reboot Drone": {"severity": 3, "bg": "#fdba74", "fg": "black"},
    "Change Drone": {"severity": 4, "bg": "#f87171", "fg": "white"},
}

WEATHER_MESSAGES = [
    "Weather: OK",
    "Weather: Gusts possible",
    "Weather: Light rain",
    "Weather: Visibility OK",
]

PHASE_LABEL = {
    "GROUND": "On ground",
    "FLIGHT": "In flight",
    "LANDING": "Landing",
}

@dataclass
class PadState:
    pad: str
    order: int | None
    phase: str  # GROUND/FLIGHT/LANDING
    phase_t: int  # seconds remaining in phase
    next_action: str  # may be blank or next order number str or action text
    # internal flags
    blocked: bool = False

def next_order(n: int) -> int:
    # 100, 103, 106 ... 999 then wrap to 100
    n2 = n + 3
    return 100 if n2 > 999 else n2

def init_sim(num_pads: int = 8) -> dict:
    pads = []
    start = 100
    for i in range(num_pads):
        pad_letter = chr(ord("A") + i)
        pads.append(PadState(pad=pad_letter, order=start, phase="FLIGHT", phase_t=60, next_action=""))
        start = next_order(start)
    return {
        "pads": pads,
        "cancelled": 0,
        "last_updated": "Just now",
        "rng_seed": random.randint(1, 10_000_000),
        "weather_i": 0,
    }

def ensure_state():
    if "sim" not in st.session_state:
        st.session_state.sim = init_sim(num_pads=8)
        random.seed(st.session_state.sim["rng_seed"])

def maybe_fault_on_flight() -> str:
    # Small chance per tick; tuned for “something happens sometimes” on demos.
    # Tick=2s -> 30 ticks/min. 2% per minute ≈ 0.00068 per tick.
    r = random.random()
    if r < 0.0010:
        return "Change Drone"
    if r < 0.0030:
        return "Reboot Drone"
    if r < 0.0060:
        return "Change Cassette"
    if r < 0.0100:
        return "Repress Pad"
    return ""

def maybe_fault_on_ground() -> str:
    r = random.random()
    if r < 0.0020:
        return "Moved to B"
    if r < 0.0050:
        return "Repress Pad"
    return ""

def step_sim():
    sim = st.session_state.sim
    pads: list[PadState] = sim["pads"]

    # Weather rotates only when there is no critical/high alert
    sim["weather_i"] = (sim["weather_i"] + 1) % (len(WEATHER_MESSAGES) * 5)  # slow rotation

    for p in pads:
        # countdown
        p.phase_t = max(0, p.phase_t - TICK_SECONDS)

        # phase transitions
        if p.phase == "FLIGHT" and p.phase_t == 0:
            p.phase = "LANDING"
            p.phase_t = 6  # landing window
        elif p.phase == "LANDING" and p.phase_t == 0:
            # landed -> load next order, back to flight
            if p.order is None:
                p.order = 100
            p.order = next_order(p.order)
            p.next_action = ""  # clear any old numeric/placeholder
            p.phase = "FLIGHT"
            p.phase_t = 60

        # decide next action
        # If next_action is a number (next order), keep it.
        if p.next_action.isdigit():
            continue

        # faults depend on phase
        fault = ""
        if p.phase == "FLIGHT":
            fault = maybe_fault_on_flight()
        else:
            fault = maybe_fault_on_ground()

        # Apply fault as next action text (or keep blank most of the time)
        p.next_action = fault

        # Sometimes show “next order to load” while on ground/landing
        if p.next_action == "" and p.phase in ("LANDING",) and random.random() < 0.15:
            # show upcoming order id
            nxt = next_order(p.order or 100)
            p.next_action = str(nxt)

    sim["last_updated"] = "Just now"

def compute_banner(pads: list[PadState]) -> tuple[str, str]:
    # If any critical action exists, keep it on top bar.
    best = None
    for p in pads:
        a = p.next_action.strip()
        sev = ACTION_STYLES.get(a, {"severity": 0})["severity"]
        if best is None or sev > best["sev"]:
            best = {"sev": sev, "pad": p.pad, "action": a}

    if best and best["sev"] >= 4:
        return (f"CRITICAL: {best['action']} (Pad {best['pad']})", "#b91c1c")
    if best and best["sev"] == 3:
        return (f"HIGH: {best['action']} (Pad {best['pad']})", "#b45309")
    if best and best["sev"] == 2:
        return (f"ATTN: {best['action']} (Pad {best['pad']})", "#1f3a8a")

    # otherwise rotate weather
    sim = st.session_state.sim
    msg = WEATHER_MESSAGES[(sim["weather_i"] // 5) % len(WEATHER_MESSAGES)]
    return (msg, "#1f3a8a")

def style_table(df: pd.DataFrame, actions: list[str]) -> pd.io.formats.style.Styler:
    def apply_styles(dataframe: pd.DataFrame):
        styles = pd.DataFrame("", index=dataframe.index, columns=dataframe.columns)
        for i, act in enumerate(actions):
            act = act.strip()
            # Blank or numeric should not be highlighted
            if act == "" or act.isdigit():
                continue
            s = ACTION_STYLES.get(act)
            if s and s["bg"]:
                styles.loc[i, "Next Action"] = f"background-color:{s['bg']};color:{s['fg']};font-weight:900;"
        return styles
    return df.style.apply(apply_styles, axis=None)

# -----------------------------
# Run simulation
# -----------------------------
ensure_state()
step_sim()

pads: list[PadState] = st.session_state.sim["pads"]

banner_text, banner_bg = compute_banner(pads)
st.markdown(f"<div class='banner' style='background:{banner_bg};'>{banner_text}</div>", unsafe_allow_html=True)

left, right = st.columns([1, 3.8], gap="large")

with left:
    st.markdown("<div class='section-title'>Base Status</div>", unsafe_allow_html=True)

    at_base = sum(1 for p in pads if p.phase != "FLIGHT")
    arriving = sum(1 for p in pads if p.phase == "FLIGHT")
    cancelled = st.session_state.sim.get("cancelled", 0)

    st.metric("At Base", at_base)
    st.metric("Arriving Soon", arriving)
    st.metric("Cancelled", cancelled)
    st.markdown(f"<div class='small-muted'>Last updated: {st.session_state.sim['last_updated']}</div>", unsafe_allow_html=True)

with right:
    st.markdown("<div class='section-title'>Pad Overview</div>", unsafe_allow_html=True)

    rows = []
    actions = []
    for p in pads:
        rows.append({
            "Pad": p.pad,
            "Order": "" if p.order is None else f"{p.order}",
            "Status": PHASE_LABEL.get(p.phase, p.phase),
            "T (s)": p.phase_t,
            "Next Action": p.next_action,
        })
        actions.append(p.next_action)

    df = pd.DataFrame(rows)
    styled = style_table(df, actions)

    st.dataframe(styled, use_container_width=True, hide_index=True, height=700)
