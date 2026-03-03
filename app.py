import time
import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import streamlit as st

# ============================================================
# LOADER WALL SCREEN – Wall-first layout (65" @ ~5m)
# 16:9 • Deterministic priority • Clean hierarchy
#
# Phase naming (ops language):
# - COLLECTING: collector has the order (Arriving Soon metric)
# - ARRIVING: order is arriving to base imminently (countdown)
# - AT_BASE: at base being loaded
#
# Layout grid:
# - Top Status Strip: 10% height (neutral dark; red only for degraded)
# - Main: 82% height (Left 65% Primary Action, Right 35% Status Stack)
# - Footer: 8% height (At Base | Arriving Soon | Cancelled | Clock)
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

ARRIVING_SOON_THRESHOLD = 60  # for primary selection only

# Make it feel live on a wall
SIM_SPEED = 2
INITIAL_COLLECTING_MIN = 10
INITIAL_COLLECTING_MAX = 80

# Top strip info (neutral)
RPP_TEXT = "RPP: 2 mins"
WEATHER_ROTATE_SECONDS = 6
WEATHER_MESSAGES = [
    "Weather: Visibility OK",
    "Weather: Light rain",
    "Weather: Wind 12kt",
    "Weather: Temps stable",
]

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


# ----------------------------
# Deterministic priority ladder (LOCKED)
# ----------------------------
def pick_primary(pads: List[PadState]) -> Tuple[str, Optional[PadState], str]:
    critical = [p for p in pads if p.phase == "AT_BASE" and p.issue and p.severity == "critical"]
    if critical:
        p = sorted(critical, key=lambda x: x.pad)[0]
        return "critical", p, p.issue or "Critical"

    attention = [p for p in pads if p.phase == "AT_BASE" and p.issue and p.severity == "attention"]
    if attention:
        p = sorted(attention, key=lambda x: x.pad)[0]
        return "attention", p, p.issue or "Attention"

    active = [p for p in pads if p.phase == "AT_BASE" and not p.issue]
    if active:
        p = sorted(active, key=lambda x: x.remaining)[0]
        return "active", p, "Load Order"

    arriving = [p for p in pads if p.phase == "ARRIVING" and p.remaining <= ARRIVING_SOON_THRESHOLD]
    if arriving:
        p = sorted(arriving, key=lambda x: x.remaining)[0]
        return "arriving", p, "Go To Pad"

    return "calm", None, "All Clear"


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
        key=lambda x: x.pad
    )
    crit_items = [status_item(p.pad, f"{p.issue}", f"{p.storage} {p.order_next}") for p in critical]

    # ACTIVE / LOADING includes attention too (still active work), with attention first
    active = sorted(
        [p for p in pads if p.phase == "AT_BASE" and p.pad not in {c.pad for c in critical}],
        key=lambda x: (0 if (x.issue and x.severity == "attention") else 1, x.remaining, x.pad)
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
  <div class="p-pad">—</div>
  <div class="p-action">All Clear</div>
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
    degraded = is_degraded(pads)
primarywrap_cls = "primarywrap urgent" if degraded else "primarywrap"
    cls = "topstrip degraded" if degraded else "topstrip"
    left = "SYSTEM DEGRADED" if degraded else RPP_TEXT
    mid = WEATHER_MESSAGES[state["weather_idx"]]
    clock = now_clock()
    return f"""
<div class="{cls}">
  <div class="ts-left">{left}</div>
  <div class="ts-mid">{mid}</div>
  <div class="ts-right">{clock}</div>
</div>
"""


def footer_html(at_base: int, arriving_soon: int, cancelled: int) -> str:
    return f"""
<div class="footer">
  <div><span class="k">At Base</span>{at_base}</div>
  <div><span class="k">Arriving Soon</span>{arriving_soon}</div>
  <div><span class="k">Cancelled</span>{cancelled}</div>
  <div class="clock">{now_clock()}</div>
</div>
"""


# ----------------------------
# Styles (wall scale)
# ----------------------------
CSS = """
<style>
:root{
  /* Pastel ops palette (matches v10-style screenshots) */
  --bg:#ffffff;
  --ink:#0b1320;
  --muted:#5b6472;

  --card:#ffffff;
  --line:#e8ebf0;

  --blue:#1f3f8a;
  --red:#b51d1d;

  --crit_bg:#fbe3e3; --crit_line:#efb1b1; --crit_text:#7a1212;
  --attn_bg:#e7efff; --attn_line:#b9d3ff; --attn_text:#143d8a;
  --load_bg:#fff7cf; --load_line:#f0e39c; --load_text:#6a5400;
  --queue_bg:#f4f5f7; --queue_line:#e1e3e8; --queue_text:#3b4350;
  --primary_bg:#fff7ed; --primary_line:#f1dcc7;
  --urgent_bg:#fff0f0;
}

/* page background */
body{background:var(--bg);}

.main .block-container{
  padding-top:0.6rem;
  padding-bottom:0.6rem;
  max-width: 1900px;
}

/* 10% / 82% / 8% */
.grid{
  display:grid;
  grid-template-rows: 10vh 82vh 8vh;
  gap: 1.2vh;
}

/* Top status strip – neutral by default; red only when degraded */
.topstrip{
  background:#111722;
  border-radius: 18px;
  padding: 0 28px;
  display:grid;
  grid-template-columns: 1fr 1.4fr 1fr;
  align-items:center;
  font-weight: 1000;
}
.topstrip .ts-left{font-size:48px; text-align:left; color:rgba(255,255,255,0.95);}
.topstrip .ts-mid{font-size:42px; text-align:center; color:rgba(255,255,255,0.70);}
.topstrip .ts-right{font-size:48px; text-align:right; letter-spacing:1px; color:rgba(255,255,255,0.95);}
.topstrip.degraded{background: var(--red);}

/* Main split 65/35 */
.mainrow{
  display:grid;
  grid-template-columns: 65% 35%;
  gap: 1.2vh;
  align-items:stretch;
  height: 82vh;
}

/* Primary action area – large type; subtle panel (no heavy boxes) */
.primarywrap{
  background: var(--primary_bg);
  border-radius: 18px;
  border: 2px solid var(--primary_line);
  display:flex;
  align-items:center;
  justify-content:center;
}

.primary{
  width: 100%;
  height: 100%;
  padding: 3vh 3vw;
  display:flex;
  flex-direction:column;
  justify-content:center;
  color: var(--ink);
}

.p-next{
  font-size: 56px;
  font-weight: 1000;
  letter-spacing: 1px;
  color: var(--muted);
  margin-bottom: 2vh;
}

.p-row{
  display:flex;
  align-items:center;
  gap: 3vw;
}

.p-arrow{
  font-size: 220px;
  font-weight: 1000;
  line-height: 1;
  color: var(--ink);
  opacity: 0.95;
}

.p-pad{
  font-size: 320px;
  font-weight: 1000;
  line-height: 0.9;
  color: var(--ink);
}

.p-action{
  margin-top: 1.6vh;
  font-size: 104px;
  font-weight: 1000;
  line-height: 1.05;
  color: var(--ink);
}

.p-count{
  margin-top: 1vh;
  font-size: 160px;
  font-weight: 1000;
  line-height: 1;
  color: var(--ink);
}

.p-sub{
  margin-top: 1.5vh;
  font-size: 54px;
  font-weight: 1000;
  color: var(--muted);
}

/* If degraded, make the primary area urgent (soft red, not full-screen banner) */
.primarywrap.urgent{
  background: var(--urgent_bg);
  border: 4px solid var(--red);
}

/* Status stack on right */
.statuswrap{
  background: transparent;
  border-radius: 18px;
  display:flex;
  flex-direction:column;
  gap: 1.2vh;
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
  padding: 1.4vh 1.6vw;
  font-size: 56px;
  font-weight: 1000;
  letter-spacing: 0.8px;
}

.t-critical{background: var(--crit_bg); color: var(--crit_text); border-bottom: 1px solid var(--crit_line);}
.t-active{background: var(--load_bg); color: var(--load_text); border-bottom: 1px solid var(--load_line);}
.t-queue{background: var(--queue_bg); color: var(--queue_text); border-bottom: 1px solid var(--queue_line);}

.stack-items{
  padding: 1.2vh 1.2vw 1.6vh 1.2vw;
  display:flex;
  flex-direction:column;
  gap: 1.2vh;
}

/* Status row: PAD | LEFT | RIGHT (aligned numbers) */
.sitem{
  display:grid;
  grid-template-columns: 92px 1fr auto;
  align-items:center;
  column-gap: 18px;
  padding: 0.7vh 0.6vw;
  border-radius: 14px;
  border: 1px solid var(--queue_line);
  background: #ffffff;
}

.spad{
  width: 72px;
  height: 72px;
  border-radius: 16px;
  background: #fff;
  border: 1px solid rgba(0,0,0,0.10);
  display:flex;
  align-items:center;
  justify-content:center;
  font-size: 52px;
  font-weight: 1000;
  color: var(--ink);
}

.sleft{
  font-size: 48px;
  font-weight: 1000;
  color: var(--ink);
  line-height:1;
  white-space: nowrap;
  overflow:hidden;
  text-overflow: ellipsis;
}

.sright{
  font-size: 48px;
  font-weight: 1000;
  color: var(--ink);
  line-height:1;
  font-variant-numeric: tabular-nums;
  letter-spacing:0.5px;
  text-align:right;
  white-space: nowrap;
}

.more{
  margin-top: 0.2vh;
  font-size: 44px;
  font-weight: 1000;
  color: var(--muted);
  padding-left: 0.4vw;
}

/* Footer: minimal, low contrast */
.footer{
  background: #ffffff;
  border: 1px solid var(--line);
  border-radius: 18px;
  padding: 0 28px;
  display:flex;
  align-items:center;
  justify-content:space-between;
  color: #6b7483;
  font-size: 30px;
  font-weight: 1000;
}

.footer .k{
  color: #6b7483;
  margin-right: 10px;
}

.footer .clock{
  color: rgba(11,19,32,0.85);
  letter-spacing: 1px;
}
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
pads = list(state["pads"].values())


primarywrap_cls = "primarywrap urgent" if degraded else "primarywrap"

st.markdown(CSS, unsafe_allow_html=True)

kind, primary_pad, primary_label = pick_primary(pads)

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
    unsafe_allow_html=True
)
