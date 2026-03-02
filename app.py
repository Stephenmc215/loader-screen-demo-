import random
from dataclasses import dataclass
import streamlit as st
from streamlit_autorefresh import st_autorefresh
import streamlit.components.v1 as components

st.set_page_config(page_title="Loader Screen Demo", layout="wide")

# -----------------------------
# Settings
# -----------------------------
TICK_SECONDS = 2
st_autorefresh(interval=TICK_SECONDS * 1000, key="loader_refresh")

# -----------------------------
# Parent-page CSS (banner + left metrics)
# -----------------------------
st.markdown("""
<style>
  .block-container { padding: 0.35rem 0.8rem !important; max-width: 100% !important; }
  .banner { border-radius: 18px; padding: 20px; text-align:center; color:white; font-weight:900; font-size:50px; margin-bottom:18px; }
  .metrics-col { padding-top: 8px; }
  .metric-label { font-size: 18px; color:#111827; margin-top: 28px; }
  .metric-value { font-size: 58px; font-weight: 900; line-height: 1.0; color:#111827; }
</style>
""", unsafe_allow_html=True)

# -----------------------------
# Simulation model
# -----------------------------
@dataclass
class Pad:
    pad: str
    order: int
    storage: str  # HEAT/SHELF/FREEZER
    phase: str    # FLIGHT/LANDING/LOADING/FIXING
    t: int        # seconds remaining in current phase
    action: str   # "", numeric next order, or issue text
    fault: bool

FLIGHT_MIN = 120
FLIGHT_MAX = 300
LANDING = 10
LOADING = 60
FIXING = 30

ISSUES = ["Repress Pad", "Change Cassette", "Reboot Drone", "Change Drone"]

def next_order(n: int) -> int:
    return 100 if n + 3 > 999 else n + 3

def rand_flight() -> int:
    return random.randint(FLIGHT_MIN, FLIGHT_MAX)

def pick_storage() -> str:
    # Keep shelf most common, then heat, then freezer
    r = random.random()
    if r < 0.15:
        return "FREEZER"
    if r < 0.40:
        return "HEAT"
    return "SHELF"

def storage_emoji(storage: str) -> str:
    return {"HEAT": "🔥", "SHELF": "📦", "FREEZER": "🧊"}.get(storage, "")

def init_pads(n: int = 8):
    pads = []
    o = 100
    for i in range(n):
        pads.append(Pad(chr(65 + i), o, pick_storage(), "FLIGHT", random.randint(20, rand_flight()), "", False))
        o = next_order(o)
    return pads

# One sim per session (each viewer gets their own sim)
if "pads" not in st.session_state:
    st.session_state.pads = init_pads(8)
    st.session_state.seed = random.randint(1, 10_000_000)
    random.seed(st.session_state.seed)

pads = st.session_state.pads

# -----------------------------
# Step simulation
# -----------------------------
for p in pads:
    p.t = max(0, p.t - TICK_SECONDS)

    if p.phase == "FLIGHT" and p.t == 0:
        p.phase = "LANDING"
        p.t = LANDING
        p.action = ""
        p.fault = False

    elif p.phase == "LANDING" and p.t == 0:
        p.phase = "LOADING"
        p.t = LOADING
        # Default "next action" when on ground is the next order to load
        p.action = str(next_order(p.order))
        p.fault = False

    elif p.phase == "LOADING":
        # Ground-only issues
        if not p.fault and random.random() < 0.04:
            p.fault = True
            p.phase = "FIXING"
            p.t = FIXING
            p.action = random.choice(ISSUES)

        # Finished loading with no fault => take off
        if p.t == 0 and not p.fault:
            p.phase = "FLIGHT"
            p.order = next_order(p.order)
            p.storage = pick_storage()  # new order => new storage location
            p.t = rand_flight()
            p.action = ""

    elif p.phase == "FIXING" and p.t == 0:
        # After fixing => take off
        p.phase = "FLIGHT"
        p.order = next_order(p.order)
        p.storage = pick_storage()  # new order => new storage location
        p.t = rand_flight()
        p.action = ""
        p.fault = False

# -----------------------------
# Banner logic (unchanged)
# -----------------------------
def severity(action: str) -> int:
    return {"Repress Pad": 1, "Change Cassette": 2, "Reboot Drone": 3, "Change Drone": 4}.get(action, 0)

best = max(pads, key=lambda x: severity(x.action))
sev = severity(best.action)

if sev >= 4:
    banner_text = f"CRITICAL: {best.action} (Pad {best.pad})"
    banner_bg = "#b91c1c"
elif sev == 3:
    banner_text = f"HIGH: {best.action} (Pad {best.pad})"
    banner_bg = "#b45309"
else:
    banner_text = "RPP: 2 mins"
    banner_bg = "#1f3a8a"

st.markdown(f"<div class='banner' style='background:{banner_bg};'>{banner_text}</div>", unsafe_allow_html=True)

# -----------------------------
# Layout
# -----------------------------
left, right = st.columns([1, 4], gap="large")

