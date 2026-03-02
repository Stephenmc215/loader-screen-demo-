
import random
import time
from dataclasses import dataclass
from typing import Optional, List, Tuple

import streamlit as st

try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=1000, key="tick")
except Exception:
    pass

st.set_page_config(page_title="Loader Wall Screen", layout="wide")

SCENARIOS = [
    ("critical", "Change Drone", True),
    ("critical", "UA failure confirmed", True),
    ("high", "Reboot Drone", True),
    ("high", "Comms lost", True),
    ("warn", "Change Cassette", False),
    ("high", "Repress Pad", False),
]

LEVEL_ORDER = {"critical": 0, "high": 1, "warn": 2}

BAG_EMOJI = ["🔥", "🧊", "📦"]
WEATHER = ["Weather: Visibility OK", "Weather: Light rain", "Weather: Windy", "RPP: 2 mins"]


@dataclass
class Pad:
    name: str
    phase: str
    phase_end: float
    current: int
    next_order: int
    emoji: str
    scenario: Optional[Tuple[str, str, bool]] = None
    scenario_until: float = 0.0


def now():
    return time.monotonic()


def next_order_id(x):
    n = x + 3
    return 100 if n > 999 else n


def new_flight():
    return random.randint(120, 300)


def init_state():
    if "pads" in st.session_state:
        return
    pads = []
    base = 100
    t = now()
    for p in "ABCDEFGH":
        pads.append(
            Pad(
                name=p,
                phase="FLIGHT",
                phase_end=t + random.randint(10, 120) + new_flight(),
                current=base,
                next_order=next_order_id(base),
                emoji=random.choice(BAG_EMOJI),
            )
        )
        base = next_order_id(base)
    st.session_state.pads = pads


def maybe_scenario():
    if random.random() < 0.1:
        return random.choice(SCENARIOS)
    return None


def advance(p: Pad):
    if now() < p.phase_end:
        return

    if p.phase == "FLIGHT":
        p.phase = "LOADING"
        p.phase_end = now() + 60
        sc = maybe_scenario()
        if sc:
            p.scenario = sc
            p.scenario_until = p.phase_end
        return

    if p.phase == "LOADING":
        if p.scenario:
            p.phase = "FIXING"
            p.phase_end = now() + 30
            p.scenario_until = p.phase_end
            return
        p.phase = "FLIGHT"
        p.phase_end = now() + new_flight()
        p.current = p.next_order
        p.next_order = next_order_id(p.current)
        p.emoji = random.choice(BAG_EMOJI)
        p.scenario = None
        return

    if p.phase == "FIXING":
        p.phase = "FLIGHT"
        p.phase_end = now() + new_flight()
        p.current = p.next_order
        p.next_order = next_order_id(p.current)
        p.emoji = random.choice(BAG_EMOJI)
        p.scenario = None


def tick():
    for p in st.session_state.pads:
        advance(p)


def rt(p):
    if p.phase != "FLIGHT":
        return None
    return max(0, int(p.phase_end - now()))


def ground_left(p):
    if p.phase not in ["LOADING", "FIXING"]:
        return None
    return max(0, int(p.phase_end - now()))


init_state()
tick()
pads = st.session_state.pads

# Banner
banner = WEATHER[int(time.time() / 6) % len(WEATHER)]
for p in pads:
    if p.scenario and now() < p.scenario_until and p.scenario[2]:
        lvl, label, _ = p.scenario
        banner = f"{lvl.upper()}: {label} (Pad {p.name})"
        break

st.markdown(f"<h1 style='text-align:center'>{banner}</h1>", unsafe_allow_html=True)

# Priority target
def priority():
    active = [p for p in pads if p.phase in ["LOADING","FIXING"] and p.scenario and now()<p.scenario_until]
    if active:
        active.sort(key=lambda x: LEVEL_ORDER.get(x.scenario[0],9))
        return active[0]
    loading = [p for p in pads if p.phase in ["LOADING","FIXING"]]
    if loading:
        loading.sort(key=lambda x: ground_left(x))
        return loading[0]
    flights = [p for p in pads if p.phase=="FLIGHT"]
    flights.sort(key=lambda x: rt(x))
    return flights[0] if flights else None

target = priority()

left, right = st.columns([4,6])

with left:
    if not target:
        st.header("STATUS")
        st.subheader("All clear")
    else:
        if target.phase in ["LOADING","FIXING"]:
            if target.scenario and now()<target.scenario_until:
                st.header("ACTION REQUIRED")
                st.subheader(target.scenario[1])
            else:
                st.header("LOAD NOW")
                st.subheader(f"{ground_left(target)}s")
        else:
            st.header("GO TO PAD")
            st.subheader(f"{target.name} – Landing in {rt(target)}s")
        st.markdown(f"### {target.emoji} {target.next_order}")

with right:
    critical = [p for p in pads if p.scenario and p.scenario[0]=="critical" and now()<p.scenario_until]
    attention = [p for p in pads if p.scenario and p.scenario[0]!="critical" and now()<p.scenario_until]
    loading_now = [p for p in pads if p.phase in ["LOADING","FIXING"]]
    landing_soon = [p for p in pads if p.phase=="FLIGHT" and rt(p)<=60]
    inflight = [p for p in pads if p.phase=="FLIGHT" and rt(p)>60]

    def section(title, items):
        if not items:
            return
        st.markdown(f"## {title}")
        for p in items[:4]:
            if p.phase=="FLIGHT":
                st.write(f"{p.name} – {rt(p)}s • {p.emoji} {p.next_order}")
            else:
                st.write(f"{p.name} – {ground_left(p)}s • {p.emoji} {p.next_order}")

    section("🔴 CRITICAL", critical)
    section("⚠️ ATTENTION", attention)
    section("🟡 LOADING NOW", loading_now)
    section("🟠 LANDING SOON", landing_soon)
    section("✈️ IN FLIGHT", inflight)

st.markdown("---")
st.write(f"At Base: {len(loading_now)} | Arriving (<60s): {len(landing_soon)} | Cancelled: 0")
