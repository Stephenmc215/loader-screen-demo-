import time
import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import streamlit as st

# ============================================================
# LOADER WALL SCREEN – V16 (stable)
# 16:9 wall grid: Top 10% • Main 82% (65/35) • Footer 8%
# Pastel V10-style colours (light UI), neutral top strip.
#
# Order pipeline language:
# - COLLECTING = collector currently carrying orders (Arriving Soon metric)
# - ARRIVING   = order arriving to base imminently (countdown)
# - AT_BASE    = at base being loaded
#
# Priority (locked):
# 1) CRITICAL issue (AT_BASE)
# 2) ATTENTION issue (AT_BASE)
# 3) ACTIVE / LOADING (AT_BASE)
# 4) ARRIVING soon (ARRIVING <= 60s)
# 5) Calm
# ============================================================

st.set_page_config(page_title="Loader Wall Screen", layout="wide")

# ----------------------------
# Config
# ----------------------------
PADS = list("ABCDEFGH")

ORDER_MIN = 100
ORDER_MAX = 999
ORDER_STEP = 3

# Phase durations (seconds)
AT_BASE_SECONDS = 60
FIX_EXTRA_SECONDS = 30
COLLECTING_MIN = 60
COLLECTING_MAX = 180
ARRIVING_MIN = 5
ARRIVING_MAX = 30

ARRIVING_SOON_THRESHOLD = 60  # affects priority selection only

# Make it feel live
SIM_SPEED = 2
INITIAL_COLLECTING_MIN = 10
INITIAL_COLLECTING_MAX = 80

# Top strip
RPP_TEXT = "RPP: 2 mins"
WEATHER_ROTATE_SECONDS = 6
WEATHER_MESSAGES = [
    "Weather: Visibility OK",
    "Weather: Light rain",
    "Weather: Wind 12kt",
    "Weather: Temps stable",
]



# Top bar behaviour (demo)
TOPBAR_ALERT_RATE = 0.05  # 5% of the time show an alert
WIND_MIN_MS = 5
WIND_MAX_MS = 10

TOPBAR_ALERT_IDS = [
    "wipe_lidar",
    "space_weather",
    "icing_checklist",
    "weather_above_limits",
    "containment_breach",
]
TOPBAR_ALERT_TEXT = {
    "wipe_lidar": "WIPE LIDAR",
    "space_weather": "SPACE WEATHER OVER LIMITS",
    "icing_checklist": "ICING PRE-FLIGHT CHECKLIST",
    "weather_above_limits": "WEATHER ABOVE LIMITS • PUT EVERYTHING IN THE HEAT",
    "containment_breach": "CONTAINMENT BREACH • GROUNDING",
}
# Top bar alert logic (from Loader Screen PDF)
ALERT_HOLD_SECONDS = 300   # 5 mins (Containment breach grounding holds)
ALERT_BRIEF_SECONDS = 90   # short advisory hold for demo

TOPBAR_ALERTS_ORDER = [
    "containment_breach",
    "wipe_lidar",
    "space_weather",
    "icing_checklist",
    "weather_above_limits",
]

TOPBAR_ALERT_TEXT = {
    "wipe_lidar": "WIPE LIDAR",
    "space_weather": "SPACE WEATHER OVER LIMITS",
    "icing_checklist": "ICING PRE-FLIGHT CHECKLIST",
    "weather_above_limits": "WEATHER ABOVE LIMITS • PUT EVERYTHING IN THE HEAT",
    "containment_breach": "CONTAINMENT BREACH • GROUNDING",
}
STORAGE_EMOJI = ["🔥", "📦", "🧊"]

ISSUES: List[Tuple[str, str]] = [
    ("critical", "Change Drone"),
    ("critical", "Pad Blocked – do not assign"),
    ("attention", "Repress Pad"),
    ("attention", "Change Cassette"),
    ("attention", "Reboot Drone"),
    ("attention", "Comms lost"),
    ("attention", "Unit expired"),
]
ISSUE_CHANCE = 0.22
CRITICAL_WEIGHT = 0.30


# ----------------------------
# Model
# ----------------------------
@dataclass
class PadState:
    pad: str
    phase: str  # COLLECTING | ARRIVING | AT_BASE
    remaining: int
    order_next: int
    storage: str
    issue: Optional[str] = None
    severity: Optional[str] = None  # critical | attention
    fix_left: int = 0


