import random
import time
import streamlit as st

st.set_page_config(page_title="Loader Wall Screen (Blank Layout)", layout="wide")

# ----------------------------
# Top bar alert config
# ----------------------------
ALERTS = [
    "Heavy rain — wipe lidar",
    "Space weather over limits",
    "Icing pre flight checklist",
    "Weather above limits — put everything in the heat",
    "Containment breach grounding",
]
ALERT_CHANCE = 0.05          # 5%
TOPBAR_ROTATE_SECONDS = 6    # how often we re-roll

# ----------------------------
# Session state
# ----------------------------
def _init_state():
    seed = int(time.time() * 1000) % 2_000_000_000
    rng = random.Random(seed)
    return {
        "rng": rng,
        "next_roll": time.time(),
        "topbar_mode": "normal",  # "normal" | "alert"
        "topbar_alert": "",
        "wind": rng.randint(5, 10),
        "rpp": "2 mins",
    }

if "blank_state" not in st.session_state:
    st.session_state["blank_state"] = _init_state()

S = st.session_state["blank_state"]
rng: random.Random = S["rng"]

# Autorefresh (safe fallback if not installed)
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=1000, key="blank_tick")
except Exception:
    pass

# Roll top bar state every TOPBAR_ROTATE_SECONDS
now = time.time()
if now >= S["next_roll"]:
    S["next_roll"] = now + TOPBAR_ROTATE_SECONDS

    # wind always updates when we roll
    S["wind"] = rng.randint(5, 10)

    if rng.random() < ALERT_CHANCE:
        S["topbar_mode"] = "alert"
        S["topbar_alert"] = rng.choice(ALERTS)
    else:
        S["topbar_mode"] = "normal"
        S["topbar_alert"] = ""

# ----------------------------
# Styling
# ----------------------------
CSS = """
<style>
:root{
  --bg:#ffffff;
  --ink:#0b1320;
  --muted:#6b7483;
  --line:#e8ebf0;

  --navy:#1f3f8a;
  --danger:#b51d1d;

  --card:#ffffff;
  --soft:#f8fafc;

  --critical_bg:#fbe3e3;
  --critical_ink:#7a1212;

  --active_bg:#fff7cf;
  --active_ink:#6a5400;

  --queue_bg:#f4f5f7;
  --queue_ink:#3b4350;
}

html, body { background: var(--bg); }
.main .block-container{
  padding-top: 1rem;
  padding-bottom: 1rem;
  max-width: 1600px;
}

.topstrip{
  border-radius: 18px;
  padding: 18px 22px;
  background: var(--navy);
  color: white;
  display:flex;
  align-items:center;
  justify-content:space-between;
  margin-bottom: 14px;
}

.topstrip.alert{
  background: var(--danger);
  justify-content:center;
  text-align:center;
}

.top-left, .top-right{
  font-size: 38px;
  font-weight: 900;
  letter-spacing: 0.3px;
  line-height: 1;
}

.top-center{
  font-size: 40px;
  font-weight: 950;
  letter-spacing: 0.5px;
  line-height: 1;
}

.shell{
  display:flex;
  gap: 14px;
  align-items: stretch;
  height: calc(100vh - 150px);
  min-height: 520px;
}

.left{
  flex: 0 0 65%;
  border: 2px solid var(--line);
  border-radius: 18px;
  background: var(--soft);
  display:flex;
  flex-direction:column;
  justify-content:flex-end;
  padding: 36px;
  position: relative;
}

.left-title{
  position:absolute;
  top: 40px;
  left: 36px;
  font-size: 44px;
  font-weight: 900;
  letter-spacing: 2px;
  color: #a0a8b5;
}

.left-big{
  font-size: 90px;
  font-weight: 1000;
  color: var(--ink);
  margin: 0;
}

.left-sub{
  font-size: 40px;
  font-weight: 900;
  color: var(--muted);
  margin-top: 10px;
}

.right{
  flex: 0 0 35%;
  display:flex;
  flex-direction:column;
  gap: 12px;
  border: 2px solid var(--line);
  border-radius: 18px;
  background: #fff;
  overflow: hidden;
}

.section{
  border-bottom: 1px solid var(--line);
}
.section:last-child{
  border-bottom: 0;
}

.section-h{
  padding: 18px 18px;
  font-size: 38px;
  font-weight: 1000;
  display:flex;
  align-items:center;
  gap: 14px;
}

.dot{
  width: 28px;
  height: 28px;
  border-radius: 999px;
  background: #c8c8c8;
  box-shadow: inset 0 2px 3px rgba(255,255,255,0.7);
}

.h-critical{ background: var(--critical_bg); color: var(--critical_ink); }
.h-critical .dot{ background: #d53a3a; }

.h-active{ background: var(--active_bg); color: var(--active_ink); }
.h-active .dot{ background: #f3c300; }

.h-queue{ background: var(--queue_bg); color: var(--queue_ink); }
.h-queue .dot{ background: #d1d4d9; }

.items{
  padding: 14px 14px 18px 14px;
  display:flex;
  flex-direction:column;
  gap: 12px;
}

.item{
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 16px 18px;
  display:flex;
  align-items:center;
  gap: 16px;
  background: #fff;
}

.badge{
  width: 54px;
  height: 54px;
  border-radius: 14px;
  border: 1px solid var(--line);
  display:flex;
  align-items:center;
  justify-content:center;
  font-size: 26px;
  font-weight: 1000;
  color: var(--ink);
  background: #fff;
}

.item-text{
  font-size: 34px;
  font-weight: 950;
  color: var(--muted);
}

.footer{
  margin-top: 14px;
  border: 2px solid var(--line);
  border-radius: 18px;
  background: #fff;
  padding: 14px 18px;
  display:flex;
  justify-content:space-between;
  align-items:center;
  font-size: 28px;
  font-weight: 950;
  color: #5b6472;
}

.footer .k{
  color: #8a93a1;
  margin-right: 10px;
}
</style>
"""

