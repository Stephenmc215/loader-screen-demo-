import random
from dataclasses import dataclass
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Loader Wall Screen Demo", layout="wide")

# -----------------------------
# Simulation timing
# -----------------------------
TICK_SECONDS = 2
REFRESH_MS = TICK_SECONDS * 1000

# -----------------------------
# Simulation model
# -----------------------------
@dataclass
class PadState:
    pad: str
    order: int
    storage: str     # HEAT/SHELF/FREEZER
    phase: str       # FLIGHT/LANDING/LOADING/FIXING
    t: int           # seconds remaining in current phase
    action: str      # "", numeric next order, or issue text
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
    r = random.random()
    if r < 0.15:
        return "FREEZER"
    if r < 0.40:
        return "HEAT"
    return "SHELF"

def storage_emoji(storage: str) -> str:
    return {"HEAT": "🔥", "SHELF": "📦", "FREEZER": "🧊"}.get(storage, "")

def severity(action: str) -> int:
    return {"Repress Pad": 1, "Change Cassette": 2, "Reboot Drone": 3, "Change Drone": 4}.get(action, 0)

def init_pads(n: int = 8):
    pads = []
    o = 100
    for i in range(n):
        pads.append(PadState(chr(65 + i), o, pick_storage(), "FLIGHT", random.randint(20, rand_flight()), "", False))
        o = next_order(o)
    return pads

# One sim per session (each viewer gets their own sim)
if "pads" not in st.session_state:
    st.session_state.pads = init_pads(8)
    st.session_state.seed = random.randint(1, 10_000_000)
    random.seed(st.session_state.seed)

pads = st.session_state.pads

# Step simulation
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
        p.action = str(next_order(p.order))  # next order to load
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
            p.storage = pick_storage()
            p.t = rand_flight()
            p.action = ""

    elif p.phase == "FIXING" and p.t == 0:
        p.phase = "FLIGHT"
        p.order = next_order(p.order)
        p.storage = pick_storage()
        p.t = rand_flight()
        p.action = ""
        p.fault = False

# -----------------------------
# Deterministic priority rules
# -----------------------------
IMMINENT = 15
LANDING_SOON = 30

imminent = [p for p in pads if p.phase == "FLIGHT" and p.t <= IMMINENT]
landing_soon = [p for p in pads if p.phase == "FLIGHT" and p.t <= LANDING_SOON]

issues = [p for p in pads if severity(p.action) > 0]
critical = [p for p in issues if severity(p.action) >= 4]
noncrit_issues = [p for p in issues if 0 < severity(p.action) < 4]

# Top bar (interrupt only for HIGH/CRITICAL)
best_issue = max(issues, key=lambda x: severity(x.action), default=None)
if best_issue and severity(best_issue.action) >= 4:
    top_text = f"CRITICAL: {best_issue.action} (Pad {best_issue.pad})"
    top_bg = "#b91c1c"
elif best_issue and severity(best_issue.action) == 3:
    top_text = f"HIGH: {best_issue.action} (Pad {best_issue.pad})"
    top_bg = "#b45309"
else:
    top_text = "RPP: 2 mins"
    top_bg = "#1f3a8a"

# Left beacon
beacon_pad = ""
beacon_title = ""
beacon_sub = ""
beacon_order = ""
beacon_hint = ""
beacon_class = "u-neutral"
pulse = False

if imminent:
    p = min(imminent, key=lambda x: x.t)
    beacon_title = "GO TO PAD"
    beacon_pad = p.pad
    beacon_sub = f"Landing in {p.t}s"
    beacon_order = f"{storage_emoji(p.storage)} {p.order}"
    beacon_hint = "Prepare to receive and load on landing"
    if p.t < 10:
        beacon_class = "u-red"
        pulse = True
    elif p.t <= 30:
        beacon_class = "u-amber"
    else:
        beacon_class = "u-neutral"
elif critical:
    p = max(critical, key=lambda x: severity(x.action))
    beacon_title = "ATTENTION REQUIRED"
    beacon_pad = p.pad
    beacon_sub = p.action
    beacon_order = f"{storage_emoji(p.storage)} {p.order}"
    beacon_hint = "Resolve issue during loading window"
    beacon_class = "u-red"