def next_order(order_id: int) -> int:
    nxt = order_id + ORDER_STEP
    return ORDER_MIN if nxt > ORDER_MAX else nxt


def pick_storage(rng: random.Random) -> str:
    return rng.choice(STORAGE_EMOJI)


def maybe_issue(rng: random.Random) -> Tuple[Optional[str], Optional[str]]:
    if rng.random() > ISSUE_CHANCE:
        return None, None
    if rng.random() < CRITICAL_WEIGHT:
        crit = [t for sev, t in ISSUES if sev == "critical"]
        return rng.choice(crit), "critical"
    att = [t for sev, t in ISSUES if sev == "attention"]
    return rng.choice(att), "attention"


def init_state() -> Dict:
    seed = int(time.time())
    rng = random.Random(seed)

    base_order = rng.randrange(ORDER_MIN, ORDER_MAX + 1, ORDER_STEP)
    pads: Dict[str, PadState] = {}

    for i, p in enumerate(PADS):
        order_id = base_order + i * ORDER_STEP
        while order_id > ORDER_MAX:
            order_id = ORDER_MIN + (order_id - ORDER_MAX - 1)

        pads[p] = PadState(
            pad=p,
            phase="COLLECTING",
            remaining=rng.randint(INITIAL_COLLECTING_MIN, INITIAL_COLLECTING_MAX),
            order_next=order_id,
            storage=pick_storage(rng),
        )

    return {
        "rng": rng,
        "pads": pads,
        "weather_idx": 0,
        "weather_next": time.time() + WEATHER_ROTATE_SECONDS,
        "last_tick": time.time(),
        "wind_ms": 7,
        "topbar_alert_id": None,
        "topbar_is_alert": False,
        # environment + top bar alert state
    }


def tick_sim(state: Dict) -> None:
    now = time.time()
    last = state.get("last_tick", now)
    dt = int(now - last)
    if dt <= 0:
        return
    state["last_tick"] = now

    rng: random.Random = state["rng"]
    pads: Dict[str, PadState] = state["pads"]

    for _ in range(dt * SIM_SPEED):
        for p in pads.values():
            p.remaining = max(0, p.remaining - 1)

            if p.phase == "COLLECTING" and p.remaining == 0:
                p.phase = "ARRIVING"
                p.remaining = rng.randint(ARRIVING_MIN, ARRIVING_MAX)

            elif p.phase == "ARRIVING" and p.remaining == 0:
                p.phase = "AT_BASE"
                p.issue, p.severity = maybe_issue(rng)
                p.fix_left = FIX_EXTRA_SECONDS if p.issue else 0
                p.remaining = AT_BASE_SECONDS + (FIX_EXTRA_SECONDS if p.issue else 0)

            elif p.phase == "AT_BASE" and p.remaining == 0:
                p.phase = "COLLECTING"
                p.remaining = rng.randint(COLLECTING_MIN, COLLECTING_MAX)
                p.order_next = next_order(p.order_next)
                p.storage = pick_storage(rng)
                p.issue = None
                p.severity = None
                p.fix_left = 0

            if p.phase == "AT_BASE" and p.issue and p.fix_left > 0:
                p.fix_left = max(0, p.fix_left - 1)

    if time.time() >= state.get("weather_next", 0):
        state["weather_idx"] = (state["weather_idx"] + 1) % len(WEATHER_MESSAGES)
        state["weather_next"] = time.time() + WEATHER_ROTATE_SECONDS






def update_topbar(state: Dict) -> None:
    """
    Demo behaviour:
      - 5% of the time show an alert (one of the PDF alert phrases)
      - otherwise show RPP + Wind reading (5–10 m/s)
    """
    rng: random.Random = state["rng"]
    # Decide whether the bar is an alert this tick
    is_alert = rng.random() < TOPBAR_ALERT_RATE
    state["topbar_is_alert"] = is_alert
    if is_alert:
        state["topbar_alert_id"] = rng.choice(TOPBAR_ALERT_IDS)
    else:
        state["topbar_alert_id"] = None
        # Update wind gently when we're in normal mode
        state["wind_ms"] = rng.randint(WIND_MIN_MS, WIND_MAX_MS)
def is_degraded(pads: List[PadState]) -> bool:
    return any(p.phase == "AT_BASE" and p.issue and p.severity == "critical" for p in pads)