st.markdown(CSS, unsafe_allow_html=True)

# ----------------------------
# Top bar render
# ----------------------------
if S["topbar_mode"] == "alert":
    st.markdown(
        f'<div class="topstrip alert"><div class="top-center">{S["topbar_alert"]}</div></div>',
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        f'''
        <div class="topstrip">
          <div class="top-left">RPP: {S["rpp"]}</div>
          <div class="top-right">Wind: {S["wind"]} m/s</div>
        </div>
        ''',
        unsafe_allow_html=True,
    )

# ----------------------------
# Blank canvas body (6 pads, no motion)
# ----------------------------
pads = list("ABCDEF")

right_html = f"""
<div class="right">
  <div class="section">
    <div class="section-h h-critical"><div class="dot"></div>CRITICAL</div>
    <div class="items">
      <div class="item"><div class="item-text">None</div></div>
    </div>
  </div>

  <div class="section">
    <div class="section-h h-active"><div class="dot"></div>ACTIVE / LOADING</div>
    <div class="items">
      <div class="item"><div class="item-text">None</div></div>
    </div>
  </div>

  <div class="section">
    <div class="section-h h-queue"><div class="dot"></div>QUEUE</div>
    <div class="items">
      {''.join(f'<div class="item"><div class="badge">{p}</div><div class="item-text">Idle</div></div>' for p in pads)}
    </div>
  </div>
</div>
"""

left_html = """
<div class="left">
  <div class="left-title">NEXT ACTION</div>
  <div>
    <div class="left-big">All clear</div>
    <div class="left-sub">Waiting for next order</div>
  </div>
</div>
"""

st.markdown(f'<div class="shell">{left_html}{right_html}</div>', unsafe_allow_html=True)

# Footer (blank metrics)
st.markdown(
    """
    <div class="footer">
      <div><span class="k">At Base</span>--</div>
      <div><span class="k">Arriving Soon</span>--</div>
      <div><span class="k">Cancelled</span>--</div>
    </div>
    """,
    unsafe_allow_html=True,
)
