import random
from dataclasses import dataclass
import streamlit as st
from streamlit_autorefresh import st_autorefresh
import streamlit.components.v1 as components

st.set_page_config(page_title="Loader Screen Demo", layout="wide")

st.markdown("""
<style>
.block-container { padding: 0.35rem 0.8rem !important; max-width: 100% !important; }
.banner { border-radius: 18px; padding: 20px; text-align:center; color:white; font-weight:900; font-size:50px; margin-bottom:18px; }
.metrics-col { padding-top: 8px; }
.metric-label { font-size: 18px; color:#111827; margin-top: 28px; }
.metric-value { font-size: 58px; font-weight: 900; line-height: 1.0; color:#111827; }
.grid-wrap { border: 1px solid #e5e7eb; border-radius: 14px; overflow: hidden; background: white; }
table.grid { width: 100%; border-collapse: collapse; table-layout: fixed; }
table.grid th { text-align: left; font-size: 26px; padding: 16px; border-bottom: 1px solid #e5e7eb; background: #f9fafb; color: #6b7280; font-weight: 700; }
table.grid td { font-size: 34px; padding: 18px; border-bottom: 1px solid #eef2f7; color: #111827; }
.col-pad { width: 14%; }
.col-order { width: 22%; }
.col-rt { width: 22%; }
.col-action { width: 42%; }
.act-blue { background: #dbeafe; font-weight:900; }
.act-yellow { background: #fde68a; font-weight:900; }
.act-orange { background: #fdba74; font-weight:900; }
.act-red { background: #f87171; color:white; font-weight:900; }
.rt-warning { background:#fdba74; font-weight:900; padding:6px 10px; border-radius:8px; display:inline-block; }
</style>
""", unsafe_allow_html=True)

TICK_SECONDS = 2
st_autorefresh(interval=TICK_SECONDS * 1000, key="loader_refresh")

@dataclass
class Pad:
    pad: str
    order: int
    phase: str
    t: int
    action: str
    fault: bool

FLIGHT_MIN = 120
FLIGHT_MAX = 300
LANDING = 10
LOADING = 60
FIXING = 30

ISSUES = ["Repress Pad", "Change Cassette", "Reboot Drone", "Change Drone"]

def next_order(n): return 100 if n+3>999 else n+3
def rand_flight(): return random.randint(FLIGHT_MIN, FLIGHT_MAX)

def init_pads():
    pads=[]; o=100
    for i in range(8):
        pads.append(Pad(chr(65+i), o, "FLIGHT", random.randint(20,rand_flight()), "", False))
        o=next_order(o)
    return pads

if "pads" not in st.session_state:
    st.session_state.pads = init_pads()
    random.seed(42)

pads = st.session_state.pads

for p in pads:
    p.t=max(0,p.t-TICK_SECONDS)

    if p.phase=="FLIGHT" and p.t==0:
        p.phase="LANDING"; p.t=LANDING; p.action=""; p.fault=False
    elif p.phase=="LANDING" and p.t==0:
        p.phase="LOADING"; p.t=LOADING; p.action=str(next_order(p.order)); p.fault=False
    elif p.phase=="LOADING":
        if not p.fault and random.random()<0.04:
            p.fault=True; p.phase="FIXING"; p.t=FIXING; p.action=random.choice(ISSUES)
        if p.t==0 and not p.fault:
            p.phase="FLIGHT"; p.order=next_order(p.order); p.t=rand_flight(); p.action=""
    elif p.phase=="FIXING" and p.t==0:
        p.phase="FLIGHT"; p.order=next_order(p.order); p.t=rand_flight(); p.action=""; p.fault=False

def severity(a):
    return {"Repress Pad":1,"Change Cassette":2,"Reboot Drone":3,"Change Drone":4}.get(a,0)

best=None
for p in pads:
    sev=severity(p.action)
    if best is None or sev>best["sev"]:
        best={"sev":sev,"pad":p.pad,"action":p.action}

if best and best["sev"]>=4:
    banner_text=f"CRITICAL: {best['action']} (Pad {best['pad']})"; banner_bg="#b91c1c"
elif best and best["sev"]==3:
    banner_text=f"HIGH: {best['action']} (Pad {best['pad']})"; banner_bg="#b45309"
else:
    banner_text="RPP: 2 mins"; banner_bg="#1f3a8a"

st.markdown(f"<div class='banner' style='background:{banner_bg};'>{banner_text}</div>", unsafe_allow_html=True)

left,right=st.columns([1,4],gap="large")

with left:
    at_base=sum(1 for p in pads if p.phase in ("LANDING","LOADING","FIXING"))
    arriving=sum(1 for p in pads if p.phase=="FLIGHT")
    st.markdown("<div class='metrics-col'>", unsafe_allow_html=True)
    st.markdown("<div class='metric-label'>At Base</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='metric-value'>{at_base}</div>", unsafe_allow_html=True)
    st.markdown("<div class='metric-label'>Arriving Soon</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='metric-value'>{arriving}</div>", unsafe_allow_html=True)
    st.markdown("<div class='metric-label'>Cancelled</div>", unsafe_allow_html=True)
    st.markdown("<div class='metric-value'>0</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

def action_class(a):
    return {"Repress Pad":"act-blue","Change Cassette":"act-yellow","Reboot Drone":"act-orange","Change Drone":"act-red"}.get(a,"")

rows=[]
for p in pads:
    if p.phase in ("LANDING","LOADING","FIXING"):
        rt=""
    else:
        rt=f"<span class='rt-warning'>{p.t}</span>" if p.t<=10 else str(p.t)
    rows.append(f"<tr><td>{p.pad}</td><td>{p.order}</td><td>{rt}</td><td class='{action_class(p.action)}'>{p.action}</td></tr>")

table_html=f"""
<div class="grid-wrap">
<table class="grid">
<thead><tr><th class="col-pad">Pad</th><th class="col-order">Order</th><th class="col-rt">RT (s)</th><th class="col-action">Next Action</th></tr></thead>
<tbody>{''.join(rows)}</tbody>
</table></div>
"""

components.html(table_html, height=820, scrolling=False)
