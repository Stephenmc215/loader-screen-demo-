import random
import time
import streamlit as st

st.set_page_config(layout="wide", page_title="Loader Wall")

PADS = ["A", "B", "C", "D", "E", "F"]

TOP_ALERTS = [
    "Heavy rain - wipe lidar",
    "Space weather over limits",
    "Icing pre flight checklist",
    "Weather above limits. Put everything in the heat.",
    "Containment Breach Grounding",
]

# -------------------------
# REFRESH (SAFE)
# -------------------------
def setup_refresh():
    # Best option: streamlit-autorefresh (non-blocking)
    try:
        from streamlit_autorefresh import st_autorefresh
        st_autorefresh(interval=2000, key="wall_refresh")  # 2s
        return
    except Exception:
        pass

    # Fallback: manual rerun buttonless (works, but can be slightly "janky")
    # We'll trigger rerun by using session state timestamp
    if "last_rerun" not in st.session_state:
        st.session_state.last_rerun = time.time()

    if time.time() - st.session_state.last_rerun >= 2:
        st.session_state.last_rerun = time.time()
        # Version-safe rerun
        if hasattr(st, "rerun"):
            st.rerun()
        elif hasattr(st, "experimental_rerun"):
            st.experimental_rerun()

setup_refresh()

# -------------------------
# TOP BAR LOGIC (5% alert)
# -------------------------
if "alert_timer" not in st.session_state:
    st.session_state.alert_timer = 0
    st.session_state.current_alert = None

# refresh alert state every ~8 seconds worth of refreshes (2s refresh -> 4 ticks)
if st.session_state.alert_timer <= 0:
    if random.random() < 0.05:
        st.session_state.current_alert = random.choice(TOP_ALERTS)
        st.session_state.alert_timer = 4  # 4 ticks * 2s = 8s
    else:
        st.session_state.current_alert = None
        st.session_state.alert_timer = 1
else:
    st.session_state.alert_timer -= 1

# -------------------------
# SIMPLE ORDER SIMULATION
# -------------------------
def generate_orders():
    orders = []
    for pad in PADS:
        state = random.choice(["LOAD", "LOAD", "ATTENTION", "NONE"])
        if state == "NONE":
            continue
        orders.append(
            {
                "pad": pad,
                "state": state,           # LOAD | ATTENTION
                "time": random.randint(5, 60),
                "id": random.randint(100, 999),
                "critical": random.random() < 0.10,
            }
        )
    return orders

orders = generate_orders()

critical = [o for o in orders if o["critical"]]
attention = [o for o in orders if (o["state"] == "ATTENTION" and not o["critical"])]
load = [o for o in orders if (o["state"] == "LOAD" and not o["critical"])]

primary = load[0] if load else (attention[0] if attention else None)

