
import random
import time

import streamlit as st
from textwrap import dedent

st.set_page_config(page_title="Loader Wall Screen - Clean Layout", layout="wide")

# Auto-refresh so the top bar can occasionally show alerts
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=2000, key="blank_layout_tick")
except Exception:
    pass

# Static pads (no simulation)
PADS = ["A", "B", "C", "D", "E", "F"]

CSS = """
<style>
*{box-sizing:border-box;}
.topstrip.alert{background: var(--alert);}
html, body, [data-testid="stAppViewContainer"]{background:#ffffff;}
:root{
  --navy:#1f3f8a;
  --alert:#b51d1d;
  --bg:#ffffff;
  --panel:#fbfcfe;
  --line:#e7ebf2;
  --ink:#0b1320;
  --muted:#667083;
  --soft:#f1f4f9;
}

.main .block-container{
  padding-top:0.6rem;
  padding-bottom:0.6rem;
  max-width: 1600px;
}

/* 16:9-ish wall layout */
.grid{
  height: calc(100vh - 1.2rem);
  display:grid;
  grid-template-rows: 10% 82% 8%;
  gap: 12px;
}

/* Top status strip */
.topstrip{
  background: var(--navy);
  border-radius: 18px;
  padding: 18px 26px;
  display:flex;
  align-items:center;
  justify-content:space-between;
  font-weight:800;
  color:white;
  line-height:1;
  font-size: clamp(18px, 1.7vw, 28px);
}
.topstrip.alert{background: var(--alert);}

/* Main row */
.mainrow{
  display:grid;
  grid-template-columns: 65% 35%;
  gap: 12px;
  min-height: 0;
}

/* Primary action (left) */
.primary{
  background: var(--panel);
  border-radius: 18px;
  border: 2px solid var(--line);
  padding: 38px 42px;
  display:flex;
  flex-direction:column;
  justify-content:center;
  min-height: 0;
}

.kicker{
  font-weight:800;
  color:#a2a9b7;
  letter-spacing: 0.04em;
  font-size: clamp(20px, 2.2vw, 40px);
  margin-bottom: 26px;
}

.bigrow{
  display:flex;
  align-items:center;
  gap: 26px;
  margin: 8px 0 22px 0;
}

.arrow{
  font-weight:800;
  color: var(--ink);
  font-size: clamp(58px, 6vw, 105px);
  line-height:1;
}

.padbig{
  font-weight:800;
  color: var(--ink);
  font-size: clamp(120px, 12vw, 230px);
  line-height:0.9;
}

.actiontext{
  font-weight:800;
  color: var(--ink);
  font-size: clamp(38px, 4.1vw, 78px);
  line-height: 1.05;
  margin-top: 8px;
}

.subline{
  margin-top: 18px;
  font-weight:800;
  color: var(--muted);
  font-size: clamp(16px, 1.8vw, 30px);
}

/* Status stack (right) */
.stack{
  background: var(--panel);
  border-radius: 18px;
  border: 2px solid var(--line);
  overflow:hidden;
  display:flex;
  flex-direction:column;
  min-height:0;
}

.section-h{
  padding: 16px 18px;
  font-weight:800;
  letter-spacing: 0.02em;
  font-size: clamp(16px, 1.55vw, 26px);
  display:flex;
  align-items:center;
  gap: 12px;
  border-bottom: 1px solid var(--line);
}

.h-critical{background:#fdecec; color:#7a1212;}
.h-active{background:#fff8d6; color:#6a5400;}
.h-queue{background:#f1f2f4; color:#3d4552;}

.dot{
  width: 22px;
  height: 22px;
  border-radius: 999px;
  background: rgba(0,0,0,0.18);
}

.items{
  padding: 14px 16px;
  display:flex;
  flex-direction:column;
  gap: 10px;
}

.item{
  border: 1px solid var(--line);
  background:white;
  border-radius: 14px;
  padding: 12px 14px;
  display:flex;
  align-items:center;
  justify-content:space-between;
}

.item-left{
  display:flex;
  align-items:center;
  gap: 12px;
}

.badge{
  width: 46px;
  height: 46px;
  border-radius: 12px;
  border: 1px solid var(--line);
  display:flex;
  align-items:center;
  justify-content:center;
  font-weight:800;
  color: var(--ink);
  font-size: 20px;
}

.label{
  font-weight:800;
  color: var(--muted);
  font-size: clamp(18px, 1.7vw, 26px);
}

/* Footer */
.footer{
  background: var(--panel);
  border-radius: 18px;
  border: 2px solid var(--line);
  padding: 14px 26px;
  display:flex;
  align-items:center;
  justify-content:space-between;
  font-weight:800;
  color: var(--muted);
  font-size: clamp(16px, 1.6vw, 24px);
}

.footer span{color:#8a93a3; margin-right:10px;}
</style>
"""

st.markdown(CSS, unsafe_allow_html=True)

# Build HTML with NO leading indentation (avoid Markdown code blocks)
top_html = (
    f'<div class="topstrip alert"><div>{alert_msg}</div><div>Wind: {wind_ms} m/s</div></div>'
    if alert_msg else
    f'<div class="topstrip"><div>RPP: 2 mins</div><div>Wind: {wind_ms} m/s</div></div>'
)

primary_html = (
    '<div class="primary">'
    '<div class="kicker">NEXT ACTION</div>'
    '<div class="bigrow"><div class="arrow">→</div><div class="padbig">—</div></div>'
    '<div class="actiontext">All clear</div>'
    '<div class="subline">Waiting for next order</div>'
    '</div>'
)

def item(pad: str, label: str) -> str:
    return (
        '<div class="item">'
        f'<div class="item-left"><div class="badge">{pad}</div><div class="label">{label}</div></div>'
        '</div>'
    )

# Static sections (no orders). Keep it visually like the final wall.
critical_items = '<div class="label">None</div>'
active_items = '<div class="label">None</div>'
queue_items = ''.join(item(p, "Idle") for p in PADS)

stack_html = (
    '<div class="stack">'
    '<div class="section-h h-critical"><div class="dot"></div>CRITICAL</div>'
    f'<div class="items">{critical_items}</div>'
    '<div class="section-h h-active"><div class="dot"></div>ACTIVE / LOADING</div>'
    f'<div class="items">{active_items}</div>'
    '<div class="section-h h-queue"><div class="dot"></div>QUEUE</div>'
    f'<div class="items">{queue_items}</div>'
    '</div>'
)

footer_html = (
    '<div class="footer">'
    '<div><span>At Base</span>--</div>'
    '<div><span>Arriving Soon</span>--</div>'
    '<div><span>Cancelled</span>--</div>'
    '</div>'
)

page = (
    '<div class="grid">'
    f'{top_html}'
    '<div class="mainrow">'
    f'{primary_html}'
    f'{stack_html}'
    '</div>'
    f'{footer_html}'
    '</div>'
)

st.markdown(page, unsafe_allow_html=True)
