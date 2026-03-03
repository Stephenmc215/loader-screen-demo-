import random
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import streamlit as st

st.set_page_config(page_title="Loader Wall Screen", layout="wide")

PADS = list("ABCDEFGH")
ORDER_MIN = 100
ORDER_MAX = 999
ORDER_STEP = 3

LOAD_SECONDS = 60
FIX_EXTRA_SECONDS = 30
COLLECT_MIN = 25
COLLECT_MAX = 110
AT_BASE_MIN = 10
AT_BASE_MAX = 60
SIM_SPEED = 2

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

STORAGE_EMOJI = ["🔥", "📦", "🧊"]

RPP_TEXT = "RPP: 2 mins"
WEATHER_MESSAGES = [
    "Weather: Visibility OK",
    "Weather: Light rain",
    "Weather: Wind steady",
    "Weather: Low cloud",
]
WEATHER_ROTATE_SECONDS = 6

TOPBAR_ALERT_RATE = 0.05
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

@dataclass
class PadState:
    pad: str
    phase: str                 # COLLECTING | AT_BASE | LOADING
    remaining: int
    order_id: int
    storage: str
    issue: Optional[str] = None
    severity: Optional[str] = None   # critical | attention
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
        candidates = [t for sev, t in ISSUES if sev == "critical"]
        return rng.choice(candidates), "critical"
    candidates = [t for sev, t in ISSUES if sev == "attention"]
    return rng.choice(candidates), "attention"

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
            remaining=rng.randint(COLLECT_MIN, COLLECT_MAX),
            order_id=order_id,
            storage=pick_storage(rng),
        )
    return {
        "rng": rng,
        "pads": pads,
        "last_tick": time.time(),
        "weather_idx": 0,
        "weather_next": time.time() + WEATHER_ROTATE_SECONDS,
        "wind_ms": rng.randint(WIND_MIN_MS, WIND_MAX_MS),
        "topbar_is_alert": False,
        "topbar_alert_id": None,
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
                p.phase = "AT_BASE"
                p.remaining = rng.randint(AT_BASE_MIN, AT_BASE_MAX)
            elif p.phase == "AT_BASE" and p.remaining == 0:
                p.phase = "LOADING"
                p.issue, p.severity = maybe_issue(rng)
                p.fix_left = FIX_EXTRA_SECONDS if p.issue else 0
                p.remaining = LOAD_SECONDS + (FIX_EXTRA_SECONDS if p.issue else 0)
            elif p.phase == "LOADING":
                if p.issue and p.fix_left > 0:
                    p.fix_left = max(0, p.fix_left - 1)
                if p.remaining == 0:
                    p.phase = "COLLECTING"
                    p.remaining = rng.randint(COLLECT_MIN, COLLECT_MAX)
                    p.order_id = next_order(p.order_id)
                    p.storage = pick_storage(rng)
                    p.issue = None
                    p.severity = None
                    p.fix_left = 0
    if time.time() >= state.get("weather_next", 0):
        state["weather_idx"] = (state["weather_idx"] + 1) % len(WEATHER_MESSAGES)
        state["weather_next"] = time.time() + WEATHER_ROTATE_SECONDS

def update_topbar(state: Dict) -> None:
    rng: random.Random = state["rng"]
    is_alert = rng.random() < TOPBAR_ALERT_RATE
    state["topbar_is_alert"] = is_alert
    if is_alert:
        state["topbar_alert_id"] = rng.choice(TOPBAR_ALERT_IDS)
    else:
        state["topbar_alert_id"] = None
        state["wind_ms"] = rng.randint(WIND_MIN_MS, WIND_MAX_MS)

def pick_primary(pads: List[PadState]) -> Tuple[str, Optional[PadState], str]:
    critical = [p for p in pads if p.phase == "LOADING" and p.issue and p.severity == "critical"]
    if critical:
        p = sorted(critical, key=lambda x: x.pad)[0]
        return "critical", p, p.issue or "Critical issue"
    attention = [p for p in pads if p.phase == "LOADING" and p.issue and p.severity == "attention"]
    if attention:
        p = sorted(attention, key=lambda x: x.pad)[0]
        return "attention", p, p.issue or "Needs attention"
    loading = [p for p in pads if p.phase == "LOADING" and not p.issue]
    if loading:
        p = sorted(loading, key=lambda x: x.remaining)[0]
        return "loading", p, "Load Order"
    return "calm", None, "All clear"

def top_strip_html(state: Dict) -> str:
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
    wind = state.get("wind_ms", 7)
    return f"""
<div class="topstrip">
  <div class="ts-left">{RPP_TEXT}</div>
  <div class="ts-mid">Wind: {wind} m/s</div>
</div>
"""

def primary_html(kind: str, p: Optional[PadState], label: str) -> Tuple[str, str]:
    urgent = kind == "critical"
    wrap_cls = "primarywrap urgent" if urgent else "primarywrap"
    if kind == "calm" or p is None:
        return wrap_cls, """
<div class="primary">
  <div class="p-next">NEXT ACTION</div>
  <div class="p-action">All clear</div>
  <div class="p-sub">Waiting for next order</div>
</div>
"""
    order_line = f"{p.storage} {p.order_id}"
    arrow = "&rarr;"
    if kind in ("critical", "attention"):
        return wrap_cls, f"""
<div class="primary">
  <div class="p-next">NEXT ACTION</div>
  <div class="p-row">
    <div class="p-arrow">{arrow}</div>
    <div class="p-pad">{p.pad}</div>
  </div>
  <div class="p-action">{label}</div>
  <div class="p-sub">{order_line}</div>
</div>
"""
    return wrap_cls, f"""
<div class="primary">
  <div class="p-next">NEXT ACTION</div>
  <div class="p-row">
    <div class="p-arrow">{arrow}</div>
    <div class="p-pad">{p.pad}</div>
  </div>
  <div class="p-action">{label}</div>
  <div class="p-count">{p.remaining}s</div>
  <div class="p-sub">{order_line}</div>
</div>
"""

def stack_section(title: str, title_cls: str, items: List[str], more_count: int) -> str:
    html = f"""
<div class="stack-section">
  <div class="stack-title {title_cls}">{title}</div>
  <div class="stack-items">
    {''.join(items)}
"""
    if more_count > 0:
        html += f'<div class="more">+{more_count} more</div>'

    html += """
  </div>
</div>
"""
    return html

def stack_item(pad: str, left_text: str, right_text: str) -> str:
    return f"""
<div class="sitem">
  <div class="spad">{pad}</div>
  <div class="sleft">{left_text}</div>
  <div class="sright">{right_text}</div>
</div>
"""

def build_status_stack(pads: List[PadState]) -> str:
    critical = sorted([p for p in pads if p.phase == "LOADING" and p.issue and p.severity == "critical"], key=lambda x: x.pad)
    crit_items = [stack_item(p.pad, p.issue or "Critical", f"{p.storage} {p.order_id}") for p in critical[:3]]
    crit_more = max(0, len(critical) - 3)

    active = [p for p in pads if p.phase == "LOADING" and (p.severity == "attention" or (not p.issue))]
    def active_key(x: PadState):
        sev_rank = 0 if x.severity == "attention" else 1
        return (sev_rank, x.remaining, x.pad)
    active = sorted(active, key=active_key)
    active_items: List[str] = []
    for p in active[:3]:
        if p.severity == "attention" and p.issue:
            active_items.append(stack_item(p.pad, p.issue, f"{p.storage} {p.order_id}"))
        else:
            active_items.append(stack_item(p.pad, f"{p.remaining}s", f"{p.storage} {p.order_id}"))
    active_more = max(0, len(active) - 3)

    queue = [p for p in pads if p.phase in ("COLLECTING", "AT_BASE")]
    def queue_key(x: PadState):
        rank = 0 if x.phase == "AT_BASE" else 1
        return (rank, x.remaining, x.pad)
    queue = sorted(queue, key=queue_key)
    queue_items: List[str] = []
    for p in queue[:3]:
        if p.phase == "AT_BASE":
            queue_items.append(stack_item(p.pad, "At base", f"{p.storage} {p.order_id}"))
        else:
            queue_items.append(stack_item(p.pad, f"{p.remaining}s", f"{p.storage} {p.order_id}"))
    queue_more = max(0, len(queue) - 3)

    html = '<div class="statuswrap">'
    if critical:
        html += stack_section("🔴 CRITICAL", "t-critical", crit_items, crit_more)
    if active:
        html += stack_section("🟡 ACTIVE / LOADING", "t-active", active_items, active_more)
    if queue:
        html += stack_section("⚪ QUEUE", "t-queue", queue_items, queue_more)
    html += "</div>"
    return html

def footer_html(pads: List[PadState]) -> str:
    at_base = sum(1 for p in pads if p.phase in ("AT_BASE", "LOADING"))
    arriving_soon = sum(1 for p in pads if p.phase == "COLLECTING")
    cancelled = 0
    return f"""
<div class="footer">
  <div><span class="k">At Base</span>{at_base}</div>
  <div><span class="k">Arriving Soon</span>{arriving_soon}</div>
  <div><span class="k">Cancelled</span>{cancelled}</div>
</div>
"""

CSS = """
<style>
*{box-sizing:border-box;}
:root{
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
.main .block-container{padding-top:0.4rem; padding-bottom:0.4rem; max-width:1800px;}
.grid{height:calc(100vh - 0.8rem); display:grid; grid-template-rows:10fr 82fr 8fr; gap:8px; min-height:0;}
.topstrip{border-radius:18px; padding:0 22px; display:grid; grid-template-columns:1fr 1.6fr; align-items:center; font-weight:1000; background:var(--navy);}
.topstrip.alert-red{background:var(--red);}
.topstrip.alert-amber{background:var(--amber);}
.ts-left{font-size:clamp(18px,2.3vw,40px); text-align:left; color:rgba(255,255,255,0.95);}
.ts-mid{font-size:clamp(16px,2.0vw,36px); text-align:right; color:rgba(255,255,255,0.78);}
.mainrow{display:grid; grid-template-columns:65% 35%; gap:8px; align-items:stretch; min-height:0;}
.primarywrap{background:var(--primary_bg); border-radius:18px; border:2px solid var(--primary_line); display:flex; align-items:center; justify-content:center; overflow:hidden;}
.primarywrap.urgent{background:var(--urgent_bg); border:4px solid var(--red);}
.primary{width:100%; height:100%; padding:clamp(12px,1.8vh,24px) clamp(12px,1.8vw,28px); display:flex; flex-direction:column; justify-content:center; color:var(--ink);}
.p-next{font-size:clamp(20px,2.6vw,44px); font-weight:1000; letter-spacing:1px; color:var(--muted); margin-bottom:clamp(8px,1.2vh,14px);}
.p-row{display:flex; align-items:center; gap:clamp(14px,2.0vw,36px);}
.p-arrow{font-size:clamp(80px,9vw,170px); font-weight:1000; line-height:1; color:var(--ink); opacity:0.95;}
.p-pad{font-size:clamp(120px,16vw,300px); font-weight:1000; line-height:0.9; color:var(--ink);}
.p-action{margin-top:clamp(6px,1.1vh,12px); font-size:clamp(34px,5.4vw,88px); font-weight:1000; line-height:1.05; color:var(--ink);}
.p-count{margin-top:clamp(4px,0.9vh,10px); font-size:clamp(52px,8.2vw,130px); font-weight:1000; line-height:1; color:var(--ink);}
.p-sub{margin-top:clamp(8px,1.2vh,14px); font-size:clamp(18px,3.2vw,44px); font-weight:1000; color:var(--muted);}
.statuswrap{display:flex; flex-direction:column; gap:8px; min-height:0; overflow:auto; padding-right:2px;}
.stack-section{background:var(--card); border:1px solid var(--line); border-radius:18px; overflow:hidden; display:flex; flex-direction:column;}
.stack-title{padding:10px 14px; font-size:clamp(18px,2.6vw,36px); font-weight:1000; letter-spacing:0.8px;}
.t-critical{background:var(--crit_bg); color:var(--crit_text); border-bottom:1px solid var(--crit_line);}
.t-active{background:var(--load_bg); color:var(--load_text); border-bottom:1px solid var(--load_line);}
.t-queue{background:var(--queue_bg); color:var(--queue_text); border-bottom:1px solid var(--queue_line);}
.stack-items{padding:10px 12px 12px 12px; display:flex; flex-direction:column; gap:8px;}
.sitem{display:grid; grid-template-columns:clamp(54px,4.4vw,76px) 1fr auto; align-items:center; column-gap:12px; padding:8px 10px; border-radius:14px; border:1px solid var(--queue_line); background:#ffffff;}
.spad{width:clamp(42px,3.8vw,62px); height:clamp(42px,3.8vw,62px); border-radius:14px; background:#fff; border:1px solid rgba(0,0,0,0.10); display:flex; align-items:center; justify-content:center; font-size:clamp(18px,2.5vw,34px); font-weight:1000; color:var(--ink);}
.sleft{font-size:clamp(16px,2.3vw,32px); font-weight:1000; color:var(--ink); line-height:1; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;}
.sright{font-size:clamp(16px,2.3vw,32px); font-weight:1000; color:var(--ink); line-height:1; font-variant-numeric:tabular-nums; letter-spacing:0.4px; text-align:right; white-space:nowrap;}
.more{margin-top:2px; font-size:clamp(14px,2.0vw,26px); font-weight:1000; color:var(--muted); padding-left:6px;}
.footer{background:#ffffff; border:1px solid var(--line); border-radius:18px; padding:0 22px; display:flex; align-items:center; justify-content:space-between; color:#6b7483; font-size:clamp(14px,1.9vw,24px); font-weight:1000;}
.footer .k{color:#6b7483; margin-right:10px;}
</style>
"""

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
kind, primary_pad, primary_label = pick_primary(pads)

st.markdown(CSS, unsafe_allow_html=True)

topbar = top_strip_html(state)
wrap_cls, primary = primary_html(kind, primary_pad, primary_label)
stack = build_status_stack(pads)
footer = footer_html(pads)

st.markdown(
    f"""
<div class="grid">
  {topbar}
  <div class="mainrow">
    <div class="{wrap_cls}">{primary}</div>
    {stack}
  </div>
  {footer}
</div>
""",
    unsafe_allow_html=True,
)