# -------------------------
# STYLING
# -------------------------
st.markdown(
    """
<style>
:root{
  --navy:#2f4a8a;
  --bg:#f4f6f9;
  --card:#ffffff;
  --line:#e5eaf2;
  --muted:#6b7280;
  --ink:#0b1320;

  --red_bg:#fde8e8;
  --red_ink:#7f1d1d;

  --yellow_bg:#fff7cc;
  --yellow_ink:#6a5400;

  --attn_bg:#fff1d6;
  --attn_ink:#7a3a00;
}

html, body, [data-testid="stAppViewContainer"]{
  background: var(--bg) !important;
}

.main .block-container{
  max-width: 1600px;
  padding-top: 1rem;
  padding-bottom: 1rem;
}

.topbar{
  background: var(--navy);
  color:#fff;
  padding: 16px 26px;
  border-radius: 16px;
  font-size: 22px;
  font-weight: 650;
  display:flex;
  justify-content:space-between;
  align-items:center;
}

.topbar.alert{
  background: #b91c1c;
}

.shell{
  display:flex;
  gap:16px;
  margin-top:14px;
}

.left{
  flex: 0 0 65%;
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 18px;
  padding: 44px 48px;
  min-height: 72vh;
  display:flex;
  flex-direction:column;
  justify-content:center;
}

.right{
  flex: 0 0 35%;
  display:flex;
  flex-direction:column;
  gap:14px;
}

.primary-kicker{
  font-size: 26px;
  letter-spacing: 1px;
  font-weight: 700;
  color: #9aa3af;
  margin-bottom: 18px;
}

.pad-letter{
  font-size: 160px;
  line-height: 0.95;
  font-weight: 800;
  color: var(--ink);
  margin: 8px 0 18px 0;
}

.primary-title{
  font-size: 56px;
  line-height: 1.05;
  font-weight: 800;
  color: var(--ink);
  margin-bottom: 18px;
}

.primary-sub{
  font-size: 26px;
  font-weight: 700;
  color: var(--muted);
}

.card{
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 18px;
  overflow:hidden;
}

.card-h{
  padding: 14px 18px;
  font-size: 20px;
  font-weight: 800;
  letter-spacing: 0.4px;
  display:flex;
  align-items:center;
  gap:10px;
}

.h-critical{ background: var(--red_bg); color: var(--red_ink); }
.h-attn{ background: var(--attn_bg); color: var(--attn_ink); }
.h-load{ background: var(--yellow_bg); color: var(--yellow_ink); }

.dot{
  width:14px; height:14px; border-radius:999px;
  background: currentColor;
  opacity: 0.9;
}

.items{
  padding: 14px;
  display:flex;
  flex-direction:column;
  gap:10px;
}

.row{
  padding: 12px 14px;
  border: 1px solid var(--line);
  border-radius: 14px;
  display:flex;
  justify-content:space-between;
  align-items:center;
  background:#fff;
}

.row-left{
  display:flex;
  align-items:center;
  gap:12px;
}

.badge{
  width:48px; height:48px;
  border-radius: 14px;
  border: 1px solid var(--line);
  display:flex;
  align-items:center;
  justify-content:center;
  font-weight: 800;
  font-size: 20px;
  color: var(--ink);
  background:#fff;
}

.row-main{
  font-size: 22px;
  font-weight: 800;
  color: var(--ink);
}

.row-right{
  font-size: 22px;
  font-weight: 800;
  color: var(--muted);
}

.none{
  color: var(--muted);
  font-weight: 700;
  font-size: 20px;
  padding: 6px 2px;
}
</style>
""",
    unsafe_allow_html=True,
)

# -------------------------
# TOP BAR RENDER
# -------------------------
if st.session_state.current_alert:
    st.markdown(
        f'<div class="topbar alert">{st.session_state.current_alert}</div>',
        unsafe_allow_html=True,
    )
else:
    wind = random.randint(5, 10)
    st.markdown(
        f'<div class="topbar"><div>RPP: 2 mins</div><div>Wind: {wind} m/s</div></div>',
        unsafe_allow_html=True,
    )

# -------------------------
# MAIN LAYOUT
# -------------------------
st.markdown('<div class="shell">', unsafe_allow_html=True)

# LEFT
left_html = '<div class="left">'
left_html += '<div class="primary-kicker">NEXT ACTION</div>'

if primary:
    left_html += f'<div class="pad-letter">{primary["pad"]}</div>'
    left_html += '<div class="primary-title">Load order</div>'
    left_html += f'<div class="primary-sub">Order {primary["id"]} • {primary["time"]}s</div>'
else:
    left_html += '<div class="primary-title">All clear</div>'
    left_html += '<div class="primary-sub">Waiting for next order</div>'

left_html += "</div>"

# RIGHT
def card(title, cls, items):
    if not items:
        return ""
    rows = ""
    for o in items[:3]:
        rows += (
            '<div class="row">'
            f'  <div class="row-left"><div class="badge">{o["pad"]}</div>'
            f'    <div class="row-main">{o.get("label","")}</div></div>'
            f'  <div class="row-right">{o.get("right","")}</div>'
            "</div>"
        )
    return (
        '<div class="card">'
        f'  <div class="card-h {cls}"><span class="dot"></span>{title}</div>'
        f'  <div class="items">{rows}</div>'
        "</div>"
    )

crit_items = [{"pad": o["pad"], "label": f"Order {o['id']}", "right": "CRIT"} for o in critical]
attn_items = [{"pad": o["pad"], "label": f"Order {o['id']}", "right": f"{o['time']}s"} for o in attention]
load_items = [{"pad": o["pad"], "label": f"{o['time']}s", "right": f"Order {o['id']}"} for o in load]

right_html = '<div class="right">'
right_html += card("CRITICAL", "h-critical", crit_items)
right_html += card("REQUIRES ATTENTION", "h-attn", attn_items)
right_html += card("LOAD", "h-load", load_items)
right_html += "</div>"

st.markdown(left_html + right_html, unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)
