import random
import time
import streamlit as st

# ============================================================
# Loader Wall Screen — Blank Layout (V4)
# Clean canvas • 6 pads • No orders moving
# Top bar: 5% alert, else shows RPP + Wind (5–10 m/s)
# Typography: sleeker / less blocky for browser viewing
# ============================================================

st.set_page_config(page_title="Loader Wall Screen (Blank)", layout="wide")

# ----------------------------
# Alert config
# ----------------------------
ALERT_CHANCE = 0.05
ALERT_MESSAGES = [
    "Heavy rain — wipe lidar",
    "Space weather over limits",
    "Icing pre‑flight checklist",
    "Weather above limits — put everything in the heat",
    "Containment breach — grounding",
]

def pick_top_strip(rng: random.Random) -> tuple[str | None, int]:
    """Return (alert_message_or_None, wind_ms)."""
    wind_ms = rng.randint(5, 10)
    if rng.random() < ALERT_CHANCE:
        return rng.choice(ALERT_MESSAGES), wind_ms
    return None, wind_ms

# Keep alert stable for a short window so it doesn't flicker every refresh
ALERT_HOLD_SECONDS = 8

def get_state() -> dict:
    if "blank_state" not in st.session_state:
        st.session_state["blank_state"] = {
            "rng": random.Random(int(time.time())),
            "alert_until": 0.0,
            "alert_msg": None,
            "wind_ms": 7,
        }
    return st.session_state["blank_state"]

def update_top_strip(state: dict) -> None:
    now = time.time()
    rng: random.Random = state["rng"]

    # If current alert expired, re-roll
    if now >= state.get("alert_until", 0):
        alert_msg, wind_ms = pick_top_strip(rng)
        state["alert_msg"] = alert_msg
        state["wind_ms"] = wind_ms
        state["alert_until"] = now + ALERT_HOLD_SECONDS

state = get_state()

# Autorefresh
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=1000, key="blank_tick")
except Exception:
    pass

update_top_strip(state)
alert_msg = state["alert_msg"]
wind_ms = state["wind_ms"]

# ----------------------------
# UI (CSS)
# ----------------------------
CSS = """
<style>
:root{
  --navy:#1f3f8a;
  --ink:#0b1320;
  --muted:#6b7483;
  --card:#ffffff;
  --line:#e6e9ef;

  --critical_bg:#fbe3e3;
  --critical_ink:#7a1212;

  --active_bg:#fff7cf;
  --active_ink:#6a5400;

  --queue_bg:#f4f5f7;
  --queue_ink:#3b4350;

  --pad_bg:#ffffff;
  --shadow: 0 1px 0 rgba(16,24,40,0.06);
}

/* Streamlit container */
.main .block-container{max-width: 1500px; padding-top: 0.9rem; padding-bottom: 0.9rem;}
html, body {background:#ffffff;}

/* Top strip */
.topstrip{
  height: 10vh;
  min-height: 64px;
  max-height: 92px;
  background: var(--navy);
  color: #fff;
  border-radius: 18px;
  padding: 14px 18px;
  display:flex;
  align-items:center;
  justify-content:space-between;
  font-weight: 800;
  box-shadow: var(--shadow);
}
.topstrip .left, .topstrip .right{
  font-size: clamp(18px, 2.0vw, 34px);
  letter-spacing: 0.2px;
}
.topstrip.alert{
  background: #b51d1d;
}

/* Grid */
.grid{
  margin-top: 14px;
  display:grid;
  grid-template-columns: 65% 35%;
  grid-template-rows: 1fr auto;
  gap: 14px;
  height: 82vh;
  min-height: 520px;
}

/* Primary action panel */
.primary{
  grid-column: 1;
  grid-row: 1;
  background: #fff;
  border: 2px solid var(--line);
  border-radius: 18px;
  padding: 26px 28px;
  display:flex;
  flex-direction:column;
  justify-content:center;
}
.kicker{
  color:#9aa3b2;
  font-weight: 900;
  letter-spacing: 0.10em;
  font-size: clamp(18px, 1.8vw, 34px);
}
.bigrow{
  margin-top: 22px;
  display:flex;
  align-items:center;
  gap: 24px;
}
.arrow{
  font-size: clamp(70px, 8vw, 120px);
  font-weight: 900;
  color: var(--ink);
}
.padbig{
  font-size: clamp(150px, 16vw, 260px);
  font-weight: 900;
  line-height: 0.9;
  color: var(--ink);
}
.actiontext{
  margin-top: 20px;
  font-size: clamp(40px, 4.2vw, 70px);
  font-weight: 900;
  color: var(--ink);
  line-height: 1.05;
}
.subline{
  margin-top: 10px;
  font-size: clamp(18px, 2.0vw, 30px);
  font-weight: 700;
  color: var(--muted);
}

/* Status stack */
.stack{
  grid-column: 2;
  grid-row: 1;
  display:flex;
  flex-direction:column;
  gap: 12px;
}
.section{
  border: 2px solid var(--line);
  border-radius: 18px;
  overflow:hidden;
  background: var(--card);
}
.section-h{
  padding: 12px 16px;
  font-weight: 950;
  letter-spacing: 0.08em;
  font-size: clamp(18px, 1.6vw, 28px);
  display:flex;
  align-items:center;
  gap: 10px;
}
.dot{
  width: 18px; height: 18px; border-radius: 50%;
  box-shadow: inset 0 2px 4px rgba(0,0,0,0.12);
}
.h-critical{background: var(--critical_bg); color: var(--critical_ink);}
.h-critical .dot{background:#d72626;}
.h-active{background: var(--active_bg); color: var(--active_ink);}
.h-active .dot{background:#f4b400;}
.h-queue{background: var(--queue_bg); color: var(--queue_ink);}
.h-queue .dot{background:#c9ccd3;}

.items{
  padding: 14px;
  display:flex;
  flex-direction:column;
  gap: 12px;
}
.item{
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 14px 14px;
  display:flex;
  align-items:center;
  gap: 14px;
  background:#fff;
}
.pad{
  width: 52px; height: 52px;
  border-radius: 14px;
  border: 1px solid rgba(0,0,0,0.10);
  background: var(--pad_bg);
  display:flex;
  align-items:center;
  justify-content:center;
  font-weight: 900;
  font-size: 24px;
  color: var(--ink);
}
.label{
  font-size: clamp(18px, 1.8vw, 28px);
  font-weight: 800;
  color: var(--muted);
}

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
  font-weight: 800;
  font-size: clamp(16px, 1.6vw, 22px);
}
.footer .k{color:#8a93a3; margin-right:10px; font-weight:900;}
</style>
"""

