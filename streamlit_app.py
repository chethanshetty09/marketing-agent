"""
🪷 Ayurvedic Clinic Multi-Agent Marketing Dashboard
Streamlit Community Cloud compatible — self-contained, no external module dependencies.
Deploy at: https://share.streamlit.io
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

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
    h1, h2, h3 { font-family: 'Cormorant Garamond', Georgia, serif !important; color: #2C2416; }

    .agent-card {
        background: white;
        border-radius: 12px;
        padding: 20px;
        border-left: 5px solid;
        box-shadow: 0 2px 8px rgba(44,36,22,0.06);
        margin-bottom: 12px;
    }
    .metric-box {
        background: white;
        border-radius: 10px;
        padding: 18px;
        text-align: center;
        box-shadow: 0 2px 8px rgba(44,36,22,0.06);
        margin-bottom: 8px;
    }
    .status-running { color: #2E7D32; font-weight: 700; }
    .status-idle { color: #8B7D6B; font-weight: 600; }
    .status-error { color: #C62828; font-weight: 700; }
    .flow-arrow { color: #C4B8A8; font-size: 20px; text-align: center; padding: 8px 0; }
    .integration-badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 12px;
        margin: 3px;
        font-family: 'Nunito Sans', sans-serif;
    }
    .badge-connected { background: #E8F5E9; color: #2E7D32; }
    .badge-pending { background: #FFF3E0; color: #E65100; }
</style>
""", unsafe_allow_html=True)


# ─── Agent Definitions ───
AGENTS = {
    "content_sage": {
        "name": "Content Sage",
        "sanskrit": "वाक्पटु",
        "emoji": "🪷",
        "color": "#5B7C4F",
        "role": "Content Creation & SEO",
        "description": "Generates educational, SEO-optimized content — blog posts, social media, YouTube scripts, and AI-generated visuals.",
        "tools": ["SEO Keywords", "Instagram", "Facebook", "DALL-E Images", "YouTube Scripts", "CRM Segments"],
        "schedule": "Daily",
    },
    "community_weaver": {
        "name": "Community Weaver",
        "sanskrit": "संगठक",
        "emoji": "🙏",
        "color": "#B8860B",
        "role": "Patient Engagement & Nurture",
        "description": "Builds patient relationships through WhatsApp follow-ups, email campaigns, referral programs, and community events.",
        "tools": ["WhatsApp API", "SendGrid Email", "Patient CRM", "Razorpay Links", "Facebook"],
        "schedule": "Daily",
    },
    "reputation_guard": {
        "name": "Reputation Guard",
        "sanskrit": "यशरक्षक",
        "emoji": "🛡️",
        "color": "#8B4513",
        "role": "Reviews & Reputation Management",
        "description": "Monitors Google Reviews and Practo, responds to feedback, sends review requests, and tracks competitors.",
        "tools": ["Google Reviews", "Practo Monitor", "Practo Competitors", "WhatsApp Templates", "CRM"],
        "schedule": "Every 2 hours",
    },
    "insight_oracle": {
        "name": "Insight Oracle",
        "sanskrit": "दृष्टिदाता",
        "emoji": "🔮",
        "color": "#4A3B6B",
        "role": "Analytics & Strategy",
        "description": "Synthesizes data from all channels — Google Ads, Analytics, Razorpay, CRM, YouTube — into actionable strategy.",
        "tools": ["Google Analytics", "Google Ads", "Search Console", "Razorpay Revenue", "YouTube Analytics", "CRM Lifecycle"],
        "schedule": "Weekly",
    },
}

INTEGRATIONS = {
    "WhatsApp Business": {"key": "WHATSAPP_ACCESS_TOKEN", "icon": "💬", "category": "Messaging"},
    "Google Reviews": {"key": "GOOGLE_SERVICE_ACCOUNT_JSON", "icon": "⭐", "category": "Reputation"},
    "Practo": {"key": "PRACTO_DOCTOR_URL", "icon": "🏥", "category": "Reputation"},
    "Meta (IG/FB)": {"key": "META_ACCESS_TOKEN", "icon": "📸", "category": "Social"},
    "YouTube": {"key": "YOUTUBE_CHANNEL_ID", "icon": "🎬", "category": "Social"},
    "Google Ads": {"key": "GOOGLE_ADS_CUSTOMER_ID", "icon": "📢", "category": "Paid"},
    "Google Analytics": {"key": "GA_PROPERTY_ID", "icon": "📊", "category": "Analytics"},
    "Search Console": {"key": "GSC_SITE_URL", "icon": "🔍", "category": "SEO"},
    "SendGrid": {"key": "SENDGRID_API_KEY", "icon": "📧", "category": "Email"},
    "Razorpay": {"key": "RAZORPAY_KEY_ID", "icon": "💳", "category": "Payments"},
    "OpenAI (Images)": {"key": "OPENAI_API_KEY", "icon": "🎨", "category": "AI"},
    "Patient CRM": {"key": None, "icon": "🗂️", "category": "Database"},
}


