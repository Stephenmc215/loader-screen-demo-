
import streamlit as st

st.set_page_config(page_title="Loader Wall Screen - Clean Layout", layout="wide")

PADS = ["A", "B", "C", "D", "E", "F"]

CSS = """
<style>
*{box-sizing:border-box;}

:root{
  --navy:#1f3f8a;
  --bg:#ffffff;
  --card:#f8f9fb;
  --line:#e6e9ef;
  --ink:#0b1320;
  --muted:#5b6472;
}

.main .block-container{
  padding-top:0.5rem;
  padding-bottom:0.5rem;
  max-width:1800px;
}

.grid{
  height: calc(100vh - 1rem);
  display:grid;
  grid-template-rows: 10fr 82fr 8fr;
  gap: 10px;
}

.topstrip{
  background: var(--navy);
  border-radius: 18px;
  padding: 0 24px;
  display:flex;
  align-items:center;
  justify-content:space-between;
  font-weight:1000;
  color:white;
  font-size: clamp(18px, 2vw, 36px);
}

.mainrow{
  display:grid;
  grid-template-columns: 65% 35%;
  gap: 10px;
}

.primary{
  background: var(--card);
  border-radius: 18px;
  border: 2px solid var(--line);
  display:flex;
  align-items:center;
  justify-content:center;
  color: var(--muted);
  font-weight:1000;
  font-size: clamp(28px, 4vw, 60px);
}

.statuswrap{
  background: var(--card);
  border-radius: 18px;
  border: 2px solid var(--line);
  padding: 20px;
  display:flex;
  flex-direction:column;
  gap: 16px;
}

.pad{
  display:flex;
  align-items:center;
  justify-content:space-between;
  padding: 16px 20px;
  border-radius: 14px;
  border: 1px solid var(--line);
  background: white;
}

.pad-left{
  display:flex;
  align-items:center;
  gap: 16px;
}

.pad-letter{
  width: 48px;
  height: 48px;
  border-radius: 12px;
  border: 1px solid var(--line);
  display:flex;
  align-items:center;
  justify-content:center;
  font-weight:1000;
  font-size: 24px;
  color: var(--ink);
}

.pad-state{
  font-size: 20px;
  font-weight:1000;
  color: var(--muted);
}

.footer{
  background: var(--card);
  border-radius: 18px;
  border: 2px solid var(--line);
  display:flex;
  align-items:center;
  justify-content:space-between;
  padding: 0 24px;
  font-weight:1000;
  color: var(--muted);
  font-size: clamp(16px, 1.8vw, 24px);
}
</style>
"""

st.markdown(CSS, unsafe_allow_html=True)

top = """
<div class="topstrip">
  <div>RPP: --</div>
  <div>Wind: --</div>
</div>
"""

primary = """
<div class="primary">
  NEXT ACTION AREA
</div>
"""

status_items = ""
for pad in PADS:
    status_items += f"""
    <div class="pad">
        <div class="pad-left">
            <div class="pad-letter">{pad}</div>
            <div class="pad-state">Idle</div>
        </div>
    </div>
    """

status = f"""
<div class="statuswrap">
  {status_items}
</div>
"""

footer = """
<div class="footer">
  <div>At Base --</div>
  <div>Arriving Soon --</div>
  <div>Cancelled --</div>
</div>
"""

st.markdown(f"""
<div class="grid">
  {top}
  <div class="mainrow">
    {primary}
    {status}
  </div>
  {footer}
</div>
""", unsafe_allow_html=True)