elif noncrit_issues:
    p = max(noncrit_issues, key=lambda x: severity(x.action))
    beacon_title = "ATTENTION REQUIRED"
    beacon_pad = p.pad
    beacon_sub = p.action
    beacon_order = f"{storage_emoji(p.storage)} {p.order}"
    beacon_hint = "Resolve issue during loading window"
    beacon_class = "u-amber"
elif landing_soon:
    p = min(landing_soon, key=lambda x: x.t)
    beacon_title = "UP NEXT"
    beacon_pad = p.pad
    beacon_sub = f"Landing in {p.t}s"
    beacon_order = f"{storage_emoji(p.storage)} {p.order}"
    beacon_hint = "Next arrival approaching"
    beacon_class = "u-neutral"
else:
    beacon_title = "RPP"
    beacon_pad = ""
    beacon_sub = "2 mins"
    beacon_order = ""
    beacon_hint = "No urgent arrivals or issues"
    beacon_class = "u-neutral"

# Right stack
landing_blocks = sorted([p for p in pads if p.phase == "FLIGHT"], key=lambda x: x.t)

idle_pads = []
for p in pads:
    if severity(p.action) != 0:
        continue
    # exclude pads already shown in landing soon list
    idle_pads.append(p)

def item_html(p: PadState, label: str, meta: str, tag: str) -> str:
    return f"""
    <div class="item {tag}">
      <div class="item-left">
        <div class="pad">{p.pad}</div>
        <div class="desc">{label}</div>
      </div>
      <div class="meta">{meta}</div>
    </div>
    """

critical_items = "".join(
    item_html(p, p.action, f"{storage_emoji(p.storage)} {p.order}", "tag-red")
    for p in sorted(critical, key=lambda x: severity(x.action), reverse=True)
) or '<div class="item tag-gray"><div class="desc">None</div></div>'

issues_items = "".join(
    item_html(p, p.action, f"{storage_emoji(p.storage)} {p.order}", "tag-blue")
    for p in sorted(noncrit_issues, key=lambda x: severity(x.action), reverse=True)
) or '<div class="item tag-gray"><div class="desc">None</div></div>'

landing_items = "".join(
    item_html(p, "Landing", f"{p.t}s • {storage_emoji(p.storage)} {p.order}", "tag-orange")
    for p in landing_blocks[:4]
) or '<div class="item tag-gray"><div class="desc">None</div></div>'

idle_items = "".join(
    item_html(p, "Idle", ("At base" if p.phase in ("LANDING","LOADING","FIXING") else "In flight"), "tag-gray")
    for p in sorted(idle_pads, key=lambda x: x.pad)[:6]
) or '<div class="item tag-gray"><div class="desc">None</div></div>'

at_base = sum(1 for p in pads if p.phase in ("LANDING", "LOADING", "FIXING"))
arriving = sum(1 for p in pads if p.phase == "FLIGHT")
cancelled = 0

# -----------------------------
# Render with components.html (prevents raw HTML showing)
# -----------------------------
pulse_class = "pulse" if pulse else ""
pad_line = f"<div class='beacon-pad'>➡ {beacon_pad}</div>" if beacon_pad else ""
order_line = f"<div class='beacon-order'><span class='emo'>{beacon_order.split(' ')[0]}</span>{' '.join(beacon_order.split(' ')[1:])}</div>" if beacon_order else ""