with left:
    at_base = sum(1 for p in pads if p.phase in ("LANDING", "LOADING", "FIXING"))
    arriving = sum(1 for p in pads if p.phase == "FLIGHT")

    st.markdown("<div class='metrics-col'>", unsafe_allow_html=True)
    st.markdown("<div class='metric-label'>At Base</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='metric-value'>{at_base}</div>", unsafe_allow_html=True)
    st.markdown("<div class='metric-label'>Arriving Soon</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='metric-value'>{arriving}</div>", unsafe_allow_html=True)
    st.markdown("<div class='metric-label'>Cancelled</div>", unsafe_allow_html=True)
    st.markdown("<div class='metric-value'>0</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

def action_class(a: str) -> str:
    return {
        "Repress Pad": "act-blue",
        "Change Cassette": "act-yellow",
        "Reboot Drone": "act-orange",
        "Change Drone": "act-red",
    }.get(a, "act-none")

# Decide which row gets the thick black focus box (highest severity issue, if any)
focus_pad = None
best_focus = 0
for p in pads:
    s = severity(p.action)
    if s > best_focus:
        best_focus = s
        focus_pad = p.pad
if best_focus == 0:
    focus_pad = None

# -----------------------------
# Table (rendered in iframe; include CSS inside iframe)
# -----------------------------
IFRAME_CSS = """
<style>
  body { margin: 0; padding: 0; font-family: system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; }
  .grid-wrap { border: 1px solid #e5e7eb; border-radius: 14px; overflow: hidden; background: white; }
  table.grid { width: 100%; border-collapse: collapse; table-layout: fixed; }
  table.grid th {
    text-align: left;
    font-size: 26px;
    padding: 16px 16px;
    border-bottom: 1px solid #e5e7eb;
    background: #f9fafb;
    color: #6b7280;
    font-weight: 700;
  }
  table.grid td {
    font-size: 34px;
    padding: 18px 16px;
    border-bottom: 1px solid #eef2f7;
    color: #111827;
    vertical-align: middle;
  }
  table.grid tr:last-child td { border-bottom: none; }

  .col-pad { width: 14%; }
  .col-order { width: 22%; }
  .col-rt { width: 22%; }
  .col-action { width: 42%; }

  .act-none { background: transparent; }
  .act-blue { background: #dbeafe; font-weight: 900; }
  .act-yellow { background: #fde68a; font-weight: 900; }
  .act-orange { background: #fdba74; font-weight: 900; }
  .act-red { background: #f87171; color: #ffffff; font-weight: 900; }

  /* RT highlight: orange badge when <= 10s to landing */
  .rt-warning { background:#fdba74; font-weight:900; padding:6px 10px; border-radius:8px; display:inline-block; }

  td.action-cell { border-left: 1px solid #eef2f7; }

  /* Focus row: thick black rectangle + larger text */
  tr.focus td {
    font-size: 42px !important;
    font-weight: 900 !important;
    border-top: 6px solid #000 !important;
    border-bottom: 6px solid #000 !important;
  }
  tr.focus td:first-child { border-left: 6px solid #000 !important; }
  tr.focus td:last-child  { border-right: 6px solid #000 !important; }

  /* Order cell: emoji smaller than number to reduce clutter */
  .order-emoji { font-size: 26px; margin-right: 10px; vertical-align: middle; display:inline-block; }
  .order-num { font-size: 34px; font-weight: 800; vertical-align: middle; display:inline-block; }
  tr.focus .order-emoji { font-size: 34px !important; }
  tr.focus .order-num { font-size: 42px !important; }
</style>
"""

with right:
    rows_html = []
    for p in pads:
        # No RT when craft is on the ground
        if p.phase in ("LANDING", "LOADING", "FIXING"):
            rt_display = ""
        else:
            rt_display = f"<span class='rt-warning'>{p.t}</span>" if p.t <= 10 else str(p.t)

        cls = action_class(p.action)
        row_class = "focus" if (focus_pad is not None and p.pad == focus_pad) else ""

        emoji = storage_emoji(p.storage)
        order_display = f"<span class='order-emoji'>{emoji}</span><span class='order-num'>{p.order}</span>"

        rows_html.append(
            f"<tr class='{row_class}'>"
            f"<td>{p.pad}</td>"
            f"<td>{order_display}</td>"
            f"<td>{rt_display}</td>"
            f"<td class='action-cell {cls}'>{p.action}</td>"
            f"</tr>"
        )

    table_html = f"""
    {IFRAME_CSS}
    <div class="grid-wrap">
      <table class="grid">
        <thead>
          <tr>
            <th class="col-pad">Pad</th>
            <th class="col-order">Order</th>
            <th class="col-rt">RT (s)</th>
            <th class="col-action">Next Action</th>
          </tr>
        </thead>
        <tbody>
          {''.join(rows_html)}
        </tbody>
      </table>
    </div>
    """

    components.html(table_html, height=820, scrolling=False)
