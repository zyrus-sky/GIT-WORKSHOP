# streamlit_github_workshop_dashboard.py
# A polished Streamlit app to showcase a GitHub/Git workshop event:
# - image gallery with smooth CSS animations
# - attendance uploader / editor / export
# - feedback form and analytics (rating distribution, keyword frequency)
# - animated KPI cards and smooth transitions
#
# Requirements:
# pip install streamlit pandas plotly pillow
# Optional: pip install python-magic if you want advanced file checks
#
# Run with: streamlit run streamlit_github_workshop_dashboard.py

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from PIL import Image
import io
import base64
from datetime import datetime
from collections import Counter
import textwrap

st.set_page_config(page_title="Git/GitHub Workshop Dashboard", layout="wide")

# ---------------------------
# Helper utilities
# ---------------------------

def to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode('utf-8')


def download_link_bytes(content: bytes, filename: str, label: str):
    b64 = base64.b64encode(content).decode()
    href = f"data:application/octet-stream;base64,{b64}"
    return f"<a href=\"{href}\" download=\"{filename}\">{label}</a>"


def make_kpi_card(title, value, delta=None, unit=""):
    delta_html = f"<div class=\"kpi-delta\">{delta}</div>" if delta is not None else ""
    return f"""
    <div class="kpi-card">
      <div class="kpi-title">{title}</div>
      <div class="kpi-value">{value}{unit}</div>
      {delta_html}
    </div>
    """


# ---------------------------
# Persistent session state structures
# ---------------------------
if 'attendance_df' not in st.session_state:
    # sample schema if not provided
    st.session_state.attendance_df = pd.DataFrame(columns=["Name","Email","Registered At","Attended","Department"]) 

if 'images' not in st.session_state:
    st.session_state.images = []  # list of dicts {name, image_bytes}

if 'feedback' not in st.session_state:
    st.session_state.feedback = pd.DataFrame(columns=["Name","Rating","Comments","Submitted At"]) 

# ---------------------------
# CSS + JS for animations and design
# ---------------------------
ANIM_CSS = """
<style>
:root{
  --accent: #ff6a00;
  --bg: #0f1720;
  --card-bg: linear-gradient(135deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01));
}
/* page resets */
.block-widget {
  transition: all 400ms cubic-bezier(.2,.8,.2,1);
}

.kpi-row{display:flex;gap:18px;align-items:stretch}
.kpi-card{
  background: var(--card-bg);
  padding:18px;border-radius:12px;box-shadow:0 6px 18px rgba(0,0,0,0.45);
  min-width:170px;flex:1;color:#fff;backdrop-filter: blur(6px);
  transition: transform .35s cubic-bezier(.2,.8,.2,1), box-shadow .35s;
}
.kpi-card:hover{transform: translateY(-6px) scale(1.02);box-shadow:0 20px 40px rgba(0,0,0,0.6)}
.kpi-title{font-size:13px;opacity:0.85}
.kpi-value{font-size:28px;font-weight:700;margin-top:6px}
.kpi-delta{font-size:12px;color:var(--accent);margin-top:8px}

/* hero */
.hero{display:flex;gap:18px;align-items:center}
.hero-left{flex:1}
.hero-right{flex:1}
.hero-card{background:linear-gradient(90deg, rgba(255,106,0,0.08), rgba(255,106,0,0.02)); padding:22px;border-radius:14px;color:#fff}

/* gallery */
.gallery{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:12px}
.gallery-item{border-radius:10px;overflow:hidden;position:relative;box-shadow: 0 8px 30px rgba(2,6,23,0.6);transition: transform .35s, box-shadow .35s}
.gallery-item:hover{transform: translateY(-10px) scale(1.03);box-shadow:0 30px 60px rgba(2,6,23,0.75)}
.gallery-item img{width:100%;height:180px;object-fit:cover;display:block}
.gallery-caption{position:absolute;left:10px;bottom:10px;background:rgba(0,0,0,0.45);padding:6px 10px;border-radius:8px;font-size:12px}

/* smooth inputs */
.stButton>button{border-radius:10px;padding:8px 12px}

/* dark mode compatibility */
[data-testid='stSidebar']{background:linear-gradient(180deg,#07101a, #061018)}

/* animated count-up */
.countup{font-size:32px;font-weight:800}

/* feedback cards */
.feedback-card{background:rgba(255,255,255,0.02);padding:12px;border-radius:10px}

/* responsive tweaks */
@media (max-width: 800px){
  .hero{flex-direction:column}
}
</style>
"""