page = f"""
<!doctype html>
<html>
<head>
<meta charset="utf-8"/>
<meta http-equiv="refresh" content="{REFRESH_MS/1000.0}">
<style>
  html, body {{ height: 100%; }}
  body {{ margin: 0; padding: 0; font-family: system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; background:#ffffff; }}
  .topbar {{
    border-radius: 18px;
    padding: 18px 22px;
    text-align: center;
    color: #ffffff;
    font-weight: 900;
    font-size: 52px;
    margin: 6px 8px 14px 8px;
    background: {top_bg};
  }}
  .wall {{
    display: grid;
    grid-template-columns: 60% 40%;
    gap: 18px;
    align-items: stretch;
    padding: 0 8px 8px 8px;
  }}
  .beacon {{
    border-radius: 18px;
    border: 1px solid #e5e7eb;
    padding: 22px 26px;
    background: #ffffff;
    height: calc(100vh - 140px);
    display: flex;
    flex-direction: column;
    justify-content: center;
  }}
  .beacon-title {{ font-size: 34px; font-weight: 900; color: #111827; letter-spacing: 0.02em; margin-bottom: 18px; }}
  .beacon-pad {{ font-size: 140px; font-weight: 1000; line-height: 1.0; margin: 0; color:#111827; }}
  .beacon-sub {{ font-size: 46px; font-weight: 900; margin-top: 10px; color:#111827; }}
  .beacon-order {{ margin-top: 18px; font-size: 40px; font-weight: 800; color: #111827; }}
  .beacon-order .emo {{ font-size: 38px; margin-right: 12px; }}
  .beacon-hint {{ margin-top: 18px; font-size: 28px; color: #374151; font-weight: 700; }}

  .u-neutral {{ background: #ffffff; }}
  .u-amber {{ background: #fff7ed; }}
  .u-red {{ background: #fff1f2; }}
  .pulse {{ border: 5px solid #b91c1c !important; animation: pulse 1.0s infinite; }}
  @keyframes pulse {{
    0% {{ box-shadow: 0 0 0 0 rgba(185, 28, 28, 0.55); }}
    70% {{ box-shadow: 0 0 0 18px rgba(185, 28, 28, 0.0); }}
    100% {{ box-shadow: 0 0 0 0 rgba(185, 28, 28, 0.0); }}
  }}

  .stack {{ height: calc(100vh - 140px); display:flex; flex-direction:column; gap:14px; }}
  .section {{ border-radius: 18px; border: 1px solid #e5e7eb; overflow:hidden; background:#ffffff; }}
  .section-h {{ padding: 12px 16px; font-size: 22px; font-weight: 900; letter-spacing: 0.02em; border-bottom: 1px solid #eef2f7; }}
  .h-critical {{ background: #fee2e2; color:#7f1d1d; }}
  .h-landing {{ background: #ffedd5; color:#7c2d12; }}
  .h-issues {{ background: #e0e7ff; color:#1e3a8a; }}
  .h-idle {{ background: #f3f4f6; color:#111827; }}
  .items {{ padding: 10px 12px; display:flex; flex-direction:column; gap:10px; }}

  .item {{ border-radius:14px; padding:12px 14px; border:1px solid #eef2f7; display:flex; align-items:center; justify-content:space-between; gap:10px; }}
  .item-left {{ display:flex; align-items:baseline; gap:12px; }}
  .pad {{ font-size:34px; font-weight:1000; color:#111827; min-width:42px; }}
  .desc {{ font-size:22px; font-weight:800; color:#111827; }}
  .meta {{ font-size:22px; font-weight:900; color:#111827; }}

  .tag-red {{ background:#fecaca; border-color:#fca5a5; }}
  .tag-orange {{ background:#ffedd5; border-color:#fdba74; }}
  .tag-blue {{ background:#dbeafe; border-color:#93c5fd; }}
  .tag-gray {{ background:#f3f4f6; border-color:#e5e7eb; }}

  .footer {{ margin-top:auto; border-radius:18px; border:1px solid #e5e7eb; background:#ffffff; padding:14px 16px; display:flex; gap:18px; justify-content:space-between; font-size:22px; font-weight:900; color:#111827; }}
  .k {{ color:#6b7280; font-weight:800; margin-right:8px; }}
</style>
</head>
<body>
  <div class="topbar">{top_text}</div>

  <div class="wall">
    <div class="beacon {beacon_class} {pulse_class}">
      <div class="beacon-title">{beacon_title}</div>
      {pad_line}
      <div class="beacon-sub">{beacon_sub}</div>
      {order_line}
      <div class="beacon-hint">{beacon_hint}</div>
    </div>

    <div class="stack">
      <div class="section">
        <div class="section-h h-critical">🔴 CRITICAL</div>
        <div class="items">{critical_items}</div>
      </div>

      <div class="section">
        <div class="section-h h-issues">⚠️ ATTENTION</div>
        <div class="items">{issues_items}</div>
      </div>

      <div class="section">
        <div class="section-h h-landing">🟠 LANDING SOON</div>
        <div class="items">{landing_items}</div>
      </div>

      <div class="section">
        <div class="section-h h-idle">⚪ IDLE</div>
        <div class="items" style="max-height: 220px; overflow: hidden;">{idle_items}</div>
      </div>

      <div class="footer">
        <div><span class="k">At Base</span>{at_base}</div>
        <div><span class="k">Arriving</span>{arriving}</div>
        <div><span class="k">Cancelled</span>{cancelled}</div>
      </div>
    </div>
  </div>
</body>
</html>
"""

# Make the component fill most of the page
components.html(page, height=920, scrolling=False)
