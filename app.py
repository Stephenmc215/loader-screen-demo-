import streamlit as st
import random
import time

st.set_page_config(layout="wide")

# -------------------------
# CONFIG
# -------------------------

PADS = ["A", "B", "C", "D", "E", "F"]

TOP_ALERTS = [
    "Heavy rain - wipe lidar",
    "Space weather over limits",
    "Icing pre flight checklist",
    "Weather above limits. Put everything in the heat.",
    "Containment Breach Grounding"
]

# -------------------------
# TOP BAR LOGIC (5% alert)
# -------------------------

if "alert_timer" not in st.session_state:
    st.session_state.alert_timer = 0
    st.session_state.current_alert = None

if st.session_state.alert_timer <= 0:
    if random.random() < 0.05:
        st.session_state.current_alert = random.choice(TOP_ALERTS)
        st.session_state.alert_timer = 8
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

        orders.append({
            "pad": pad,
            "state": state,
            "time": random.randint(5, 40),
            "id": random.randint(100, 999),
            "critical": random.random() < 0.1
        })
    return orders

orders = generate_orders()

critical = [o for o in orders if o["critical"]]
attention = [o for o in orders if o["state"] == "ATTENTION" and not o["critical"]]
load = [o for o in orders if o["state"] == "LOAD" and not o["critical"]]

# Primary = first load, else attention, else none
primary = load[0] if load else (attention[0] if attention else None)

# -------------------------
# STYLING
# -------------------------

st.markdown("""
<style>
body {
    background-color: #f4f6f9;
    font-family: -apple-system, BlinkMacSystemFont, sans-serif;
}
.topbar {
    background: #2f4a8a;
    color: white;
    padding: 18px 40px;
    border-radius: 16px;
    font-size: 24px;
    font-weight: 600;
    display:flex;
    justify-content:space-between;
}
.alertbar {
    background:#b91c1c;
}
.section {
    background:white;
    padding:20px;
    border-radius:16px;
    margin-bottom:20px;
}
.section-title {
    font-weight:600;
    font-size:22px;
    margin-bottom:12px;
}
.row {
    padding:14px 18px;
    border-radius:12px;
    background:#f3f4f6;
    margin-bottom:10px;
    display:flex;
    justify-content:space-between;
    font-size:20px;
}
.primary-area {
    background:white;
    padding:60px;
    border-radius:20px;
    height:600px;
}
.pad-letter {
    font-size:180px;
    font-weight:700;
    margin-bottom:10px;
}
.primary-title {
    font-size:42px;
    font-weight:600;
}
.primary-sub {
    font-size:22px;
    color:#6b7280;
}
</style>
""", unsafe_allow_html=True)

# -------------------------
# TOP BAR
# -------------------------

if st.session_state.current_alert:
    st.markdown(
        f'<div class="topbar alertbar">{st.session_state.current_alert}</div>',
        unsafe_allow_html=True
    )
else:
    wind = random.randint(5, 10)
    st.markdown(
        f'<div class="topbar"><div>RPP: 2 mins</div><div>Wind: {wind} m/s</div></div>',
        unsafe_allow_html=True
    )

st.markdown("<br>", unsafe_allow_html=True)

# -------------------------
# LAYOUT
# -------------------------

left, right = st.columns([2, 1])

# -------------------------
# LEFT – PRIMARY
# -------------------------

with left:
    st.markdown('<div class="primary-area">', unsafe_allow_html=True)

    if primary:
        st.markdown(
            f'<div class="pad-letter">{primary["pad"]}</div>',
            unsafe_allow_html=True
        )
        st.markdown(
            f'<div class="primary-title">Load Order</div>',
            unsafe_allow_html=True
        )
        st.markdown(
            f'<div class="primary-sub">🔥 {primary["id"]} • {primary["time"]}s</div>',
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            '<div class="primary-title">All clear</div>',
            unsafe_allow_html=True
        )
        st.markdown(
            '<div class="primary-sub">Waiting for next order</div>',
            unsafe_allow_html=True
        )

    st.markdown('</div>', unsafe_allow_html=True)

# -------------------------
# RIGHT – STATUS STACK
# -------------------------

with right:

    if critical:
        st.markdown('<div class="section">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">🔴 CRITICAL</div>', unsafe_allow_html=True)
        for o in critical[:3]:
            st.markdown(
                f'<div class="row">{o["pad"]} • Order {o["id"]}</div>',
                unsafe_allow_html=True
            )
        st.markdown('</div>', unsafe_allow_html=True)

    if attention:
        st.markdown('<div class="section">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">🟡 REQUIRES ATTENTION</div>', unsafe_allow_html=True)
        for o in attention[:3]:
            st.markdown(
                f'<div class="row">{o["pad"]} • {o["time"]}s</div>',
                unsafe_allow_html=True
            )
        st.markdown('</div>', unsafe_allow_html=True)

    if load:
        st.markdown('<div class="section">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">LOAD</div>', unsafe_allow_html=True)
        for o in load[:3]:
            st.markdown(
                f'<div class="row">{o["pad"]} • {o["time"]}s</div>',
                unsafe_allow_html=True
            )
        st.markdown('</div>', unsafe_allow_html=True)

# -------------------------
# REFRESH LOOP
# -------------------------

time.sleep(2)
st.experimental_rerun()