# ----------------------------
# UI helpers
# ----------------------------
def now_clock() -> str:
    return time.strftime("%H:%M:%S")


def list_items_with_more(items: List[str], max_visible: int = 3) -> str:
    visible = items[:max_visible]
    extra = len(items) - len(visible)
    html = "".join(visible)
    if extra > 0:
        html += f'<div class="more">+{extra} more</div>'
    return html


def status_item(pad: str, left: str, right: str) -> str:
    return f"""
<div class="sitem">
  <div class="spad">{pad}</div>
  <div class="sleft">{left}</div>
  <div class="sright">{right}</div>
</div>
"""


def section(title: str, kind: str, items_html: str) -> str:
    return f"""
<div class="stack-section">
  <div class="stack-title {kind}">{title}</div>
  <div class="stack-items">{items_html}</div>
</div>
"""


def build_status_stack(pads: List[PadState]) -> str:
    critical = sorted(
        [p for p in pads if p.phase == "AT_BASE" and p.issue and p.severity == "critical"],
        key=lambda x: x.pad,
    )
    crit_items = [status_item(p.pad, f"{p.issue}", f"{p.storage} {p.order_next}") for p in critical]

    # ACTIVE / LOADING includes attention first (still "active work")
    active = sorted(
        [p for p in pads if p.phase == "AT_BASE" and p.pad not in {c.pad for c in critical}],
        key=lambda x: (0 if (x.issue and x.severity == "attention") else 1, x.remaining, x.pad),
    )

    act_items: List[str] = []
    for p in active:
        if p.issue and p.severity == "attention":
            act_items.append(status_item(p.pad, f"{p.issue}", f"{p.storage} {p.order_next}"))
        else:
            act_items.append(status_item(p.pad, f"{p.remaining}s", f"{p.storage} {p.order_next}"))

    queue = sorted([p for p in pads if p.phase == "COLLECTING"], key=lambda x: x.remaining)
    q_items = [status_item(p.pad, f"{p.remaining}s", f"{p.storage} {p.order_next}") for p in queue]

    html = ""
    if crit_items:
        html += section("🔴 CRITICAL", "t-critical", list_items_with_more(crit_items, 3))
    if act_items:
        html += section("🟡 ACTIVE / LOADING", "t-active", list_items_with_more(act_items, 3))
    if q_items:
        html += section("⚪ QUEUE", "t-queue", list_items_with_more(q_items, 3))

    if not html.strip():
        html = section("⚪ QUEUE", "t-queue", status_item("✓", "All clear", ""))

    return html


def build_primary_action(kind: str, p: Optional[PadState], label: str) -> str:
    if kind == "calm" or p is None:
        return """
<div class="primary">
  <div class="p-next">NEXT ACTION</div>
  <div class="p-row">
    <div class="p-arrow">→</div>
    <div class="p-pad">—</div>
  </div>
  <div class="p-action">All clear</div>
  <div class="p-sub">Waiting for next order</div>
</div>
"""

    countdown = ""
    if kind in ("arriving", "active") and p.remaining > 0:
        countdown = f'<div class="p-count">{p.remaining}s</div>'

    return f"""
<div class="primary">
  <div class="p-next">NEXT ACTION</div>
  <div class="p-row">
    <div class="p-arrow">→</div>
    <div class="p-pad">{p.pad}</div>
  </div>
  <div class="p-action">{label}</div>
  {countdown}
  <div class="p-sub">{p.storage} {p.order_next}</div>
</div>
"""


def top_strip_html(pads: List[PadState], state: Dict) -> str:
    """
    Top bar:
      - If alert: show alert phrase (left) + rotating weather text (right)
      - Else: show RPP (left) + wind reading (right)
    """
    if state.get("topbar_is_alert") and state.get("topbar_alert_id"):
        alert_id = state["topbar_alert_id"]
        left = TOPBAR_ALERT_TEXT.get(alert_id, "ALERT")
        right = WEATHER_MESSAGES[state["weather_idx"]]
        cls = "topstrip alert-red" if alert_id == "containment_breach" else "topstrip alert-amber"
        return f"""
<div class="{cls}">
  <div class="ts-left">{left}</div>
  <div class="ts-mid">{right}</div>
</div>
"""
    # normal
    wind = state.get("wind_ms", 7)
    return f"""
<div class="topstrip">
  <div class="ts-left">{RPP_TEXT}</div>
  <div class="ts-mid">Wind: {wind} m/s</div>
</div>
"""
def footer_html(at_base: int, arriving_soon: int, cancelled: int) -> str:
    return f"""
<div class="footer">
  <div><span class="k">At Base</span>{at_base}</div>
  <div><span class="k">Arriving Soon</span>{arriving_soon}</div>
  <div><span class="k">Cancelled</span>{cancelled}</div>
</div>
"""

