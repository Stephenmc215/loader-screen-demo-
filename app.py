import time
import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import streamlit as st

# ============================================================
# LOADER WALL SCREEN (V10 – REBUILT CLEAN)
# Landscape • Deterministic priority • Clean hierarchy
#
# Locked priority ladder:
# 1) Critical issue (on ground)
# 2) Attention issue (on ground)
# 3) Loading now (on ground, no issue)
# 4) Landing ≤60s
# 5) Calm
#
# Right stack behavior:
# - Sections ONLY appear if they have items
# - No "In Flight" section
# - If nothing actionable/soon: show a single STATUS card
#
# Footer:
# - At Base • Arriving Soon • Cancelled
# - Cancelled is a demo constant (0) in this simulator
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
LOAD_SECONDS = 60
FIX_EXTRA_SECONDS = 30
FLIGHT_MIN = 60
FLIGHT_MAX = 180
LANDING_MIN = 5
LANDING_MAX = 30

LANDING_SOON_THRESHOLD = 60  # ARRIVING countdown threshold for right-side "INBOUND ≤60s" section

# Make it feel live
SIM_SPEED = 2
INITIAL_FLIGHT_MIN = 10
INITIAL_FLIGHT_MAX = 80

# Banner rotation (calm only)
WEATHER_ROTATE_SECONDS = 6
WEATHER_MESSAGES = [
    "RPP: 2 mins",
    "Weather: Visibility OK",
    "Weather: Light rain",
    "Weather: Wind 12kt",
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
            remaining=rng.randint(INITIAL_FLIGHT_MIN, INITIAL_FLIGHT_MAX),
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

            # FLIGHT -> LANDING
            if p.phase == "COLLECTING" and p.remaining == 0:
                p.phase = "ARRIVING"
                p.remaining = rng.randint(LANDING_MIN, LANDING_MAX)

            # LANDING -> LOADING
            elif p.phase == "ARRIVING" and p.remaining == 0:
                p.phase = "AT_BASE"
                p.issue, p.severity = maybe_issue(rng)
                p.fix_left = FIX_EXTRA_SECONDS if p.issue else 0
                p.remaining = LOAD_SECONDS + (FIX_EXTRA_SECONDS if p.issue else 0)

            # LOADING -> FLIGHT
            elif p.phase == "AT_BASE" and p.remaining == 0:
                p.phase = "COLLECTING"
                p.remaining = rng.randint(FLIGHT_MIN, FLIGHT_MAX)
                p.order_next = next_order(p.order_next)
                p.storage = pick_storage(rng)
                p.issue = None
                p.severity = None
                p.fix_left = 0

            # LOADING issue timer
            if p.phase == "AT_BASE" and p.issue and p.fix_left > 0:
                p.fix_left = max(0, p.fix_left - 1)

    # rotate banner text
    if time.time() >= state.get("weather_next", 0):
        state["weather_idx"] = (state["weather_idx"] + 1) % len(WEATHER_MESSAGES)
        state["weather_next"] = time.time() + WEATHER_ROTATE_SECONDS


# ----------------------------
# Priority (LOCKED)
# ----------------------------
def pick_primary(pads: List[PadState]) -> Tuple[str, Optional[PadState], str]:
    critical = [p for p in pads if p.phase == "AT_BASE" and p.issue and p.severity == "critical"]
    if critical:
        p = sorted(critical, key=lambda x: x.pad)[0]
        return "critical", p, p.issue or "Critical issue"

    attention = [p for p in pads if p.phase == "AT_BASE" and p.issue and p.severity == "attention"]
    if attention:
        p = sorted(attention, key=lambda x: x.pad)[0]
        return "attention", p, p.issue or "Attention issue"

    loading = [p for p in pads if p.phase == "AT_BASE" and not p.issue]
    if loading:
        p = sorted(loading, key=lambda x: x.remaining)[0]
        return "loading", p, "Load now"

    landing = [p for p in pads if p.phase == "ARRIVING" and p.remaining <= LANDING_SOON_THRESHOLD]
    if landing:
        p = sorted(landing, key=lambda x: x.remaining)[0]
        return "landing", p, "Landing soon"

    return "calm", None, "All clear"


def wall_mode(kind: str) -> str:
    if kind == "critical":
        return "CRITICAL"
    if kind in ("attention", "loading", "landing"):
        return "ACTION"
    return "CALM"


# ----------------------------
# UI builders
# ----------------------------
def item_html(pad: str, kind: str, label: str, right_text: str) -> str:
    tag_class = {
        "critical": "tag-red",
        "attention": "tag-blue",
        "loading": "tag-yellow",
        "landing": "tag-orange",
        "status": "tag-gray",
    }.get(kind, "tag-gray")

    return f"""
<div class="item {tag_class}">
  <div class="item-left">
    <div class="pad">{pad}</div>
    <div class="desc">{label}</div>
  </div>
  <div class="meta">{right_text}</div>
</div>
"""


def section_html(title: str, cls: str, items_html: str) -> str:
    return f"""
<div class="section">
  <div class="section-h {cls}">{title}</div>
  <div class="items">{items_html}</div>
</div>
"""


def build_right_stack(pads: List[PadState]) -> str:
    used = set()

    critical = sorted([p for p in pads if p.phase == "AT_BASE" and p.issue and p.severity == "critical"], key=lambda x: x.pad)
    used |= {p.pad for p in critical}

    attention = sorted([p for p in pads if p.phase == "AT_BASE" and p.issue and p.severity == "attention" and p.pad not in used], key=lambda x: x.pad)
    used |= {p.pad for p in attention}

    loading = sorted([p for p in pads if p.phase == "AT_BASE" and not p.issue and p.pad not in used], key=lambda x: x.remaining)
    used |= {p.pad for p in loading}

    landing = sorted([p for p in pads if p.phase == "ARRIVING" and p.remaining <= LANDING_SOON_THRESHOLD and p.pad not in used], key=lambda x: x.remaining)
    used |= {p.pad for p in landing}

    html = ""

    if critical:
        html += section_html(
            "🔴 CRITICAL",
            "h-critical",
            "".join(item_html(p.pad, "critical", p.issue or "Issue", f"{p.storage} {p.order_next}") for p in critical),
        )

    if attention:
        html += section_html(
            "⚠️ ATTENTION",
            "h-attn",
            "".join(item_html(p.pad, "attention", p.issue or "Attention", f"{p.storage} {p.order_next}") for p in attention),
        )

    if loading:
        html += section_html(
            "🟡 LOADING NOW",
            "h-load",
            "".join(item_html(p.pad, "loading", "Loading", f"{p.remaining}s • {p.storage} {p.order_next}") for p in loading),
        )

    if landing:
        html += section_html(
            "🟠 INBOUND ≤60s",
            "h-land",
            "".join(item_html(p.pad, "landing", "Arriving Soon", f"{p.remaining}s • {p.storage} {p.order_next}") for p in landing),
        )

    if not html.strip():
        html = section_html("⚪ STATUS", "h-flight", item_html("✓", "status", "All clear", ""))

    return html


def build_left_panel(kind: str, p: Optional[PadState], label: str) -> str:
    if kind == "calm" or p is None:
        return """
<div class="left calm">
  <div class="left-title">STATUS</div>
  <div class="left-big">All clear</div>
  <div class="left-sub">Waiting for next arrival</div>
</div>
"""

    urgent = (kind == "critical")
    left_cls = "left urgent" if urgent else "left action"

    if kind in ("critical", "attention"):
        return f"""
<div class="{left_cls}">
  <div class="left-title">ACTION REQUIRED</div>
  <div class="bigrow">
    <div class="arrow">➡</div>
    <div class="padbig">{p.pad}</div>
  </div>
  <div class="primaryline">{label}</div>
  <div class="orderline">{p.storage} {p.order_next}</div>
</div>
"""

    if kind == "loading":
        return f"""
<div class="{left_cls}">
  <div class="left-title">LOAD NOW</div>
  <div class="bigrow">
    <div class="arrow">➡</div>
    <div class="padbig">{p.pad}</div>
  </div>
  <div class="primaryline">{p.remaining}s left</div>
  <div class="orderline">{p.storage} {p.order_next}</div>
</div>
"""

    return f"""
<div class="{left_cls}">
  <div class="left-title">GO TO PAD</div>
  <div class="bigrow">
    <div class="arrow">➡</div>
    <div class="padbig">{p.pad}</div>
  </div>
  <div class="primaryline">Arriving Soon in {p.remaining}s</div>
  <div class="orderline">{p.storage} {p.order_next}</div>
</div>
"""


def top_banner(pads: List[PadState], mode: str, state: Dict, primary: Optional[PadState], primary_label: str) -> Tuple[str, str]:
    crit = [p for p in pads if p.phase == "AT_BASE" and p.issue and p.severity == "critical"]
    if crit:
        p = sorted(crit, key=lambda x: x.pad)[0]
        return "banner-red", f"CRITICAL: {p.issue} (Pad {p.pad})"

    if mode == "ACTION" and primary is not None:
        return "banner-blue", f"{primary_label.upper()} • PAD {primary.pad}"

    return "banner-blue", WEATHER_MESSAGES[state["weather_idx"]]


# ----------------------------
# Styles
# ----------------------------
CSS = """
<style>
:root{
  --bg:#ffffff; --ink:#0b1320; --muted:#5b6472; --card:#ffffff; --line:#e8ebf0;
  --blue:#1f3f8a; --red:#b51d1d;
  --tag_red_bg:#fbe3e3; --tag_red_line:#efb1b1;
  --tag_blue_bg:#e7efff; --tag_blue_line:#b9d3ff;
  --tag_yellow_bg:#fff7cf; --tag_yellow_line:#f0e39c;
  --tag_orange_bg:#ffedd7; --tag_orange_line:#f4c99a;
  --tag_gray_bg:#f4f5f7; --tag_gray_line:#e1e3e8;
}
.main .block-container{padding-top:1rem; padding-bottom:1rem; max-width:1600px;}
.banner{border-radius:20px; padding:18px 22px; font-weight:1000; text-align:center; font-size:52px; margin-bottom:14px; color:white;}
.banner-blue{background:var(--blue);} .banner-red{background:var(--red);}
.shell{display:flex; gap:16px; align-items:stretch;}
.left{flex:0 0 40%; border-radius:18px; padding:26px; min-height:74vh; display:flex; flex-direction:column; justify-content:center; border:2px solid #e8ebf0; background:#fff;}
.left.action{background:#fff7ed; border-color:#f1dcc7;} .left.urgent{background:#fff0f0; border:4px solid var(--red);} .left.calm{background:#f8fafc;}
.left-title{font-size:34px; font-weight:1000; letter-spacing:1px; margin-bottom:10px;}
.bigrow{display:flex; gap:18px; align-items:center;}
.arrow{font-size:120px; font-weight:1000; line-height:1;}
.padbig{font-size:190px; font-weight:1000; line-height:0.9;}
.primaryline{margin-top:10px; font-size:64px; font-weight:1000; line-height:1.05;}
.left-big{margin-top:6px; font-size:74px; font-weight:1000; line-height:1.05;}
.left-sub{margin-top:12px; font-size:28px; font-weight:800; color:var(--muted);}
.orderline{margin-top:18px; font-size:46px; font-weight:1000;}
.right{flex:0 0 60%; display:flex; flex-direction:column; gap:12px; min-height:74vh;}
.section{border:1px solid var(--line); border-radius:14px; overflow:hidden; background:var(--card);}
.section-h{padding:10px 14px; font-size:18px; font-weight:1000; letter-spacing:0.6px;}
.h-critical{background:var(--tag_red_bg); color:#7a1212;}
.h-attn{background:var(--tag_blue_bg); color:#143d8a;}
.h-load{background:var(--tag_yellow_bg); color:#6a5400;}
.h-land{background:var(--tag_orange_bg); color:#7a3a00;}
.h-flight{background:var(--tag_gray_bg); color:#3b4350;}
.items{padding:10px; display:flex; flex-direction:column; gap:10px;}
.item{border-radius:12px; padding:12px 14px; display:flex; justify-content:space-between; align-items:center; border:1px solid var(--tag_gray_line);}
.item-left{display:flex; gap:14px; align-items:center;}
.pad{width:46px; height:46px; border-radius:12px; background:#fff; border:1px solid rgba(0,0,0,0.10); display:flex; align-items:center; justify-content:center; font-weight:1000; font-size:22px;}
.desc{font-size:22px; font-weight:1000;} .meta{font-size:22px; font-weight:1000;}
.tag-red{background:var(--tag_red_bg); border-color:var(--tag_red_line);}
.tag-blue{background:var(--tag_blue_bg); border-color:var(--tag_blue_line);}
.tag-yellow{background:var(--tag_yellow_bg); border-color:var(--tag_yellow_line);}
.tag-orange{background:var(--tag_orange_bg); border-color:var(--tag_orange_line);}
.tag-gray{background:var(--tag_gray_bg); border-color:var(--tag_gray_line);}
.footer{margin-top:auto; border:1px solid var(--line); border-radius:14px; background:#fff; padding:14px 16px; display:flex; justify-content:space-between; font-size:26px; font-weight:1000; color:#525b68;}
.footer .k{color:#6b7483; font-weight:1000; margin-right:10px;}
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

st.markdown(CSS, unsafe_allow_html=True)

kind, primary_pad, primary_label = pick_primary(pads)
mode = wall_mode(kind)

banner_cls, banner_text = top_banner(pads, mode, state, primary_pad, primary_label)
st.markdown(f'<div class="banner {banner_cls}">{banner_text}</div>', unsafe_allow_html=True)

left_html = build_left_panel(kind, primary_pad, primary_label)
right_html = build_right_stack(pads)

# Footer counts (operational meaning)
at_base = sum(1 for p in pads if p.phase == "AT_BASE")
arriving_soon = sum(1 for p in pads if p.phase == "COLLECTING")
cancelled = 0  # demo constant

right_html += f"""
<div class="footer">
  <div><span class="k">At Base</span>{at_base}</div>
  <div><span class="k">Arriving Soon</span>{arriving_soon}</div>
  <div><span class="k">Cancelled</span>{cancelled}</div>
</div>
"""
st.markdown(f'<div class="shell">{left_html}<div class="right">{right_html}</div></div>', unsafe_allow_html=True)
