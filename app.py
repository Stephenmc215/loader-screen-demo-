import random
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import streamlit as st

# ============================================================
# Loader Wall Screen – Clean Layout + Moving Orders (demo)
# 16:9 grid:
#   Top strip (navy) 10%
#   Main: Primary (65%) | Status stack (35%)
#   Footer 8%: At Base | Arriving Soon | Cancelled
# Notes:
# - Arriving Soon = COLLECTING (collector has order)
# - At Base = AT_BASE (order at base waiting to be loaded)
# - Cancelled = 0 (demo)
# - Right stack: CRITICAL / ACTIVE-LOADING / QUEUE
# ============================================================

st.set_page_config(page_title="Loader Wall Screen", layout="wide")

# ----------------------------
# Demo configuration
# ----------------------------
PADS = list("ABCDEF")
ORDER_MIN, ORDER_MAX, ORDER_STEP = 200, 999, 1
STORAGE_EMOJI = ["🔥", "📦", "🧊"]

# Phase durations (seconds)
COLLECT_MIN, COLLECT_MAX = 25, 70
ATBASE_MIN, ATBASE_MAX = 12, 35
LOAD_MIN, LOAD_MAX = 20, 55
FIX_MIN, FIX_MAX = 25, 55

SIM_SPEED = 1  # how many simulation seconds elapse per real second tick

ALERT_CHANCE = 0.05
ALERT_MESSAGES = [
    "Heavy rain — wipe lidar",
    "Space weather over limits",
    "Icing pre-flight checklist",
    "Weather above limits — put everything in the heat",
    "Containment breach — grounding",
]

# ----------------------------
# Model
# ----------------------------
@dataclass
class PadState:
    pad: str
    phase: str  # COLLECTING | AT_BASE | LOADING | CRITICAL
    remaining: int
    order_id: int
    storage: str
    issue: Optional[str] = None


def _rand_dur(rng: random.Random, lo: int, hi: int) -> int:
    return rng.randint(lo, hi)


def _next_order(rng: random.Random) -> int:
    return rng.randint(ORDER_MIN, ORDER_MAX)


def init_state() -> Dict:
    seed = int(time.time())
    rng = random.Random(seed)

    pads: Dict[str, PadState] = {}
    for p in PADS:
        pads[p] = PadState(
            pad=p,
            phase="COLLECTING",
            remaining=_rand_dur(rng, COLLECT_MIN, COLLECT_MAX),
            order_id=_next_order(rng),
            storage=rng.choice(STORAGE_EMOJI),
        )

    return {
        "rng": rng,
        "pads": pads,
        "last_tick": time.time(),
        "wind": rng.randint(5, 10),
        "wind_next": time.time() + 8,
        "alert_msg": None,
        "alert_until": 0.0,
        "alert_next_check": time.time() + 6,
    }


def tick(state: Dict) -> None:
    now = time.time()
    last = state.get("last_tick", now)
    dt = int(now - last)
    if dt <= 0:
        return
    state["last_tick"] = now

    rng: random.Random = state["rng"]
    pads: Dict[str, PadState] = state["pads"]

    # Wind update (slow-ish)
    if now >= state.get("wind_next", 0):
        state["wind"] = rng.randint(5, 10)
        state["wind_next"] = now + 8

    # Alert logic: 5% chance to show an alert when we check; otherwise show RPP + wind.
    if now >= state.get("alert_next_check", 0):
        if rng.random() < ALERT_CHANCE:
            state["alert_msg"] = rng.choice(ALERT_MESSAGES)
            state["alert_until"] = now + 10  # show alert for ~10s
        else:
            # Only clear if not currently showing one
            if now >= state.get("alert_until", 0):
                state["alert_msg"] = None
        state["alert_next_check"] = now + 6

    # Expire alert when time is up
    if state.get("alert_msg") and now >= state.get("alert_until", 0):
        state["alert_msg"] = None

    # Simulate each second
    for _ in range(dt * SIM_SPEED):
        for ps in pads.values():
            ps.remaining = max(0, ps.remaining - 1)

            if ps.remaining != 0:
                continue

            # Transitions
            if ps.phase == "COLLECTING":
                ps.phase = "AT_BASE"
                ps.remaining = _rand_dur(rng, ATBASE_MIN, ATBASE_MAX)

            elif ps.phase == "AT_BASE":
                # Start loading; occasional issue routes to CRITICAL
                if rng.random() < 0.12:
                    ps.phase = "CRITICAL"
                    ps.issue = rng.choice([
                        "Comms lost",
                        "Repress pad",
                        "Unit expired",
                        "Change cassette",
                        "Reboot drone",
                    ])
                    ps.remaining = _rand_dur(rng, FIX_MIN, FIX_MAX)
                else:
                    ps.phase = "LOADING"
                    ps.issue = None
                    ps.remaining = _rand_dur(rng, LOAD_MIN, LOAD_MAX)

            elif ps.phase == "CRITICAL":
                # After fix, go back to loading with a short load time
                ps.phase = "LOADING"
                ps.issue = None
                ps.remaining = _rand_dur(rng, 12, 28)

            elif ps.phase == "LOADING":
                # Complete load -> collector takes next order
                ps.phase = "COLLECTING"
                ps.remaining = _rand_dur(rng, COLLECT_MIN, COLLECT_MAX)
                ps.order_id = _next_order(rng)
                ps.storage = rng.choice(STORAGE_EMOJI)


