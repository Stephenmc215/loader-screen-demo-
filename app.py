import random
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
      .block-container { padding-top: 0.45rem; padding-bottom: 0.6rem; padding-left: 1.0rem; padding-right: 1.0rem; max-width: 100% !important; }
      .banner { border-radius: 18px; padding: 18px 18px; text-align:center; color:white; font-weight:900; font-size:46px; letter-spacing:0.2px; margin-bottom:14px; }
      .section-title { font-size: 36px; font-weight: 900; margin-top: 6px; margin-bottom: 10px; }
      .small-muted { color:#6b7280; font-size: 1.05rem; }
      .stMetric { background: #ffffff; border: 1px solid #e5e7eb; border-radius: 14px; padding: 14px 14px; }
      /* Larger dataframe fonts */
      div[data-testid="stDataFrame"] thead tr th { font-size: 20px !important; }
      div[data-testid="stDataFrame"] tbody tr td { font-size: 26px !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

TICK_SECONDS = 2
st_autorefresh(interval=TICK_SECONDS * 1000, key="loader_refresh")

# -----------------------------
# Scenario library (ground-only notifications)
# -----------------------------
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

ACTION_STYLES = {
    "": {"severity": 0, "bg": None, "fg": None},
    "Moved to B": {"severity": 1, "bg": "#dbeafe", "fg": "black"},
    "Repress Pad": {"severity": 1, "bg": "#dbeafe", "fg": "black"},
    "Change Cassette": {"severity": 2, "bg": "#fde68a", "fg": "black"},
    "Reboot Drone": {"severity": 3, "bg": "#fdba74", "fg": "black"},
    "Change Drone": {"severity": 4, "bg": "#f87171", "fg": "white"},
}

# "Fix time" once an issue is detected on the ground (adds realism before takeoff)
FIX_DELAY_S = 30

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
    "FIXING": "Fixing",
}

# Timing (seconds)
FLIGHT_MIN_S = 120   # 2 minutes
FLIGHT_MAX_S = 300   # 5 minutes
LANDING_S = 10
LOADING_S = 60       # on the ground to load
FIXING_S = FIX_DELAY_S

@dataclass
class PadState:
    pad: str
    order: int
    phase: str
    phase_t: int
    next_action: str
    fault_reason: str
    fault_active: bool

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
        ft = rand_flight_time()
        ft = random.randint(20, ft)  # stagger start
        pads.append(PadState(pad=pad_letter, order=start, phase="FLIGHT", phase_t=ft,
                             next_action="", fault_reason="", fault_active=False))
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

def roll_ground_fault() -> tuple[str, str]:
    """
    Faults only occur while the craft is on the ground (LOADING).
    """
    r = random.random()
    # Tune: issues should appear sometimes, not constantly
    if r < 0.030:
        s = next(x for x in SCENARIOS if x["display"] == "Repress Pad")
        return ("Repress Pad", random.choice(s["examples"]))
    if r < 0.045:
        s = next(x for x in SCENARIOS if x["display"] == "Change Cassette")
        return ("Change Cassette", random.choice(s["examples"]))
    if r < 0.055:
        s = next(x for x in SCENARIOS if x["display"] == "Reboot Drone")
        return ("Reboot Drone", random.choice(s["examples"]))
    if r < 0.060:
        s = next(x for x in SCENARIOS if x["display"] == "Change Drone")
        return ("Change Drone", random.choice(s["examples"]))
    if r < 0.070:
        s = next(x for x in SCENARIOS if x["display"] == "Moved to B")
        return ("Moved to B", random.choice(s["examples"]))
    return ("", "")

def maybe_topbar_alert() -> str:
    # Rare, only when calm
    if random.random() < 0.002:
        return random.choice(TOP_BAR_ALERTS)
    return ""

def step_sim():
    sim = st.session_state.sim
    pads: list[PadState] = sim["pads"]
    sim["weather_i"] = (sim["weather_i"] + 1) % (len(WEATHER_MESSAGES) * 6)

    for p in pads:
        p.phase_t = max(0, p.phase_t - TICK_SECONDS)

        # Phase transitions
        if p.phase == "FLIGHT" and p.phase_t == 0:
            p.phase = "LANDING"
            p.phase_t = LANDING_S
            p.next_action = ""
            p.fault_active = False
            p.fault_reason = ""

        elif p.phase == "LANDING" and p.phase_t == 0:
            p.phase = "LOADING"
            p.phase_t = LOADING_S
            # During loading, show next order number as default task
            p.next_action = str(next_order(p.order))
            p.fault_active = False
            p.fault_reason = ""

        elif p.phase == "LOADING":
            # Ground-only notifications can trigger while loading
            if not p.fault_active:
                act, reason = roll_ground_fault()
                if act:
                    p.fault_active = True
                    p.next_action = act
                    p.fault_reason = reason
                    # When an issue happens on ground, we add a fixing phase after loading
            if p.phase_t == 0:
                if p.fault_active:
                    p.phase = "FIXING"
                    p.phase_t = FIXING_S
                else:
                    p.phase = "FLIGHT"
                    p.order = next_order(p.order)
                    p.phase_t = rand_flight_time()
                    p.next_action = ""
                    p.fault_reason = ""
                    p.fault_active = False

        elif p.phase == "FIXING" and p.phase_t == 0:
            # After fixing, take off
            p.phase = "FLIGHT"
            p.order = next_order(p.order)
            p.phase_t = rand_flight_time()
            p.next_action = ""
            p.fault_reason = ""
            p.fault_active = False

    sim["last_updated"] = "Just now"

def compute_banner(sim: dict) -> tuple[str, str]:
    pads: list[PadState] = sim["pads"]

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

    alert = maybe_topbar_alert()
    if alert:
        return (alert, "#b91c1c")

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

    at_base = sum(1 for p in pads if p.phase in ("LANDING", "LOADING", "FIXING"))
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
        # If on ground (Loading/Fixing/Landing), no RT shown
        rt = "" if p.phase in ("LANDING", "LOADING", "FIXING") else p.phase_t

        rows.append({
            "Pad": p.pad,
            "Order": f"{p.order}",
            "RT (s)": rt,
            "Status": PHASE_LABEL.get(p.phase, p.phase),
            "Next Action": p.next_action,
        })
        actions.append(p.next_action)

    df = pd.DataFrame(rows)

    # Make the grid "bigger" by giving it more vertical space and bigger fonts (above),
    # and ordering columns to match your preferred 4-column feel.
    df = df[["Pad", "Order", "RT (s)", "Next Action", "Status"]]

    styled = style_table(df, actions)
    st.dataframe(styled, use_container_width=True, hide_index=True, height=780)