COUNTUP_JS = """
<script>
function countUp(elId, endVal, duration){
  const el = document.getElementById(elId);
  if(!el) return;
  const start = 0; const range = endVal - start;
  const minTimer = 50; const stepTime = Math.max(Math.floor(duration / endVal), minTimer);
  let current = start;
  const timer = setInterval(()=>{
    current += Math.ceil(range * (stepTime/duration));
    if(current >= endVal){ current = endVal; clearInterval(timer); }
    el.innerText = current;
  }, stepTime);
}
</script>
"""

# ---------------------------
# Top: header / hero
# ---------------------------
st.markdown(ANIM_CSS, unsafe_allow_html=True)
st.markdown(COUNTUP_JS, unsafe_allow_html=True)

with st.container():
    col1, col2 = st.columns([2,1])
    with col1:
        st.markdown("<div class='hero-left'>", unsafe_allow_html=True)
        st.markdown("""
        <div class='hero-card'>
          <div style='display:flex;justify-content:space-between;align-items:center'>
            <div>
              <div style='font-size:22px;font-weight:800;color:white'>Git & GitHub Workshop — Dashboard</div>
              <div style='opacity:0.8;margin-top:6px'>Visualize attendance, feedback, images and more with a sleek UI.</div>
            </div>
            <div style='text-align:right'>
              <div style='font-size:12px;opacity:0.75'>Event dates</div>
              <div style='font-weight:700'>March 15–16, 2024</div>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with col2:
        st.markdown(make_kpi_card("Live Mode","Demo"), unsafe_allow_html=True)

st.markdown("---")

# ---------------------------
# Sidebar: data inputs, uploads
# ---------------------------
with st.sidebar:
    st.header("Data & Uploads")
    st.markdown("Upload an attendance CSV (columns: Name, Email, Registered At, Department, Attended)")
    att_upload = st.file_uploader("Attendance CSV", type=['csv'], key='att_up')

    st.markdown("Upload event images (multiple allowed)")
    imgs = st.file_uploader("Event images", type=['png','jpg','jpeg'], accept_multiple_files=True)

    st.markdown("Feedback import/export")
    fb_upload = st.file_uploader("Feedback CSV", type=['csv'])

    if st.button("Ingest uploads"):
        if att_upload is not None:
            df = pd.read_csv(att_upload)
            # quick normalization
            if 'Attended' in df.columns:
                df['Attended'] = df['Attended'].astype(bool)
            st.session_state.attendance_df = df
            st.success("Loaded attendance ({} rows)".format(len(df)))
        if imgs:
            for f in imgs:
                name = f.name
                img_bytes = f.read()
                st.session_state.images.append({'name':name,'bytes':img_bytes})
            st.success(f"Loaded {len(imgs)} images")
        if fb_upload is not None:
            fbdf = pd.read_csv(fb_upload)
            st.session_state.feedback = pd.concat([st.session_state.feedback, fbdf], ignore_index=True)
            st.success("Loaded feedback")

    st.markdown("---")
    st.markdown("Export data")
    if st.button("Download attendance CSV"):
        csvb = to_csv_bytes(st.session_state.attendance_df)
        st.markdown(download_link_bytes(csvb, 'attendance_export.csv', 'Click to download attendance CSV'), unsafe_allow_html=True)
    if st.button("Download feedback CSV"):
        fb = to_csv_bytes(st.session_state.feedback)
        st.markdown(download_link_bytes(fb, 'feedback_export.csv', 'Click to download feedback CSV'), unsafe_allow_html=True)

# ---------------------------
# Main KPIs
# ---------------------------
with st.container():
    d = st.session_state.attendance_df
    total_registered = int(len(d))
    total_attended = int(d['Attended'].sum()) if 'Attended' in d.columns and len(d)>0 else 0
    attendance_rate = f"{(total_attended/total_registered*100):.1f}%" if total_registered>0 else "0%"

    kpi_html = "<div class='kpi-row'>"
    kpi_html += make_kpi_card("Registered", f"<span id='k_reg'>0</span>", delta=None)
    kpi_html += make_kpi_card("Attended", f"<span id='k_att'>0</span>", delta=None)
    kpi_html += make_kpi_card("Attendance Rate", attendance_rate, delta=None)
    kpi_html += "</div>"
    st.markdown(kpi_html, unsafe_allow_html=True)
    # trigger JS countup
    st.components.v1.html(f"<script>countUp('k_reg',{total_registered},800);countUp('k_att',{total_attended},800);</script>", height=0)

# ---------------------------
# Two-column layout: Attendance table + Analytics
# ---------------------------
left, right = st.columns([2,3])

with left:
    st.subheader("Attendance & Roster")
    st.markdown("Use the table below to review and toggle attendance. Edits persist in this session.")

    if len(st.session_state.attendance_df)==0:
        st.info("No attendance loaded. You can upload a CSV in the sidebar or click 'Create sample data'.")
        if st.button("Create sample data"):
            sample = pd.DataFrame({
                'Name': ['Aisha Patel','Rohit Sharma','Kavya Nair','Arjun Menon','Leena Thomas'],
                'Email': ['aisha@uni.edu','rohit@uni.edu','kavya@uni.edu','arjun@uni.edu','leena@uni.edu'],
                'Registered At': [
                    '2024-03-01 10:10','2024-03-02 11:20','2024-03-03 09:15','2024-03-03 13:40','2024-03-04 08:50'
                ],
                'Department':['CSE','ECE','CSE','ME','CSE'],
                'Attended':[True,False,True,True,False]
            })
            st.session_state.attendance_df = sample
            st.experimental_rerun()

    else:
        df = st.session_state.attendance_df.copy()
        # Display an editable table using checkboxes for attendance
        for i,row in df.iterrows():
            cols = st.columns([3,4,2,1])
            with cols[0]:
                st.markdown(f"**{row.get('Name','-')}**")
            with cols[1]:
                st.markdown(row.get('Email','-'))
            with cols[2]:
                st.markdown(row.get('Department','-'))
            with cols[3]:
                key = f"att_{i}"
                newval = st.checkbox("Present", value=bool(row.get('Attended',False)), key=key)
                st.session_state.attendance_df.at[i,'Attended'] = newval
        st.markdown("---")
        if st.button("Export attendance CSV (current)"):
            b = to_csv_bytes(st.session_state.attendance_df)
            st.markdown(download_link_bytes(b,'attendance_current.csv','Click to download current attendance CSV'), unsafe_allow_html=True)

with right:
    st.subheader("Event Images")
    st.markdown("Smooth animated gallery — upload images from the sidebar to populate.")
    if len(st.session_state.images)==0:
        st.info("No images uploaded yet. Upload images via the sidebar 'Event images' uploader or press 'Use placeholder images'.")
        if st.button("Use placeholder images"):
            # create simple placeholders
            for i in range(6):
                img = Image.new('RGB',(800,480), color=(int(20+30*i), int(40+20*i), int(50+10*i)))
                buf = io.BytesIO(); img.save(buf,'JPEG'); buf.seek(0)
                st.session_state.images.append({'name':f'placeholder_{i}.jpg','bytes':buf.getvalue()})
            st.experimental_rerun()
    else:
        # render gallery with HTML/CSS grid
        gallery_html = "<div class='gallery'>"
        for img_obj in st.session_state.images:
            b64 = base64.b64encode(img_obj['bytes']).decode()
            name = img_obj['name']
            gallery_html += f"<div class='gallery-item'><img src=\"data:image/jpeg;base64,{b64}\" alt=\"{name}\" /><div class='gallery-caption'>{name}</div></div>"
        gallery_html += "</div>"
        st.markdown(gallery_html, unsafe_allow_html=True)

# ---------------------------
# Feedback section
# ---------------------------
st.markdown("---")
colf1, colf2 = st.columns([2,3])
with colf1:
    st.subheader("Collect feedback")
    with st.form("feedback_form", clear_on_submit=True):
        fname = st.text_input("Name")
        rating = st.slider("Rating (1-5)", 1,5,4)
        comments = st.text_area("Comments (short)")
        submitted = st.form_submit_button("Submit feedback")
        if submitted:
            new = {'Name': fname or 'Anonymous', 'Rating': rating, 'Comments': comments or '', 'Submitted At': datetime.utcnow().isoformat()}
            st.session_state.feedback = pd.concat([st.session_state.feedback, pd.DataFrame([new])], ignore_index=True)
            st.success("Thanks for the feedback!")

with colf2:
    st.subheader("Feedback analytics")
    fb = st.session_state.feedback
    if len(fb)==0:
        st.info("No feedback yet — encourage attendees to submit!")
    else:
        fig = px.histogram(fb, x='Rating', nbins=5, range_x=[0.5,5.5], text_auto=True)
        fig.update_layout(yaxis_title='Count', xaxis_title='Rating', template='plotly_dark')
        st.plotly_chart(fig, use_container_width=True)

        # simple keyword frequency
        all_comments = " ".join(fb['Comments'].astype(str).tolist()).lower()
        tokens = [t.strip('.,!?:;()[]"\'') for t in all_comments.split() if len(t)>3]
        common = Counter(tokens).most_common(10)
        if common:
            kw_df = pd.DataFrame(common, columns=['word','count'])
            st.markdown("**Top words in feedback**")
            st.table(kw_df)

# ---------------------------
# Attendance analytics and charts
# ---------------------------
st.markdown("---")
st.header("Analytics")
col_a, col_b = st.columns(2)
with col_a:
    st.subheader("Attendance by Department")
    if 'Department' in st.session_state.attendance_df.columns and len(st.session_state.attendance_df)>0:
        group = st.session_state.attendance_df.groupby('Department')['Attended'].agg(['sum','count']).reset_index()
        group['attendance_pct'] = group['sum'] / group['count'] * 100
        fig2 = px.bar(group, x='Department', y='attendance_pct', text='attendance_pct')
        fig2.update_layout(yaxis_title='Attendance %', template='plotly_dark')
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info('Add a Department column to attendance data to see this chart')

with col_b:
    st.subheader("Registration timeline (demo)")
    if 'Registered At' in st.session_state.attendance_df.columns and len(st.session_state.attendance_df)>0:
        tmp = st.session_state.attendance_df.copy()
        try:
            tmp['Registered At'] = pd.to_datetime(tmp['Registered At'])
            times = tmp.groupby(tmp['Registered At'].dt.date).size().reset_index(name='registrations')
            fig3 = px.line(times, x='Registered At', y='registrations', markers=True)
            fig3.update_layout(xaxis_title='Date', template='plotly_dark')
            st.plotly_chart(fig3, use_container_width=True)
        except Exception as e:
            st.error('Unable to parse Registered At column as datetime — ensure it is a valid date or ISO string.')
    else:
        st.info('Provide Registered At timestamps in the attendance CSV to see timeline')

# ---------------------------
# Admin actions: clear session data
# ---------------------------
st.markdown("---")
st.markdown("### Admin")
colc1, colc2, colc3 = st.columns(3)
with colc1:
    if st.button("Clear images"):
        st.session_state.images = []
        st.success('Images cleared')
with colc2:
    if st.button("Clear attendance"):
        st.session_state.attendance_df = pd.DataFrame(columns=st.session_state.attendance_df.columns)
        st.success('Attendance cleared')
with colc3:
    if st.button("Clear feedback"):
        st.session_state.feedback = pd.DataFrame(columns=st.session_state.feedback.columns)
        st.success('Feedback cleared')

st.markdown("---")
st.markdown("#### Notes & next steps")
st.markdown(textwrap.dedent('''
- This demo app is designed to be a production-grade starting point. For persistence across restarts, connect to a database (Firebase, Supabase, PostgreSQL) or save uploads to cloud storage (S3/GCS).
- For richer animations consider embedding Lottie animations (via streamlit-lottie) or building a React front-end and communicating via an API.
- For feedback sentiment analysis, integrate a small NLP model or use an external API. Also consider authentication for admin actions.
'''))

# end of file