# ----------------------------
# Priority / UI selection
# ----------------------------
def pick_primary(pads: List[PadState]) -> Tuple[str, Optional[PadState], str]:
    critical = [p for p in pads if p.phase == "CRITICAL"]
    if critical:
        p = sorted(critical, key=lambda x: x.pad)[0]
        return "critical", p, p.issue or "Action required"

    loading = [p for p in pads if p.phase == "LOADING"]
    if loading:
        p = sorted(loading, key=lambda x: x.remaining)[0]
        return "loading", p, "Load order"

    at_base = [p for p in pads if p.phase == "AT_BASE"]
    if at_base:
        p = sorted(at_base, key=lambda x: x.remaining)[0]
        return "at_base", p, "Load order"

    return "calm", None, "All clear"


# ----------------------------
# Styles (sleeker, less blocky)
# ----------------------------
CSS = """
<style>
:root{
  --bg:#ffffff;
  --ink:#0b1320;
  --muted:#667085;
  --line:#e7ebf2;
  --navy:#1f3f8a;
  --shadow: 0 10px 30px rgba(16,24,40,0.06);

  --crit_bg:#fde8e8; --crit_ink:#7a1212;
  --act_bg:#fff6cc;  --act_ink:#6a5400;
  --q_bg:#f2f4f7;    --q_ink:#3b4350;
}

/* Streamlit page */
.main .block-container{max-width: 1650px; padding-top: 0.9rem; padding-bottom: 1.0rem;}

/* Top strip (10% height) */
.topstrip{
  height: 10vh; min-height: 68px; max-height: 96px;
  background: var(--navy);
  color: #fff;
  border-radius: 18px;
  padding: 16px 22px;
  display:flex;
  align-items:center;
  justify-content:space-between;
  font-weight: 900;
  letter-spacing: 0.2px;
  box-shadow: var(--shadow);
}
.topstrip .left{font-size: clamp(22px, 2.1vw, 34px);}
.topstrip .right{font-size: clamp(20px, 1.9vw, 30px); opacity: 0.92;}

.topstrip.alert{background:#b51d1d;}

/* Grid */
.grid{
  margin-top: 12px;
  display:grid;
  grid-template-columns: 65% 35%;
  grid-template-rows: 82vh 8vh;
  gap: 14px;
}

/* Primary */
.primary{
  grid-column: 1; grid-row: 1;
  background:#fff;
  border: 2px solid var(--line);
  border-radius: 18px;
  padding: 34px 34px;
  display:flex;
  flex-direction:column;
  justify-content:center;
  overflow:hidden;
}
.kicker{
  font-size: clamp(18px, 1.9vw, 28px);
  font-weight: 900;
  letter-spacing: 0.8px;
  color: #9aa3b2;
  margin-bottom: 18px;
}
.bigrow{display:flex; align-items:center; gap: 28px; margin: 4px 0 18px 0;}
.arrow{font-size: clamp(84px, 7vw, 150px); font-weight: 900; color: var(--ink); opacity: 0.95;}
.padbig{font-size: clamp(150px, 12vw, 280px); font-weight: 1000; color: var(--ink); letter-spacing: -2px;}
.actiontext{font-size: clamp(44px, 4.2vw, 88px); font-weight: 1000; color: var(--ink); line-height: 1.04;}
.subline{margin-top: 14px; font-size: clamp(18px, 1.9vw, 30px); font-weight: 800; color: var(--muted);}
.smallmeta{margin-top: 18px; font-size: clamp(20px, 2.0vw, 32px); font-weight: 900; color: var(--muted);}

/* Stack */
.stack{
  grid-column: 2; grid-row: 1;
  display:flex;
  flex-direction:column;
  gap: 12px;
  overflow:hidden;
}
.section{
  border: 2px solid var(--line);
  border-radius: 18px;
  background:#fff;
  overflow:hidden;
}
.section-h{
  padding: 14px 16px;
  font-size: clamp(18px, 1.6vw, 26px);
  font-weight: 1000;
  letter-spacing: 0.6px;
  display:flex;
  align-items:center;
  gap: 10px;
}
.dot{width: 18px; height: 18px; border-radius: 999px; background: rgba(0,0,0,0.18);}
.h-critical{background: var(--crit_bg); color: var(--crit_ink);} 
.h-active{background: var(--act_bg); color: var(--act_ink);} 
.h-queue{background: var(--q_bg); color: var(--q_ink);} 

.items{padding: 12px; display:flex; flex-direction:column; gap: 10px;}
.item{
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 12px 12px;
  display:flex;
  align-items:center;
  justify-content:space-between;
  background:#fff;
}
.item-left{display:flex; align-items:center; gap: 12px; min-width: 0;}
.pad{
  width: 50px; height: 50px;
  border-radius: 14px;
  border: 1px solid rgba(0,0,0,0.10);
  background:#fff;
  display:flex;
  align-items:center;
  justify-content:center;
  font-weight: 900;
  font-size: 22px;
  color: var(--ink);
  flex: 0 0 auto;
}
.desc{
  font-size: clamp(16px, 1.55vw, 24px);
  font-weight: 900;
  color: var(--ink);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.meta{
  font-size: clamp(16px, 1.55vw, 24px);
  font-weight: 900;
  color: var(--muted);
  flex: 0 0 auto;
}
.more{margin-top: 2px; color: var(--muted); font-weight: 900; font-size: clamp(14px, 1.35vw, 20px);}

/* Footer */
.footer{
  grid-column: 1 / span 2;
  grid-row: 2;
  height: 8vh;
  min-height: 52px;
  max-height: 78px;
  border: 2px solid var(--line);
  border-radius: 18px;
  padding: 10px 16px;
  background:#fff;
  display:flex;
  align-items:center;
  justify-content:space-between;
  color: var(--muted);
  font-weight: 900;
  font-size: clamp(16px, 1.5vw, 22px);
}
.footer .k{color:#8a93a3; margin-right:10px; font-weight: 1000;}
</style>
"""