st.markdown(CSS, unsafe_allow_html=True)

# ----------------------------
# Build HTML (avoid indentation so Streamlit won't render as code blocks)
# ----------------------------
top_html = ""
if alert_msg:
    top_html = f'<div class="topstrip alert"><div class="left">{alert_msg}</div><div class="right">Wind: {wind_ms} m/s</div></div>'
else:
    top_html = f'<div class="topstrip"><div class="left">RPP: 2 mins</div><div class="right">Wind: {wind_ms} m/s</div></div>'

def item(pad_letter: str, label: str) -> str:
    return f'<div class="item"><div class="pad">{pad_letter}</div><div class="label">{label}</div></div>'

# 6 pads shown under QUEUE for the clean canvas
pads = list("ABCDEF")

critical_html = '<div class="section"><div class="section-h h-critical"><span class="dot"></span>CRITICAL</div><div class="items"><div class="label" style="font-weight:800;color:#6b7483;">None</div></div></div>'
active_html = '<div class="section"><div class="section-h h-active"><span class="dot"></span>ACTIVE / LOADING</div><div class="items"><div class="label" style="font-weight:800;color:#6b7483;">None</div></div></div>'

queue_items = "".join(item(p, "Idle") for p in pads)
queue_html = f'<div class="section"><div class="section-h h-queue"><span class="dot"></span>QUEUE</div><div class="items">{queue_items}</div></div>'

primary_html = (
    '<div class="primary">'
      '<div class="kicker">NEXT ACTION</div>'
      '<div class="bigrow"><div class="arrow">→</div><div class="padbig">—</div></div>'
      '<div class="actiontext">All clear</div>'
      '<div class="subline">Waiting for next order</div>'
    '</div>'
)

stack_html = f'<div class="stack">{critical_html}{active_html}{queue_html}</div>'

footer_html = (
    '<div class="footer">'
      '<div><span class="k">At Base</span>--</div>'
      '<div><span class="k">Arriving Soon</span>--</div>'
      '<div><span class="k">Cancelled</span>--</div>'
    '</div>'
)

grid_html = f'<div class="grid">{primary_html}{stack_html}{footer_html}</div>'

st.markdown(top_html + grid_html, unsafe_allow_html=True)
