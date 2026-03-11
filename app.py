"""
🪷 Ayurvedic Clinic Multi-Agent Marketing System — Dashboard
Streamlit Community Cloud compatible (self-contained, no parent imports).
Deploy: Connect this repo to share.streamlit.io
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
    .tool-badge {
        display: inline-block;
        background: #E8F0E4;
        color: #3D5A35;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 12px;
        margin: 2px 4px 2px 0;
        font-family: 'Nunito Sans', sans-serif;
    }
    .tool-badge-gold {
        background: #FFF5E0;
        color: #8B6508;
    }
    .tool-badge-brown {
        background: #F5EDE4;
        color: #6B3410;
    }
    .tool-badge-purple {
        background: #EEEAF5;
        color: #352A50;
    }
    .flow-arrow {
        text-align: center;
        font-size: 24px;
        color: #C4B8A8;
        padding: 5px 0;
    }
    .section-divider {
        border: none;
        border-top: 1px solid #E8E0D4;
        margin: 24px 0;
    }
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
        "badge_class": "tool-badge",
        "description": "Generates educational, trust-building content that positions your clinic as the authentic Ayurvedic authority.",
        "tools": ["SEO Keywords", "Search Console", "Instagram", "Facebook", "DALL-E Images", "YouTube Scripts", "CRM Segments"],
        "tasks": [
            "Generate 1 SEO blog post per week",
            "Create 7 social media posts with AI images",
            "Produce 2 Instagram Reels scripts",
            "YouTube video scripts for treatments",
            "Update seasonal Ritucharya content",
        ],
    },
    "community_weaver": {
        "name": "Community Weaver",
        "sanskrit": "संगठक",
        "emoji": "🙏",
        "color": "#B8860B",
        "role": "Patient Engagement & Nurture",
        "badge_class": "tool-badge tool-badge-gold",
        "description": "Builds deep patient relationships through personalized outreach, lifecycle campaigns, and referral programs.",
        "tools": ["WhatsApp API", "Email Campaigns", "Patient CRM", "Razorpay Links", "Facebook"],
        "tasks": [
            "Post-treatment follow-ups within 48 hours",
            "Dosha-personalized wellness tips",
            "Seasonal campaign triggers",
            "Referral program management",
            "Payment link generation",
        ],
    },
    "reputation_guard": {
        "name": "Reputation Guard",
        "sanskrit": "यशरक्षक",
        "emoji": "🛡️",
        "color": "#8B4513",
        "role": "Reviews & Reputation",
        "badge_class": "tool-badge tool-badge-brown",
        "description": "Protects and amplifies your online reputation across Google AND Practo.",
        "tools": ["Google Reviews", "Practo Reviews", "Practo Competitors", "WhatsApp Templates", "CRM"],
        "tasks": [
            "Scan reviews every 2 hours",
            "Respond to negative reviews < 4 hours",
            "Send review requests to happy patients",
            "Competitor review velocity tracking",
            "Curate testimonials for marketing",
        ],
    },
    "insight_oracle": {
        "name": "Insight Oracle",
        "sanskrit": "दृष्टिदाता",
        "emoji": "🔮",
        "color": "#4A3B6B",
        "role": "Analytics & Strategy",
        "badge_class": "tool-badge tool-badge-purple",
        "description": "Synthesizes data from ALL channels to produce actionable strategy — ensuring every rupee is optimized.",
        "tools": ["Google Analytics", "Google Ads", "Search Console", "Razorpay Revenue", "CRM Lifecycle", "YouTube Analytics", "Practo Competitors"],
        "tasks": [
            "Weekly strategy brief every Monday",
            "ROAS analysis (Razorpay vs Google Ads)",
            "Patient churn risk identification",
            "Competitor intelligence reports",
            "Budget reallocation recommendations",
        ],
    },
}

DATA_FLOWS = [
    {"from": "content_sage", "to": "community_weaver", "label": "Content feeds nurture campaigns"},
    {"from": "content_sage", "to": "reputation_guard", "label": "Content fuels testimonial promotion"},
    {"from": "community_weaver", "to": "insight_oracle", "label": "Engagement data flows to analytics"},
    {"from": "reputation_guard", "to": "insight_oracle", "label": "Reputation signals inform strategy"},
    {"from": "insight_oracle", "to": "content_sage", "label": "Strategy guides content direction"},
    {"from": "insight_oracle", "to": "community_weaver", "label": "Insights optimize nurture flows"},
    {"from": "insight_oracle", "to": "reputation_guard", "label": "Data prioritizes reputation efforts"},
    {"from": "reputation_guard", "to": "content_sage", "label": "Top reviews become content assets"},
]

INTEGRATIONS = {
    "Core": [
        {"name": "WhatsApp Business", "icon": "💬", "status": "whatsapp"},
        {"name": "Google Reviews", "icon": "⭐", "status": "google"},
        {"name": "Meta (IG/FB)", "icon": "📸", "status": "meta"},
        {"name": "SendGrid Email", "icon": "📧", "status": "sendgrid"},
        {"name": "Google Analytics", "icon": "📊", "status": "ga"},
        {"name": "Google Search Console", "icon": "🔍", "status": "gsc"},
    ],
    "New": [
        {"name": "Practo", "icon": "🏥", "status": "practo"},
        {"name": "Google Ads", "icon": "💰", "status": "gads"},
        {"name": "Patient CRM", "icon": "🗃️", "status": "crm"},
        {"name": "DALL-E Images", "icon": "🎨", "status": "dalle"},
        {"name": "YouTube", "icon": "▶️", "status": "youtube"},
        {"name": "Razorpay", "icon": "💳", "status": "razorpay"},
    ],
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


def check_api_status(key_name):
    """Check if an API key is configured via Streamlit secrets or env vars."""
    # Check Streamlit secrets first, then environment
    try:
        if key_name in st.secrets:
            return bool(st.secrets[key_name])
    except Exception:
        pass
    return bool(os.getenv(key_name, ""))


# ─── Sidebar ───
with st.sidebar:
    st.markdown("## 🪷 Control Center")
    st.markdown("---")

    # Clinic Config
    st.markdown("### 🏥 Clinic Settings")
    clinic_name = st.text_input("Clinic Name", value="Ayurvedic Wellness Clinic", key="clinic_name")
    clinic_city = st.text_input("City", value="Bengaluru", key="clinic_city")
    specialties = st.multiselect(
        "Specialties",
        ["Panchakarma", "Prakriti Analysis", "Skin Care", "Weight Management",
         "Stress Relief", "Joint Care", "Digestive Health", "Hair Treatment",
         "Infertility", "Respiratory Care"],
        default=["Panchakarma", "Prakriti Analysis", "Skin Care"],
        key="specialties",
    )

    st.markdown("---")

    # Workflow Triggers
    st.markdown("### ▶️ Run Workflows")
    col1, col2 = st.columns(2)
    with col1:
        daily_btn = st.button("🌅 Daily", use_container_width=True, type="primary")
    with col2:
        weekly_btn = st.button("📅 Weekly", use_container_width=True)
    col3, col4 = st.columns(2)
    with col3:
        review_btn = st.button("🛡️ Reviews", use_container_width=True)
    with col4:
        monthly_btn = st.button("📊 Monthly", use_container_width=True)

    if any([daily_btn, weekly_btn, review_btn, monthly_btn]):
        mode = "daily" if daily_btn else "weekly" if weekly_btn else "review-scan" if review_btn else "monthly"
        st.session_state["run_mode"] = mode

    st.markdown("---")

    # Integration Status
    st.markdown("### 🔌 Integrations")
    api_checks = {
        "WhatsApp": "WHATSAPP_ACCESS_TOKEN",
        "Google Business": "GOOGLE_SERVICE_ACCOUNT_JSON",
        "Meta (IG/FB)": "META_ACCESS_TOKEN",
        "SendGrid": "SENDGRID_API_KEY",
        "Google Analytics": "GA_PROPERTY_ID",
        "Google Ads": "GOOGLE_ADS_CUSTOMER_ID",
        "Practo": "PRACTO_DOCTOR_URL",
        "Razorpay": "RAZORPAY_KEY_ID",
        "YouTube": "YOUTUBE_CHANNEL_ID",
        "OpenAI (Images)": "OPENAI_API_KEY",
    }
    connected = 0
    for api_name, env_key in api_checks.items():
        is_connected = check_api_status(env_key)
        if is_connected:
            connected += 1
        icon = "🟢" if is_connected else "🔴"
        st.markdown(f"{icon} {api_name}")

    st.caption(f"{connected}/{len(api_checks)} connected")


# ─── Main Content ───
st.markdown("# 🪷 Ayurvedic Marketing Agents")
st.markdown(f"*Multi-agent AI system for **{clinic_name}**, {clinic_city}*")

# ─── Navigation Tabs ───
tab_dashboard, tab_agents, tab_flow, tab_content, tab_reviews, tab_logs = st.tabs([
    "📊 Dashboard", "🤖 Agents", "🔄 Data Flow", "📝 Content", "⭐ Reviews", "📋 Logs"
])


# ═══════════════════════════════════════
# TAB 1: DASHBOARD
# ═══════════════════════════════════════
with tab_dashboard:
    st.markdown("### Marketing Performance")

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Website Visits (7d)", "1,247", "+12%")
    m2.metric("Google Reviews", "4.6 ★ (89)", "+3")
    m3.metric("Practo Reviews", "4.4 ★ (42)", "+5")
    m4.metric("Social Engagement", "2.3K", "+18%")
    m5.metric("Revenue (30d)", "₹1,84,500", "+22%")

    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.markdown("### Traffic Sources")
        traffic_data = pd.DataFrame({
            "Source": ["Google Organic", "Practo", "Direct", "Social Media", "Google Ads", "WhatsApp", "Email", "YouTube"],
            "Sessions": [480, 320, 290, 210, 180, 145, 78, 44],
        })
        fig = px.bar(
            traffic_data.sort_values("Sessions", ascending=True),
            x="Sessions", y="Source", orientation="h",
            color_discrete_sequence=["#5B7C4F"],
        )
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Nunito Sans", size=12),
            margin=dict(l=0, r=20, t=10, b=0),
            height=300,
            yaxis=dict(title=""),
            xaxis=dict(title="Sessions"),
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_chart2:
        st.markdown("### Patient Acquisition Funnel")
        funnel_data = pd.DataFrame({
            "Stage": ["Website Visit", "Treatment Page", "Contact / Call", "Booking", "Treatment Done", "Review Left"],
            "Count": [1247, 543, 198, 67, 52, 31],
        })
        fig2 = go.Figure(go.Funnel(
            y=funnel_data["Stage"], x=funnel_data["Count"],
            marker=dict(color=["#5B7C4F", "#6B8C5F", "#B8860B", "#8B4513", "#4A3B6B", "#6B5B8B"]),
            textinfo="value+percent initial",
        ))
        fig2.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Nunito Sans", size=12),
            margin=dict(l=0, r=0, t=10, b=0),
            height=300,
        )
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    col_rev, col_ads = st.columns(2)

    with col_rev:
        st.markdown("### Revenue Trend (Razorpay)")
        dates = pd.date_range(end=datetime.now(), periods=30, freq="D")
        import random
        random.seed(42)
        revenue = [random.randint(3000, 12000) for _ in range(30)]
        rev_df = pd.DataFrame({"Date": dates, "Revenue (₹)": revenue})
        fig3 = px.area(rev_df, x="Date", y="Revenue (₹)", color_discrete_sequence=["#B8860B"])
        fig3.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Nunito Sans", size=12),
            margin=dict(l=0, r=0, t=10, b=0), height=250,
        )
        st.plotly_chart(fig3, use_container_width=True)

    with col_ads:
        st.markdown("### Google Ads Performance")
        ads_data = pd.DataFrame({
            "Campaign": ["Panchakarma", "Skin Care", "Weight Mgmt", "Brand"],
            "Spend (₹)": [4500, 3200, 2100, 1800],
            "Conversions": [12, 8, 5, 3],
        })
        ads_data["CPA (₹)"] = (ads_data["Spend (₹)"] / ads_data["Conversions"]).round(0).astype(int)
        st.dataframe(ads_data, use_container_width=True, hide_index=True)


# ═══════════════════════════════════════
# TAB 2: AGENTS
# ═══════════════════════════════════════
with tab_agents:
    st.markdown("### Agent System Overview")
    st.markdown(f"4 specialized AI agents managing marketing for **{clinic_name}**")

    for agent_id, agent in AGENTS.items():
        st.markdown(f"""
        <div class="agent-card" style="border-left-color: {agent['color']}">
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div>
                    <span style="font-size: 28px;">{agent['emoji']}</span>
                    <span style="font-size: 22px; font-weight: 700; color: {agent['color']}; font-family: 'Cormorant Garamond', serif; margin-left: 10px;">
                        {agent['name']}
                    </span>
                    <span style="font-size: 14px; color: #8B7D6B; margin-left: 8px;">
                        ({agent['sanskrit']})
                    </span>
                </div>
                <div style="font-size: 11px; color: #8B7D6B; letter-spacing: 1px; text-transform: uppercase; padding-top: 8px;">
                    {agent['role']}
                </div>
            </div>
            <p style="color: #5A5044; margin: 10px 0; font-family: 'Nunito Sans', sans-serif; font-size: 14px;">
                {agent['description']}
            </p>
            <div style="margin-top: 8px;">
                {''.join(f'<span class="{agent["badge_class"]}">{t}</span>' for t in agent['tools'])}
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.expander(f"📋 {agent['name']} — Priority Tasks"):
            for task in agent["tasks"]:
                st.markdown(f"- {task}")

    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
    st.markdown("### 🔌 All Integrations (12 Tools)")

    for category, tools in INTEGRATIONS.items():
        st.markdown(f"**{category} Integrations**")
        cols = st.columns(6)
        for i, tool in enumerate(tools):
            with cols[i]:
                st.markdown(f"""
                <div style="text-align: center; padding: 12px; background: white; border-radius: 10px;
                     border: 1px solid #E8E0D4; margin-bottom: 8px;">
                    <div style="font-size: 24px;">{tool['icon']}</div>
                    <div style="font-size: 12px; color: #5A5044; font-family: 'Nunito Sans', sans-serif; margin-top: 4px;">
                        {tool['name']}
                    </div>
                </div>
                """, unsafe_allow_html=True)