# ----------------------------
# Styles (pastel + wall scale)
# ----------------------------
CSS = """
<style>
*{box-sizing:border-box;}
:root{
  --bg:#ffffff;
  --ink:#0b1320;
  --muted:#5b6472;

  --card:#ffffff;
  --line:#e8ebf0;

  --red:#b51d1d;
  --navy:#1f3f8a;
  --amber:#b07a00;

  --crit_bg:#fbe3e3; --crit_line:#efb1b1; --crit_text:#7a1212;
  --load_bg:#fff7cf; --load_line:#f0e39c; --load_text:#6a5400;
  --queue_bg:#f4f5f7; --queue_line:#e1e3e8; --queue_text:#3b4350;

  --primary_bg:#fff7ed; --primary_line:#f1dcc7;
  --urgent_bg:#fff0f0;
}

body{background:var(--bg);}

.main .block-container{
  padding-top:0.4rem;
  padding-bottom:0.4rem;
  max-width: 1800px;
}

/* Fit everything inside viewport */
.grid{
  height: calc(100vh - 0.8rem);
  display:grid;
  grid-template-rows: 10fr 82fr 8fr;
  gap: 8px;
  min-height: 0;
}

/* Top strip (navy by default, red when degraded) */
.topstrip{
  background: var(--navy);
  border-radius: 18px;
  padding: 0 22px;
  display:grid;
  grid-template-columns: 1fr 1.6fr;
  align-items:center;
  font-weight: 1000;
  min-height:0;
}
.topstrip .ts-left{
  font-size: clamp(18px, 2.3vw, 40px);
  text-align:left;
  color:rgba(255,255,255,0.95);
}
.topstrip .ts-mid{
  font-size: clamp(16px, 2.0vw, 36px);
  text-align:right;
  color:rgba(255,255,255,0.78);
}
.topstrip.degraded{background: var(--red);} /* legacy */
.topstrip.alert-red{background: var(--red);} 
.topstrip.alert-amber{background: var(--amber);}

/* Main split */
.mainrow{
  display:grid;
  grid-template-columns: 65% 35%;
  gap: 8px;
  align-items:stretch;
  min-height: 0;
}

/* Primary */
.primarywrap{
  background: var(--primary_bg);
  border-radius: 18px;
  border: 2px solid var(--primary_line);
  display:flex;
  align-items:center;
  justify-content:center;
  min-height: 0;
  overflow:hidden;
}
.primarywrap.urgent{
  background: var(--urgent_bg);
  border: 4px solid var(--red);
}

.primary{
  width: 100%;
  height: 100%;
  padding: clamp(12px, 1.8vh, 24px) clamp(12px, 1.8vw, 28px);
  display:flex;
  flex-direction:column;
  justify-content:center;
  color: var(--ink);
  min-height: 0;
}
.p-next{
  font-size: clamp(20px, 2.6vw, 44px);
  font-weight: 1000;
  letter-spacing: 1px;
  color: var(--muted);
  margin-bottom: clamp(8px, 1.2vh, 14px);
}
.p-row{display:flex; align-items:center; gap: clamp(14px, 2.0vw, 36px);}
.p-arrow{
  font-size: clamp(80px, 9vw, 170px);
  font-weight: 1000; line-height:1; color: var(--ink); opacity:0.95;
}
.p-pad{
  font-size: clamp(120px, 16vw, 300px);
  font-weight: 1000; line-height:0.9; color: var(--ink);
}
.p-action{
  margin-top: clamp(6px, 1.1vh, 12px);
  font-size: clamp(34px, 5.4vw, 88px);
  font-weight: 1000; line-height: 1.05; color: var(--ink);
}
.p-count{
  margin-top: clamp(4px, 0.9vh, 10px);
  font-size: clamp(52px, 8.2vw, 130px);
  font-weight: 1000; line-height: 1; color: var(--ink);
}
.p-sub{
  margin-top: clamp(8px, 1.2vh, 14px);
  font-size: clamp(18px, 3.2vw, 44px);
  font-weight: 1000;
  color: var(--muted);
}

/* Status stack: prevent jumble by tightening scale + allowing internal scroll */
.statuswrap{
  display:flex;
  flex-direction:column;
  gap: 8px;
  min-height: 0;
  overflow:auto; /* if content exceeds, scroll instead of overlapping */
  padding-right: 2px;
}
.stack-section{
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 18px;
  overflow:hidden;
  display:flex;
  flex-direction:column;
}
.stack-title{
  padding: 10px 14px;
  font-size: clamp(18px, 2.6vw, 36px);
  font-weight: 1000;
  letter-spacing: 0.8px;
}
.t-critical{background: var(--crit_bg); color: var(--crit_text); border-bottom: 1px solid var(--crit_line);}
.t-active{background: var(--load_bg); color: var(--load_text); border-bottom: 1px solid var(--load_line);}
.t-queue{background: var(--queue_bg); color: var(--queue_text); border-bottom: 1px solid var(--queue_line);}

.stack-items{
  padding: 10px 12px 12px 12px;
  display:flex;
  flex-direction:column;
  gap: 8px;
}

.sitem{
  display:grid;
  grid-template-columns: clamp(54px, 4.4vw, 76px) 1fr auto;
  align-items:center;
  column-gap: 12px;
  padding: 8px 10px;
  border-radius: 14px;
  border: 1px solid var(--queue_line);
  background: #ffffff;
}
.spad{
  width: clamp(42px, 3.8vw, 62px);
  height: clamp(42px, 3.8vw, 62px);
  border-radius: 14px;
  background: #fff;
  border: 1px solid rgba(0,0,0,0.10);
  display:flex; align-items:center; justify-content:center;
  font-size: clamp(18px, 2.5vw, 34px);
  font-weight: 1000;
  color: var(--ink);
}
.sleft{
  font-size: clamp(16px, 2.3vw, 32px);
  font-weight: 1000;
  color: var(--ink);
  line-height:1;
  white-space: nowrap;
  overflow:hidden;
  text-overflow: ellipsis;
}
.sright{
  font-size: clamp(16px, 2.3vw, 32px);
  font-weight: 1000;
  color: var(--ink);
  line-height:1;
  font-variant-numeric: tabular-nums;
  letter-spacing:0.4px;
  text-align:right;
  white-space: nowrap;
}

.more{
  margin-top: 2px;
  font-size: clamp(14px, 2.0vw, 26px);
  font-weight: 1000;
  color: var(--muted);
  padding-left: 6px;
}

/* Footer */
.footer{
  background: #ffffff;
  border: 1px solid var(--line);
  border-radius: 18px;
  padding: 0 22px;
  display:flex;
  align-items:center;
  justify-content:space-between;
  color: #6b7483;
  font-size: clamp(14px, 1.9vw, 24px);
  font-weight: 1000;
  min-height:0;
}
.footer .k{color:#6b7483; margin-right:10px;}
</style>
"""


# ----------------------------
# Runtime
# ----------------------------
if "wall_state" not in st.session_state:
    st.session_state["wall_state"] = init_state()

state = st.session_state["wall_state"]

try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=1000, key="tick_wall")
except Exception:
    pass

tick_sim(state)
update_topbar(state)
pads = list(state["pads"].values())
st.markdown(CSS, unsafe_allow_html=True)

kind, primary_pad, primary_label = pick_primary(pads)
degraded = is_degraded(pads)
primarywrap_cls = "primarywrap urgent" if degraded else "primarywrap"

top_html = top_strip_html(pads, state)
primary_html = build_primary_action(kind, primary_pad, primary_label)
stack_html = build_status_stack(pads)

at_base = sum(1 for p in pads if p.phase == "AT_BASE")
arriving_soon = sum(1 for p in pads if p.phase == "COLLECTING")
cancelled = 0

foot_html = footer_html(at_base, arriving_soon, cancelled)

st.markdown(
    f"""
<div class="grid">
  {top_html}
  <div class="mainrow">
    <div class="{primarywrap_cls}">{primary_html}</div>
    <div class="statuswrap">{stack_html}</div>
  </div>
  {foot_html}
</div>
""",
    unsafe_allow_html=True,
)
