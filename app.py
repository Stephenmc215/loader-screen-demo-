import random
import time
from dataclasses import dataclass
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
      .banner { border-radius: 18px; padding: 18px 18px; text-align:center; color:white; font-weight:900; font-size:44px; letter-spacing:0.2px; margin-bottom:14px; }
      .section-title { font-size: 34px; font-weight: 900; margin-top: 6px; margin-bottom: 10px; }
      .small-muted { color:#6b7280; font-size: 1.05rem; }
      .stMetric { background: #ffffff; border: 1px solid #e5e7eb; border-radius: 14px; padding: 14px 14px; }
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
# Scenario library (from your PDF)
# -----------------------------
# Each entry has:
# - display: how it should appear (drives colour + priority)
# - examples: more realistic underlying reasons (optional; we show some variety)
SCENARIOS = [
    {"display": "Moved to B", "examples": ["Change order to different pad"]},
    {"display": "Repress Pad", "examples": [
        "Mission validation failed (repress)",
        "Repress landing pad",
        "Pads forgotten to be pressed",
        "Insufficient departure time (repress)",
        "Missed takeoff (might not be required)",
    ]},
    {"display": "Change Cassette", "examples": [
        "Battery below arm temperature",
        "Missed res check",
        "Missed daily check",
        "Cassette firmware read failed (swap cassette)",
    ]},
    {"display": "Reboot Drone", "examples": [
        "Backup GNSS (case by case)",
        "Reboot required",
        "Stuck in maintenance (reboot)",
        "Telem loss (reboot)",
        "VMS/FCU sync (?)",
    ]},
    {"display": "Change Drone", "examples": [
        "Backup battery voltage too low (change craft)",
        "Missed aircraft daily check (change craft)",
    ]},
]

TOP_BAR_ALERTS = [
    "Wipe lidar (rain/fog + lidar abort)",
    "Space weather over limits",
    "Icing pre-flight checklist",
]

# Display action -> styling & priority
ACTION_STYLES = {
    "": {"severity": 0, "bg": None, "fg": None},
    "Moved to B": {"severity": 1, "bg": "#dbeafe", "fg": "black"},
    "Repress Pad": {"severity": 1, "bg": "#dbeafe", "fg": "black"},
    "Change Cassette": {"severity": 2, "bg": "#fde68a", "fg": "black"},
    "Reboot Drone": {"severity": 3, "bg": "#fdba74", "fg": "black"},
    "Change Drone": {"severity": 4, "bg": "#f87171", "fg": "white"},
}

# How long things "stick" on screen (seconds) so it doesn't flash for a split second
FAULT_DURATIONS = {
    "Moved to B": 60,
    "Repress Pad": 90,
    "Change Cassette": 180,
    "Reboot Drone": 120,
    "Change Drone": 240,
}

WEATHER_MESSAGES = [
    "Weather: OK",
    "Weather: Gusts possible",
    "Weather: Light rain",
    "Weather: Visibility OK",
]

PHASE_LABEL = {
    "FLIGHT": "In flight",
    "LANDING": "Landing",
    "LOADING": "Loading",
}

# Timing (seconds)
FLIGHT_MIN_S = 120   # 2 minutes
FLIGHT_MAX_S = 300   # 5 minutes
LANDING_S = 10
LOADING_S = 60       # ~1 minute on the ground to load

@dataclass
class PadState:
    pad: str
    order: int
    phase: str          # FLIGHT/LANDING/LOADING
    phase_t: int        # seconds remaining in phase
    next_action: str    # blank, numeric next order, or action display text
    fault_reason: str   # more descriptive reason (optional)
    fault_t: int        # seconds remaining for the fault (0 means none)

def next_order(n: int) -> int:
    n2 = n + 3
    return 100 if n2 > 999 else n2

def rand_flight_time() -> int:
    return random.randint(FLIGHT_MIN_S, FLIGHT_MAX_S)

def init_sim(num_pads: int = 8) -> dict:
    pads = []
    start = 100
    for i in range(num_pads):
        pad_letter = chr(ord("A") + i)
        # Stagger initial times so they don't align
        ft = rand_flight_time()
        ft = random.randint(20, ft)
        pads.append(PadState(
            pad=pad_letter,
            order=start,
            phase="FLIGHT",
            phase_t=ft,
            next_action="",
            fault_reason="",
            fault_t=0,
        ))
        start = next_order(start)

    return {
        "pads": pads,
        "cancelled": 0,
        "last_updated": "Just now",
        "rng_seed": random.randint(1, 10_000_000),
        "weather_i": 0,
        "topbar_i": 0,
        "last_banner": "",
    }

def ensure_state():
    if "sim" not in st.session_state:
        st.session_state.sim = init_sim(num_pads=8)
        random.seed(st.session_state.sim["rng_seed"])

def roll_fault(phase: str) -> tuple[str, str, int]:
    """
    Returns (display_action, reason, duration_seconds) or ("","",0)
    Tune probabilities so errors appear sometimes, but not constantly.
    """
    r = random.random()

    # Slightly higher chance of noticing issues while loading/landing
    if phase in ("LANDING", "LOADING"):
        if r < 0.020:
            s = next(x for x in SCENARIOS if x["display"] == "Repress Pad")
            return ("Repress Pad", random.choice(s["examples"]), FAULT_DURATIONS["Repress Pad"])
        if r < 0.030:
            s = next(x for x in SCENARIOS if x["display"] == "Change Cassette")
            return ("Change Cassette", random.choice(s["examples"]), FAULT_DURATIONS["Change Cassette"])
        if r < 0.036:
            s = next(x for x in SCENARIOS if x["display"] == "Reboot Drone")
            return ("Reboot Drone", random.choice(s["examples"]), FAULT_DURATIONS["Reboot Drone"])
        if r < 0.040:
            s = next(x for x in SCENARIOS if x["display"] == "Change Drone")
            return ("Change Drone", random.choice(s["examples"]), FAULT_DURATIONS["Change Drone"])
        if r < 0.048:
            s = next(x for x in SCENARIOS if x["display"] == "Moved to B")
            return ("Moved to B", random.choice(s["examples"]), FAULT_DURATIONS["Moved to B"])
        return ("", "", 0)

    # In flight: lower chance
    if r < 0.006:
        s = next(x for x in SCENARIOS if x["display"] == "Reboot Drone")
        return ("Reboot Drone", random.choice(s["examples"]), FAULT_DURATIONS["Reboot Drone"])
    if r < 0.009:
        s = next(x for x in SCENARIOS if x["display"] == "Change Cassette")
        return ("Change Cassette", random.choice(s["examples"]), FAULT_DURATIONS["Change Cassette"])
    if r < 0.010:
        s = next(x for x in SCENARIOS if x["display"] == "Change Drone")
        return ("Change Drone", random.choice(s["examples"]), FAULT_DURATIONS["Change Drone"])
    return ("", "", 0)

def maybe_topbar_alert(sim: dict) -> str:
    # Rare top bar alerts, rotate a bit when present
    # (kept off most of the time so it feels believable)
    if random.random() < 0.002:
        return random.choice(TOP_BAR_ALERTS)
    return ""

def step_sim():
    sim = st.session_state.sim
    pads: list[PadState] = sim["pads"]

    # Weather rotates only when there is no critical/high alert
    sim["weather_i"] = (sim["weather_i"] + 1) % (len(WEATHER_MESSAGES) * 6)

    for p in pads:
        # decrement phase timer
        p.phase_t = max(0, p.phase_t - TICK_SECONDS)

        # decrement fault timer (faults persist; don't flash)
        if p.fault_t > 0:
            p.fault_t = max(0, p.fault_t - TICK_SECONDS)
            if p.fault_t == 0:
                # fault resolved automatically (simulating someone completed the task)
                p.next_action = ""
                p.fault_reason = ""

        # Phase transitions
        if p.phase == "FLIGHT" and p.phase_t == 0:
            p.phase = "LANDING"
            p.phase_t = LANDING_S

        elif p.phase == "LANDING" and p.phase_t == 0:
            p.phase = "LOADING"
            p.phase_t = LOADING_S
            # Show upcoming order id while loading (if no fault)
            if p.next_action == "":
                p.next_action = str(next_order(p.order))

        elif p.phase == "LOADING" and p.phase_t == 0:
            # Only take off if there is no active fault
            if p.fault_t == 0 and p.next_action not in ("Moved to B", "Repress Pad", "Change Cassette", "Reboot Drone", "Change Drone"):
                p.order = next_order(p.order)
                p.next_action = ""
                p.phase = "FLIGHT"
                p.phase_t = rand_flight_time()
            else:
                # waiting for task completion; keep LOADING but show 0 so it feels "stuck until done"
                p.phase_t = 0

        # If a fault is active, keep showing it
        if p.fault_t > 0:
            continue

        # Otherwise maybe create a new fault
        act, reason, dur = roll_fault(p.phase)
        if act:
            p.next_action = act
            p.fault_reason = reason
            p.fault_t = dur
            continue

        # Otherwise, show next order id sometimes during landing/loading (if nothing else)
        if p.phase in ("LANDING", "LOADING") and p.next_action == "":
            if random.random() < 0.25:
                p.next_action = str(next_order(p.order))
        # If we had a numeric next order but now we're in flight, clear it
        if p.phase == "FLIGHT" and p.next_action.isdigit():
            p.next_action = ""

    sim["last_updated"] = "Just now"

def compute_banner(sim: dict) -> tuple[str, str]:
    pads: list[PadState] = sim["pads"]

    # 1) Any CRITICAL issue locks banner
    best = None
    for p in pads:
        a = p.next_action.strip()
        sev = ACTION_STYLES.get(a, {"severity": 0})["severity"]
        if best is None or sev > best["sev"]:
            best = {"sev": sev, "pad": p.pad, "action": a, "reason": p.fault_reason}

    if best and best["sev"] >= 4:
        return (f"CRITICAL: {best['action']} (Pad {best['pad']})", "#b91c1c")
    if best and best["sev"] == 3:
        return (f"HIGH: {best['action']} (Pad {best['pad']})", "#b45309")

    # 2) Occasional top-bar alert (only when no high/critical)
    alert = maybe_topbar_alert(sim)
    if alert:
        return (alert, "#b91c1c")

    # 3) Calm: rotate weather; if clear, show "RPP: 2 mins"
    msg = WEATHER_MESSAGES[(sim["weather_i"] // 6) % len(WEATHER_MESSAGES)]
    if msg == "Weather: OK":
        return ("RPP: 2 mins", "#1f3a8a")
    return (msg, "#1f3a8a")

def style_table(df: pd.DataFrame, actions: list[str]) -> pd.io.formats.style.Styler:
    def apply_styles(dataframe: pd.DataFrame):
        styles = pd.DataFrame("", index=dataframe.index, columns=dataframe.columns)
        for i, act in enumerate(actions):
            act = act.strip()
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

sim = st.session_state.sim
pads: list[PadState] = sim["pads"]

banner_text, banner_bg = compute_banner(sim)
st.markdown(f"<div class='banner' style='background:{banner_bg};'>{banner_text}</div>", unsafe_allow_html=True)

left, right = st.columns([1, 3.8], gap="large")

with left:
    st.markdown("<div class='section-title'>Base Status</div>", unsafe_allow_html=True)

    at_base = sum(1 for p in pads if p.phase in ("LANDING", "LOADING"))
    arriving = sum(1 for p in pads if p.phase == "FLIGHT")
    cancelled = sim.get("cancelled", 0)

    st.metric("At Base", at_base)
    st.metric("Arriving Soon", arriving)
    st.metric("Cancelled", cancelled)
    st.markdown(f"<div class='small-muted'>Last updated: {sim['last_updated']}</div>", unsafe_allow_html=True)

with right:
    st.markdown("<div class='section-title'>Pad Overview</div>", unsafe_allow_html=True)

    rows = []
    actions = []
    for p in pads:
        # If fault active, we show the display action (e.g. "Change Cassette") in Next Action.
        # Otherwise show blank or next order number during loading.
        rows.append({
            "Pad": p.pad,
            "Order": f"{p.order}",
            "Status": PHASE_LABEL.get(p.phase, p.phase),
            "T (s)": p.phase_t,
            "Next Action": p.next_action,
        })
        actions.append(p.next_action)

    df = pd.DataFrame(rows)
    styled = style_table(df, actions)

    st.dataframe(styled, use_container_width=True, hide_index=True, height=720)
