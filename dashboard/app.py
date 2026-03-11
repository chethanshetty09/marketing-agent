"""
Streamlit Dashboard — Control center for the Ayurvedic Marketing Agent System.
Run with: streamlit run dashboard/app.py
"""

import json
import os
import sys
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import yaml

# Add parent to path so imports work
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# ─── Page Config ───
st.set_page_config(
    page_title="Ayurvedic Marketing Agents",
    page_icon="🪷",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom Styling ───
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500;600;700&family=Nunito+Sans:wght@300;400;600;700&display=swap');

    .stApp { background-color: #FAF7F2; }
    h1, h2, h3 { font-family: 'Cormorant Garamond', Georgia, serif; color: #2C2416; }
    p, li, span, div { font-family: 'Nunito Sans', sans-serif; }

    .agent-card {
        background: white;
        border-radius: 12px;
        padding: 20px;
        border-left: 5px solid;
        box-shadow: 0 2px 8px rgba(44,36,22,0.06);
        margin-bottom: 12px;
    }
    .metric-card {
        background: white;
        border-radius: 10px;
        padding: 16px 20px;
        text-align: center;
        box-shadow: 0 2px 8px rgba(44,36,22,0.06);
    }
    .status-running { color: #2E7D32; font-weight: 700; }
    .status-idle { color: #8B7D6B; font-weight: 600; }
    .status-error { color: #C62828; font-weight: 700; }
</style>
""", unsafe_allow_html=True)


# ─── Agent Definitions ───
AGENTS = {
    "content_sage": {
        "name": "Content Sage", "sanskrit": "वाक्पटु", "emoji": "🪷",
        "color": "#5B7C4F", "role": "Content & SEO",
    },
    "community_weaver": {
        "name": "Community Weaver", "sanskrit": "संगठक", "emoji": "🙏",
        "color": "#B8860B", "role": "Engagement & Nurture",
    },
    "reputation_guard": {
        "name": "Reputation Guard", "sanskrit": "यशरक्षक", "emoji": "🛡️",
        "color": "#8B4513", "role": "Reviews & Reputation",
    },
    "insight_oracle": {
        "name": "Insight Oracle", "sanskrit": "दृष्टिदाता", "emoji": "🔮",
        "color": "#4A3B6B", "role": "Analytics & Strategy",
    },
}


def load_recent_outputs():
    """Load recent agent output files."""
    output_dir = Path(__file__).resolve().parent.parent / "outputs"
    if not output_dir.exists():
        return []
    files = sorted(output_dir.glob("*.json"), reverse=True)[:20]
    results = []
    for f in files:
        try:
            with open(f) as fh:
                data = json.load(fh)
                data["filename"] = f.name
                results.append(data)
        except Exception:
            pass
    return results


# ─── Sidebar ───
with st.sidebar:
    st.markdown("## 🪷 Agent Control Center")
    st.markdown("---")

    st.markdown("### Run Workflows")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("▶ Daily", use_container_width=True, type="primary"):
            st.session_state["run_mode"] = "daily"
    with col2:
        if st.button("▶ Weekly", use_container_width=True):
            st.session_state["run_mode"] = "weekly"

    col3, col4 = st.columns(2)
    with col3:
        if st.button("🛡️ Review Scan", use_container_width=True):
            st.session_state["run_mode"] = "review-scan"
    with col4:
        if st.button("📊 Monthly", use_container_width=True):
            st.session_state["run_mode"] = "monthly"

    st.markdown("---")
    st.markdown("### Configuration")
    st.text_input("Clinic Name", value="Ayurvedic Wellness Clinic", key="clinic_name")
    st.text_input("City", value="Bengaluru", key="clinic_city")
    st.multiselect(
        "Specialties",
        ["Panchakarma", "Prakriti Analysis", "Skin Care", "Weight Management",
         "Stress Relief", "Joint Care", "Digestive Health", "Hair Treatment"],
        default=["Panchakarma", "Prakriti Analysis", "Skin Care"],
        key="specialties",
    )

    st.markdown("---")
    st.markdown("### API Status")
    apis = {
        "WhatsApp": bool(os.getenv("WHATSAPP_ACCESS_TOKEN")),
        "Google Business": bool(os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")),
        "Meta (IG/FB)": bool(os.getenv("META_ACCESS_TOKEN")),
        "SendGrid": bool(os.getenv("SENDGRID_API_KEY")),
        "Google Analytics": bool(os.getenv("GA_PROPERTY_ID")),
    }
    for api_name, connected in apis.items():
        icon = "🟢" if connected else "🔴"
        st.markdown(f"{icon} {api_name}")


# ─── Main Content ───
st.markdown("# 🪷 Ayurvedic Marketing Agents")
st.markdown("*Multi-agent AI system for clinic growth*")

# ─── Agent Status Cards ───
st.markdown("## Agent Overview")
cols = st.columns(4)
for i, (agent_id, agent) in enumerate(AGENTS.items()):
    with cols[i]:
        st.markdown(f"""
        <div class="agent-card" style="border-left-color: {agent['color']}">
            <div style="font-size: 28px; margin-bottom: 8px;">{agent['emoji']}</div>
            <div style="font-size: 18px; font-weight: 700; color: {agent['color']}; font-family: 'Cormorant Garamond', serif;">
                {agent['name']}
            </div>
            <div style="font-size: 11px; color: #8B7D6B; letter-spacing: 1px; text-transform: uppercase;">
                {agent['role']}
            </div>
            <div style="margin-top: 10px; font-size: 13px;" class="status-idle">
                ● Idle
            </div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")

# ─── Tabbed Content ───
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Dashboard", "📝 Content Queue", "⭐ Reviews", "📋 Logs"
])

with tab1:
    st.markdown("### Marketing Performance")

    # Mock metrics for demo (replace with real API data in production)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Website Visits (7d)", "1,247", "+12%")
    m2.metric("Google Reviews", "4.6 ★ (89)", "+3 this week")
    m3.metric("Social Engagement", "2.3K", "+18%")
    m4.metric("WhatsApp Campaigns", "82% read rate", "+5%")

    st.markdown("### Traffic Sources")
    # Demo chart
    traffic_data = pd.DataFrame({
        "Source": ["Google Organic", "Direct", "Social Media", "WhatsApp", "Email", "Referral"],
        "Sessions": [480, 290, 210, 145, 78, 44],
    })
    fig = px.bar(
        traffic_data, x="Source", y="Sessions",
        color_discrete_sequence=["#5B7C4F"],
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Nunito Sans"),
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Patient Acquisition Funnel")
    funnel_data = pd.DataFrame({
        "Stage": ["Website Visit", "Treatment Page View", "Contact Click", "Booking", "Completed Treatment"],
        "Count": [1247, 543, 198, 67, 52],
    })
    fig2 = go.Figure(go.Funnel(
        y=funnel_data["Stage"], x=funnel_data["Count"],
        marker=dict(color=["#5B7C4F", "#6B8C5F", "#B8860B", "#8B4513", "#4A3B6B"]),
    ))
    fig2.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", font=dict(family="Nunito Sans"),
    )
    st.plotly_chart(fig2, use_container_width=True)

with tab2:
    st.markdown("### Content Queue")
    st.info("Content Sage generates content here. Run the **Daily** workflow to populate.")

    # Sample content queue
    content_items = [
        {"type": "📸 Instagram", "title": "5 Morning Dinacharya Rituals for Vata Season",
         "status": "Draft", "scheduled": "Tomorrow 9:00 AM"},
        {"type": "📘 Facebook", "title": "Understanding Your Prakriti — Free Assessment This Saturday",
         "status": "Ready", "scheduled": "Today 6:00 PM"},
        {"type": "📝 Blog", "title": "Panchakarma in Bengaluru: Complete Guide to Detox Therapy",
         "status": "Outline", "scheduled": "Thursday"},
        {"type": "🎬 Reel", "title": "3 Ayurvedic Herbs You Already Have in Your Kitchen",
         "status": "Script Ready", "scheduled": "Wednesday"},
    ]
    for item in content_items:
        col_a, col_b, col_c, col_d = st.columns([1, 3, 1, 2])
        col_a.write(item["type"])
        col_b.write(item["title"])
        col_c.write(f"`{item['status']}`")
        col_d.write(f"📅 {item['scheduled']}")

with tab3:
    st.markdown("### Review Monitor")
    st.info("Reputation Guard monitors reviews here. Run **Review Scan** to fetch latest.")

    # Sample reviews
    reviews = [
        {"stars": "⭐⭐⭐⭐⭐", "text": "Amazing Panchakarma experience! Dr. was very thorough.",
         "replied": True, "date": "2 days ago"},
        {"stars": "⭐⭐⭐⭐", "text": "Good treatment, but waiting time was long.",
         "replied": False, "date": "3 days ago"},
        {"stars": "⭐⭐", "text": "Expensive compared to other clinics.",
         "replied": False, "date": "5 days ago"},
    ]
    for rev in reviews:
        status = "✅ Replied" if rev["replied"] else "⏳ Pending"
        urgent = "🚨 " if "⭐⭐" == rev["stars"] else ""
        st.markdown(f"""
        <div class="agent-card" style="border-left-color: {'#2E7D32' if rev['replied'] else '#C62828'}">
            <strong>{urgent}{rev['stars']}</strong> — {rev['date']} — {status}<br>
            <span style="color: #5A5044;">{rev['text']}</span>
        </div>
        """, unsafe_allow_html=True)

with tab4:
    st.markdown("### Agent Run Logs")
    outputs = load_recent_outputs()
    if outputs:
        for output in outputs:
            with st.expander(
                f"📄 {output.get('mode', 'unknown')} — {output.get('timestamp', 'N/A')}"
            ):
                st.json(output)
    else:
        st.info("No agent runs yet. Use the sidebar to trigger a workflow.")

# ─── Run Executor ───
if "run_mode" in st.session_state:
    mode = st.session_state.pop("run_mode")
    st.markdown("---")
    st.markdown(f"### 🚀 Running `{mode}` workflow...")
    with st.spinner(f"Executing {mode} agent crew — this may take a few minutes..."):
        st.code(f"python main.py {mode}", language="bash")
        st.info(
            f"To run the agents, execute this command in your terminal:\n\n"
            f"```\ncd ayurvedic-agents && python main.py {mode}\n```\n\n"
            f"The results will appear in the **Logs** tab after execution."
        )