def render_item(p: PadState, label: str, meta: str) -> str:
    return (
        '<div class="item">'
        f'<div class="item-left"><div class="pad">{p.pad}</div><div class="desc">{label}</div></div>'
        f'<div class="meta">{meta}</div>'
        '</div>'
    )


def section(title: str, header_cls: str, dot_color: str, body_html: str) -> str:
    return (
        '<div class="section">'
        f'<div class="section-h {header_cls}"><span class="dot" style="background:{dot_color}"></span>{title}</div>'
        f'<div class="items">{body_html}</div>'
        '</div>'
    )


def capped_list(items_html: List[str], cap: int = 3) -> str:
    if not items_html:
        return '<div class="desc" style="color:#6b7483; font-weight:800;">None</div>'
    shown = items_html[:cap]
    extra = len(items_html) - len(shown)
    out = "".join(shown)
    if extra > 0:
        out += f'<div class="more">+{extra} more</div>'
    return out


# ----------------------------
# App runtime
# ----------------------------
if "wall_state" not in st.session_state:
    st.session_state["wall_state"] = init_state()

state = st.session_state["wall_state"]

try:
    from streamlit_autorefresh import st_autorefresh

    st_autorefresh(interval=1000, key="tick")
except Exception:
    pass

tick(state)

pads_list = list(state["pads"].values())
kind, primary_pad, primary_label = pick_primary(pads_list)