# ═══════════════════════════════════════
# TAB 3: DATA FLOW
# ═══════════════════════════════════════
with tab_flow:
    st.markdown("### Inter-Agent Data Flow")
    st.markdown("Each connection represents a continuous data pipeline between agents.")

    for flow in DATA_FLOWS:
        from_agent = AGENTS[flow["from"]]
        to_agent = AGENTS[flow["to"]]
        st.markdown(f"""
        <div style="display: flex; align-items: center; gap: 10px; padding: 8px 0;
             border-bottom: 1px solid #F0EBE3; font-family: 'Nunito Sans', sans-serif;">
            <div style="background: {from_agent['color']}15; border: 1px solid {from_agent['color']}40;
                 border-radius: 6px; padding: 4px 12px; font-size: 13px; font-weight: 600;
                 color: {from_agent['color']}; min-width: 160px; text-align: center;">
                {from_agent['emoji']} {from_agent['name']}
            </div>
            <div style="color: #C4B8A8; font-size: 18px;">→</div>
            <div style="flex: 1; font-size: 13px; color: #5A5044; font-style: italic;">
                {flow['label']}
            </div>
            <div style="color: #C4B8A8; font-size: 18px;">→</div>
            <div style="background: {to_agent['color']}15; border: 1px solid {to_agent['color']}40;
                 border-radius: 6px; padding: 4px 12px; font-size: 13px; font-weight: 600;
                 color: {to_agent['color']}; min-width: 160px; text-align: center;">
                {to_agent['emoji']} {to_agent['name']}
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

    st.markdown("### 🔄 Orchestration Cycles")
    cycles = [
        {"cycle": "Hourly", "icon": "⏰", "desc": "Reputation Guard scans Google + Practo for new reviews"},
        {"cycle": "Daily", "icon": "🌅", "desc": "Content Sage creates → Community Weaver distributes → Reviews monitored"},
        {"cycle": "Weekly", "icon": "📅", "desc": "Insight Oracle analyzes all data → strategy brief → adjusts all agents"},
        {"cycle": "Monthly", "icon": "📊", "desc": "Full performance review → budget reallocation → content calendar refresh"},
        {"cycle": "Seasonal", "icon": "🍃", "desc": "Ritucharya alignment → seasonal treatments → dosha-specific campaigns"},
    ]
    for cycle in cycles:
        col_icon, col_text = st.columns([1, 11])
        with col_icon:
            st.markdown(f"<div style='font-size: 28px; text-align: center;'>{cycle['icon']}</div>", unsafe_allow_html=True)
        with col_text:
            st.markdown(f"**{cycle['cycle']}** — {cycle['desc']}")


# ═══════════════════════════════════════
# TAB 4: CONTENT QUEUE
# ═══════════════════════════════════════
with tab_content:
    st.markdown("### Content Queue")
    st.info("Content Sage generates content here. Run the **Daily** workflow to populate with real data.")

    content_items = [
        {"type": "📸 Instagram", "title": "5 Morning Dinacharya Rituals for Vata Season", "status": "✅ Ready", "scheduled": "Tomorrow 9:00 AM", "image": "AI Generated"},
        {"type": "📘 Facebook", "title": "Understanding Your Prakriti — Free Assessment Saturday", "status": "✅ Ready", "scheduled": "Today 6:00 PM", "image": "AI Generated"},
        {"type": "📝 Blog", "title": f"Panchakarma in {clinic_city}: Complete Guide to Detox Therapy", "status": "📝 Outline", "scheduled": "Thursday", "image": "—"},
        {"type": "🎬 Reel", "title": "3 Ayurvedic Herbs You Already Have in Your Kitchen", "status": "📄 Script Ready", "scheduled": "Wednesday", "image": "—"},
        {"type": "▶️ YouTube", "title": "What is Panchakarma? Complete Treatment Explained", "status": "📄 Script Ready", "scheduled": "Friday", "image": "Thumbnail"},
        {"type": "📸 Instagram", "title": "Seasonal Ritucharya: What to Eat This Month", "status": "⏳ Draft", "scheduled": "Saturday", "image": "AI Generated"},
    ]

    header_cols = st.columns([1, 4, 1, 2, 1])
    header_cols[0].markdown("**Type**")
    header_cols[1].markdown("**Title**")
    header_cols[2].markdown("**Status**")
    header_cols[3].markdown("**Scheduled**")
    header_cols[4].markdown("**Visual**")

    for item in content_items:
        cols = st.columns([1, 4, 1, 2, 1])
        cols[0].write(item["type"])
        cols[1].write(item["title"])
        cols[2].write(item["status"])
        cols[3].write(f"📅 {item['scheduled']}")
        cols[4].write(item["image"])


# ═══════════════════════════════════════
# TAB 5: REVIEWS
# ═══════════════════════════════════════
with tab_reviews:
    st.markdown("### Review Monitor")

    col_google, col_practo = st.columns(2)

    with col_google:
        st.markdown("#### ⭐ Google Reviews")
        google_reviews = [
            {"stars": 5, "text": "Amazing Panchakarma experience! Dr. was very thorough and caring.", "replied": True, "date": "2 days ago"},
            {"stars": 4, "text": "Good treatment, but waiting time was a bit long.", "replied": False, "date": "3 days ago"},
            {"stars": 2, "text": "Expensive compared to other clinics in the area.", "replied": False, "date": "5 days ago"},
        ]
        for rev in google_reviews:
            stars_display = "⭐" * rev["stars"]
            status = "✅ Replied" if rev["replied"] else "⏳ Pending"
            border_color = "#2E7D32" if rev["replied"] else ("#C62828" if rev["stars"] <= 2 else "#B8860B")
            urgent = "🚨 " if rev["stars"] <= 2 else ""
            st.markdown(f"""
            <div class="agent-card" style="border-left-color: {border_color}; padding: 14px 16px;">
                <strong>{urgent}{stars_display}</strong> — <span style="color: #8B7D6B;">{rev['date']}</span> — {status}<br>
                <span style="color: #5A5044; font-family: 'Nunito Sans', sans-serif; font-size: 13px;">{rev['text']}</span>
            </div>
            """, unsafe_allow_html=True)

    with col_practo:
        st.markdown("#### 🏥 Practo Reviews")
        practo_reviews = [
            {"stars": 5, "text": "Best Ayurvedic doctor in Bengaluru. Highly recommend for skin issues.", "replied": True, "date": "1 day ago"},
            {"stars": 5, "text": "Very knowledgeable about Prakriti analysis. Changed my lifestyle completely.", "replied": True, "date": "4 days ago"},
            {"stars": 3, "text": "Treatment was okay, but I expected faster results.", "replied": False, "date": "6 days ago"},
        ]
        for rev in practo_reviews:
            stars_display = "⭐" * rev["stars"]
            status = "✅ Replied" if rev["replied"] else "⏳ Pending"
            border_color = "#2E7D32" if rev["replied"] else ("#C62828" if rev["stars"] <= 2 else "#B8860B")
            st.markdown(f"""
            <div class="agent-card" style="border-left-color: {border_color}; padding: 14px 16px;">
                <strong>{stars_display}</strong> — <span style="color: #8B7D6B;">{rev['date']}</span> — {status}<br>
                <span style="color: #5A5044; font-family: 'Nunito Sans', sans-serif; font-size: 13px;">{rev['text']}</span>
            </div>
            """, unsafe_allow_html=True)


# ═══════════════════════════════════════
# TAB 6: LOGS
# ═══════════════════════════════════════
with tab_logs:
    st.markdown("### Agent Run Logs")
    outputs = load_recent_outputs()
    if outputs:
        for output in outputs:
            with st.expander(
                f"📄 {output.get('mode', 'unknown')} — {output.get('timestamp', 'N/A')}"
            ):
                st.json(output)
    else:
        st.info("No agent runs yet. Use the sidebar to trigger a workflow. Logs will appear here after execution.")

    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
    st.markdown("### 🖥️ Run Agents Locally")
    st.code("""# Install dependencies
pip install -r requirements.txt

# Configure API keys
cp .env.example .env
# Edit .env with your keys

# Run daily workflow
python main.py daily

# Run weekly strategy
python main.py weekly

# Quick review scan
python main.py review-scan

# Launch this dashboard locally
streamlit run app.py""", language="bash")


# ─── Run Executor ───
if "run_mode" in st.session_state:
    mode = st.session_state.pop("run_mode")
    st.toast(f"🚀 Triggered **{mode}** workflow!")
    st.sidebar.success(
        f"To execute the **{mode}** workflow, run:\n\n"
        f"`python main.py {mode}`\n\n"
        f"Results will appear in the **Logs** tab."
    )