def load_recent_outputs():
    """Load recent agent output files."""
    output_dir = Path("outputs")
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
    st.markdown("## 🪷 Control Center")
    st.markdown("---")

    st.markdown("### ▶ Run Workflows")
    col1, col2 = st.columns(2)
    with col1:
        daily_btn = st.button("Daily", use_container_width=True, type="primary")
    with col2:
        weekly_btn = st.button("Weekly", use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        review_btn = st.button("🛡️ Reviews", use_container_width=True)
    with col4:
        monthly_btn = st.button("📊 Monthly", use_container_width=True)

    if daily_btn:
        st.session_state["run_mode"] = "daily"
    if weekly_btn:
        st.session_state["run_mode"] = "weekly"
    if review_btn:
        st.session_state["run_mode"] = "review-scan"
    if monthly_btn:
        st.session_state["run_mode"] = "monthly"

    st.markdown("---")

    # Clinic Configuration
    st.markdown("### ⚙️ Clinic Config")
    clinic_name = st.text_input("Clinic Name", value=os.getenv("CLINIC_NAME", "Ayurvedic Wellness Clinic"))
    clinic_city = st.text_input("City", value=os.getenv("CLINIC_CITY", "Bengaluru"))
    specialties = st.multiselect(
        "Specialties",
        ["Panchakarma", "Prakriti Analysis", "Skin Care", "Weight Management",
         "Stress Relief", "Joint Care", "Digestive Health", "Hair Treatment",
         "Detox Therapy", "Women's Health"],
        default=["Panchakarma", "Prakriti Analysis", "Skin Care"],
    )

    st.markdown("---")

    # Integration Status
    st.markdown("### 🔌 Integrations")
    connected_count = 0
    for name, info in INTEGRATIONS.items():
        if info["key"] is None:
            is_connected = True  # CRM is built-in
        else:
            is_connected = bool(os.getenv(info["key"]))
        if is_connected:
            connected_count += 1
        icon = "🟢" if is_connected else "🔴"
        st.markdown(f"{icon} {info['icon']} {name}")

    st.caption(f"{connected_count}/{len(INTEGRATIONS)} integrations active")


# ─── Main Content ───
st.markdown("# 🪷 Ayurvedic Marketing Agents")
st.markdown(f"*Multi-agent AI system for **{clinic_name}**, {clinic_city}*")

# ─── Agent Status Cards ───
st.markdown("## Agent Overview")
cols = st.columns(4)
for i, (agent_id, agent) in enumerate(AGENTS.items()):
    with cols[i]:
        tools_html = " ".join(
            [f'<span class="integration-badge badge-connected">{t}</span>' for t in agent["tools"][:4]]
        )
        st.markdown(f"""
        <div class="agent-card" style="border-left-color: {agent['color']}">
            <div style="font-size: 28px; margin-bottom: 6px;">{agent['emoji']}</div>
            <div style="font-size: 17px; font-weight: 700; color: {agent['color']}; font-family: 'Cormorant Garamond', serif;">
                {agent['name']}
            </div>
            <div style="font-size: 11px; color: #8B7D6B; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 8px;">
                {agent['role']}
            </div>
            <div style="font-size: 12px; color: #5A5044; line-height: 1.5; margin-bottom: 10px; font-family: 'Nunito Sans', sans-serif;">
                {agent['description']}
            </div>
            <div style="margin-bottom: 8px;">{tools_html}</div>
            <div style="font-size: 12px; font-family: 'Nunito Sans', sans-serif;" class="status-idle">
                ● Idle — Runs {agent['schedule']}
            </div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")

# ─── Tabbed Content ───
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Dashboard", "📝 Content Queue", "⭐ Reviews", "👥 Patient CRM", "📋 Logs"
])

with tab1:
    st.markdown("### Marketing Performance")

    # Metrics row
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Website Visits (7d)", "1,247", "+12%")
    m2.metric("Google Reviews", "4.6 ★ (89)", "+3 this week")
    m3.metric("Practo Rating", "4.7 ★ (142)", "+5 this week")
    m4.metric("Social Engagement", "2.3K", "+18%")
    m5.metric("Revenue (30d)", "₹3,45,000", "+8%")

    st.markdown("")

    # Charts row
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.markdown("### Traffic Sources")
        traffic_data = pd.DataFrame({
            "Source": ["Google Organic", "Practo", "Direct", "Social Media", "Google Ads", "WhatsApp", "Email", "Referral"],
            "Sessions": [480, 320, 290, 210, 180, 145, 78, 44],
        })
        fig = px.bar(
            traffic_data, x="Sessions", y="Source", orientation="h",
            color_discrete_sequence=["#5B7C4F"],
        )
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Nunito Sans", size=12),
            margin=dict(l=0, r=0, t=10, b=0),
            height=320,
            yaxis=dict(autorange="reversed"),
        )
        st.plotly_chart(fig, use_container_width=True)

    with chart_col2:
        st.markdown("### Patient Acquisition Funnel")
        funnel_data = pd.DataFrame({
            "Stage": ["Website Visit", "Treatment Page", "Contact Click", "Booking", "Treatment Done", "Review Left"],
            "Count": [1247, 543, 198, 67, 52, 23],
        })
        fig2 = go.Figure(go.Funnel(
            y=funnel_data["Stage"], x=funnel_data["Count"],
            marker=dict(color=["#5B7C4F", "#6B8C5F", "#B8860B", "#8B4513", "#4A3B6B", "#6A5ACD"]),
        ))
        fig2.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", font=dict(family="Nunito Sans", size=12),
            margin=dict(l=0, r=0, t=10, b=0),
            height=320,
        )
        st.plotly_chart(fig2, use_container_width=True)

    # Revenue & Ads ROI
    st.markdown("### Revenue vs Ad Spend (Last 30 Days)")
    rev_col1, rev_col2, rev_col3 = st.columns(3)
    rev_col1.metric("Razorpay Revenue", "₹3,45,000", "+₹27,000")
    rev_col2.metric("Google Ads Spend", "₹18,500", "-₹2,000")
    rev_col3.metric("ROAS", "18.6x", "+2.1x")

    days = list(range(1, 31))
    revenue_trend = pd.DataFrame({
        "Day": days,
        "Revenue (₹)": [8500 + (d * 300) + (d % 7 * 2000) for d in days],
        "Ad Spend (₹)": [500 + (d % 5 * 100) for d in days],
    })
    fig3 = px.line(
        revenue_trend, x="Day", y=["Revenue (₹)", "Ad Spend (₹)"],
        color_discrete_map={"Revenue (₹)": "#5B7C4F", "Ad Spend (₹)": "#C62828"},
    )
    fig3.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Nunito Sans"),
        margin=dict(l=0, r=0, t=10, b=0),
        height=250, legend=dict(orientation="h", yanchor="top", y=1.15),
    )
    st.plotly_chart(fig3, use_container_width=True)


with tab2:
    st.markdown("### Content Queue")
    st.info("Content Sage generates content here. Run the **Daily** workflow to populate.")

    content_items = [
        {"type": "📸 Instagram", "title": "5 Morning Dinacharya Rituals for Vata Season",
         "status": "✅ Ready", "scheduled": "Tomorrow 9:00 AM", "image": "AI Generated"},
        {"type": "📘 Facebook", "title": "Understanding Your Prakriti — Free Assessment This Saturday",
         "status": "✅ Ready", "scheduled": "Today 6:00 PM", "image": "AI Generated"},
        {"type": "📝 Blog", "title": f"Panchakarma in {clinic_city}: Complete Guide to Detox Therapy",
         "status": "📝 Outline", "scheduled": "Thursday", "image": "—"},
        {"type": "🎬 YouTube", "title": "What Happens During a Panchakarma Session? (5 min)",
         "status": "📄 Script", "scheduled": "Friday", "image": "—"},
        {"type": "🎬 Reel", "title": "3 Ayurvedic Herbs You Already Have in Your Kitchen",
         "status": "📄 Script", "scheduled": "Wednesday", "image": "—"},
        {"type": "📸 Instagram", "title": "Patient Transformation Story — Chronic Pain Relief",
         "status": "⏳ Draft", "scheduled": "Next Monday", "image": "Pending"},
    ]

    # Header
    h1, h2, h3, h4, h5 = st.columns([1, 3, 1, 1.5, 1])
    h1.markdown("**Platform**")
    h2.markdown("**Title**")
    h3.markdown("**Status**")
    h4.markdown("**Scheduled**")
    h5.markdown("**Visual**")

    for item in content_items:
        c1, c2, c3, c4, c5 = st.columns([1, 3, 1, 1.5, 1])
        c1.write(item["type"])
        c2.write(item["title"])
        c3.write(item["status"])
        c4.write(f"📅 {item['scheduled']}")
        c5.write(f"🎨 {item['image']}")


with tab3:
    st.markdown("### Review Monitor")

    rev_col1, rev_col2 = st.columns(2)
    with rev_col1:
        st.markdown("#### Google Reviews")
        google_reviews = [
            {"stars": 5, "text": "Amazing Panchakarma experience! Dr. was very thorough with the diagnosis.",
             "replied": True, "date": "2 days ago", "reviewer": "Priya S."},
            {"stars": 4, "text": "Good treatment, but waiting time was long. Staff is friendly.",
             "replied": False, "date": "3 days ago", "reviewer": "Rahul M."},
            {"stars": 2, "text": "Expensive compared to other clinics. Expected more for the price.",
             "replied": False, "date": "5 days ago", "reviewer": "Anita K."},
        ]
        for rev in google_reviews:
            stars = "⭐" * rev["stars"]
            status = "✅ Replied" if rev["replied"] else "⏳ Pending"
            urgent = "🚨 " if rev["stars"] <= 2 else ""
            border_color = "#2E7D32" if rev["replied"] else ("#C62828" if rev["stars"] <= 2 else "#B8860B")
            st.markdown(f"""
            <div class="agent-card" style="border-left-color: {border_color}">
                <strong>{urgent}{stars}</strong> — {rev['reviewer']} — {rev['date']} — {status}<br>
                <span style="color: #5A5044; font-family: 'Nunito Sans', sans-serif; font-size: 14px;">{rev['text']}</span>
            </div>
            """, unsafe_allow_html=True)

    with rev_col2:
        st.markdown("#### Practo Reviews")
        practo_reviews = [
            {"stars": 5, "text": "Best Ayurvedic doctor in the city. Very knowledgeable about treatments.",
             "replied": True, "date": "1 day ago", "reviewer": "Deepa R."},
            {"stars": 5, "text": "Shirodhara session was incredibly relaxing. Highly recommend!",
             "replied": True, "date": "4 days ago", "reviewer": "Vikram P."},
            {"stars": 3, "text": "Treatment was okay. Results took longer than expected.",
             "replied": False, "date": "6 days ago", "reviewer": "Kavitha N."},
        ]
        for rev in practo_reviews:
            stars = "⭐" * rev["stars"]
            status = "✅ Replied" if rev["replied"] else "⏳ Pending"
            border_color = "#2E7D32" if rev["replied"] else "#B8860B"
            st.markdown(f"""
            <div class="agent-card" style="border-left-color: {border_color}">
                <strong>{stars}</strong> — {rev['reviewer']} — {rev['date']} — {status}<br>
                <span style="color: #5A5044; font-family: 'Nunito Sans', sans-serif; font-size: 14px;">{rev['text']}</span>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### Competitor Snapshot (Practo)")
    comp_data = pd.DataFrame({
        "Clinic": [f"🏥 {clinic_name} (You)", "🏥 Competitor A", "🏥 Competitor B", "🏥 Competitor C"],
        "Rating": [4.7, 4.5, 4.3, 4.1],
        "Reviews": [142, 210, 89, 156],
        "Review Velocity (30d)": [12, 8, 5, 10],
    })
    st.dataframe(comp_data, use_container_width=True, hide_index=True)


with tab4:
    st.markdown("### Patient CRM")
    st.info("Patient data is managed by the built-in SQLite CRM. Below is a sample view.")

    crm_col1, crm_col2, crm_col3, crm_col4 = st.columns(4)
    crm_col1.metric("Total Patients", "234")
    crm_col2.metric("Active", "189", "+12 this month")
    crm_col3.metric("Churn Risk", "18", "needs re-engagement")
    crm_col4.metric("Avg Lifetime Value", "₹8,450")

    st.markdown("### Patient Segments")
    segments = pd.DataFrame({
        "Segment": [
            "🔥 Needs Follow-up (48hrs)", "🌬️ Vata Patients", "☀️ Pitta Patients",
            "🌍 Kapha Patients", "⚠️ Inactive (60+ days)", "💎 High Value (>₹10K)",
            "📝 No Review Asked Yet", "✅ Recent Completions"
        ],
        "Count": [8, 67, 52, 43, 18, 31, 45, 12],
        "Action": [
            "WhatsApp follow-up", "Send Vata seasonal tips", "Send Pitta cooling tips",
            "Send Kapha energizing tips", "Re-engagement campaign", "VIP wellness offers",
            "Send review request", "Ask for Google/Practo review"
        ],
    })
    st.dataframe(segments, use_container_width=True, hide_index=True)

    st.markdown("### Dosha Distribution")
    dosha_data = pd.DataFrame({
        "Dosha": ["Vata", "Pitta", "Kapha", "Vata-Pitta", "Pitta-Kapha", "Vata-Kapha", "Unknown"],
        "Patients": [67, 52, 43, 28, 19, 14, 11],
    })
    fig_dosha = px.pie(
        dosha_data, values="Patients", names="Dosha",
        color_discrete_sequence=["#5B7C4F", "#B8860B", "#8B4513", "#6B8C5F", "#D4A843", "#4A3B6B", "#C4B8A8"],
    )
    fig_dosha.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", font=dict(family="Nunito Sans"),
        height=300, margin=dict(l=0, r=0, t=10, b=0),
    )
    st.plotly_chart(fig_dosha, use_container_width=True)


with tab5:
    st.markdown("### Agent Run Logs")
    outputs = load_recent_outputs()
    if outputs:
        for output in outputs:
            with st.expander(
                f"📄 {output.get('mode', 'unknown')} — {output.get('timestamp', 'N/A')}"
            ):
                st.json(output)
    else:
        st.info("No agent runs yet. Trigger a workflow from the sidebar to see results here.")

    st.markdown("---")
    st.markdown("### Agent Data Flow")
    st.markdown("""
    ```
    ┌─────────────┐    content     ┌─────────────────┐
    │ Content Sage │ ──────────→  │ Community Weaver  │
    │   (Daily)    │              │     (Daily)       │
    └──────┬───────┘              └────────┬──────────┘
           │ content                       │ engagement data
           ▼                               ▼
    ┌──────────────┐   reviews    ┌─────────────────┐
    │  Reputation   │ ──────────→ │  Insight Oracle  │
    │    Guard      │             │    (Weekly)      │
    │  (Hourly)     │ ←────────── │                  │
    └───────────────┘  strategy   └─────────────────┘
                                         │
                                    strategy briefs
                                         │
                              ┌──────────┼──────────┐
                              ▼          ▼          ▼
                         Content    Community   Reputation
                          Sage       Weaver       Guard
    ```
    """)


# ─── Run Executor ───
if "run_mode" in st.session_state:
    mode = st.session_state.pop("run_mode")
    st.markdown("---")
    st.markdown(f"### 🚀 Running `{mode}` workflow...")
    st.warning(
        f"To execute the agents, run this in your terminal:\n\n"
        f"```bash\n"
        f"cd marketing-agent && python main.py {mode}\n"
        f"```\n\n"
        f"Results will appear in the **Logs** tab after the run completes.\n\n"
        f"*Note: Agent execution requires API keys configured in your `.env` file.*"
    )


# ─── Footer ───
st.markdown("---")
st.markdown(
    '<div style="text-align: center; color: #A89880; font-size: 12px; font-family: \'Nunito Sans\', sans-serif;">'
    '🪷 Ayurvedic Marketing Agent System — 4 Agents • 12 Tool Modules • 30+ Integrations'
    '</div>',
    unsafe_allow_html=True,
)