# Footer metrics
at_base = sum(1 for p in pads_list if p.phase == "AT_BASE")
arriving_soon = sum(1 for p in pads_list if p.phase == "COLLECTING")
cancelled = 0

# Top strip
wind_ms = state.get("wind", 7)
alert_msg = state.get("alert_msg")

st.markdown(CSS, unsafe_allow_html=True)

if alert_msg:
    top_html = f'<div class="topstrip alert"><div class="left">{alert_msg}</div><div class="right">Wind: {wind_ms} m/s</div></div>'
else:
    top_html = f'<div class="topstrip"><div class="left">RPP: 2 mins</div><div class="right">Wind: {wind_ms} m/s</div></div>'

# Primary block
if kind == "critical" and primary_pad is not None:
    primary_html = (
        '<div class="primary">'
        '<div class="kicker">NEXT ACTION</div>'
        f'<div class="bigrow"><div class="arrow">→</div><div class="padbig">{primary_pad.pad}</div></div>'
        f'<div class="actiontext">{primary_label}</div>'
        f'<div class="smallmeta">{primary_pad.storage} {primary_pad.order_id}</div>'
        f'<div class="subline">Fix time: {primary_pad.remaining}s</div>'
        '</div>'
    )
elif kind in ("loading", "at_base") and primary_pad is not None:
    primary_html = (
        '<div class="primary">'
        '<div class="kicker">NEXT ACTION</div>'
        f'<div class="bigrow"><div class="arrow">→</div><div class="padbig">{primary_pad.pad}</div></div>'
        '<div class="actiontext">Load order</div>'
        f'<div class="smallmeta">{primary_pad.storage} {primary_pad.order_id}</div>'
        f'<div class="subline">{primary_pad.phase.replace("_"," ").title()} • {primary_pad.remaining}s</div>'
        '</div>'
    )
else:
    primary_html = (
        '<div class="primary">'
        '<div class="kicker">NEXT ACTION</div>'
        '<div class="bigrow"><div class="arrow">→</div><div class="padbig">—</div></div>'
        '<div class="actiontext">All clear</div>'
        '<div class="subline">Waiting for next order</div>'
        '</div>'
    )

# Right stack sections
critical_items = []
for p in sorted([x for x in pads_list if x.phase == "CRITICAL"], key=lambda x: x.pad):
    critical_items.append(render_item(p, p.issue or "Issue", f"{p.storage} {p.order_id}"))

active_items = []
for p in sorted([x for x in pads_list if x.phase == "LOADING"], key=lambda x: x.remaining):
    active_items.append(render_item(p, f"{p.remaining}s", f"{p.storage} {p.order_id}"))

queue_items = []
# Queue = at base first (needs attention soon), then collecting
for p in sorted([x for x in pads_list if x.phase == "AT_BASE"], key=lambda x: x.remaining):
    queue_items.append(render_item(p, "At base", f"{p.storage} {p.order_id}"))
for p in sorted([x for x in pads_list if x.phase == "COLLECTING"], key=lambda x: x.remaining):
    queue_items.append(render_item(p, f"Arriving in {p.remaining}s", f"{p.storage} {p.order_id}"))

critical_html = section("CRITICAL", "h-critical", "#d92d20", capped_list(critical_items, 3))
active_html = section("ACTIVE / LOADING", "h-active", "#fdb022", capped_list(active_items, 3))
queue_html = section("QUEUE", "h-queue", "#98a2b3", capped_list(queue_items, 3))

stack_html = f'<div class="stack">{critical_html}{active_html}{queue_html}</div>'

footer_html = (
    '<div class="footer">'
    f'<div><span class="k">At Base</span>{at_base}</div>'
    f'<div><span class="k">Arriving Soon</span>{arriving_soon}</div>'
    f'<div><span class="k">Cancelled</span>{cancelled}</div>'
    '</div>'
)

grid_html = f'<div class="grid">{primary_html}{stack_html}{footer_html}</div>'

st.markdown(top_html + grid_html, unsafe_allow_html=True)
