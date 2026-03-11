# 🪷 Ayurvedic Clinic Multi-Agent Marketing System

A production-ready **CrewAI-powered** multi-agent system with real API integrations and a **Streamlit web dashboard** for managing your Ayurvedic clinic's marketing.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                  STREAMLIT DASHBOARD                 │
│         (Control Center + Analytics UI)              │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│              CREWAI ORCHESTRATOR                     │
│     (Manages agent collaboration & task flow)        │
└──┬──────────┬──────────┬──────────┬─────────────────┘
   │          │          │          │
┌──▼───┐  ┌──▼───┐  ┌───▼──┐  ┌───▼──┐
│CONTENT│  │COMM- │  │REPU- │  │INSIGHT│
│ SAGE  │  │UNITY │  │TATION│  │ORACLE │
│      │  │WEAVER│  │GUARD │  │       │
└──┬───┘  └──┬───┘  └──┬───┘  └──┬───┘
   │         │         │         │
┌──▼─────────▼─────────▼─────────▼────────────────────┐
│                   TOOL LAYER                         │
│  WhatsApp API │ Google APIs │ Meta API │ Analytics   │
└─────────────────────────────────────────────────────┘
```

## 📂 Project Structure

```
ayurvedic-agents/
├── main.py                  # Entry point — run the crew
├── agents/
│   ├── __init__.py
│   ├── content_sage.py      # Content creation agent
│   ├── community_weaver.py  # Patient engagement agent
│   ├── reputation_guard.py  # Review management agent
│   └── insight_oracle.py    # Analytics & strategy agent
├── tools/
│   ├── __init__.py
│   ├── whatsapp_tool.py     # WhatsApp Business API
│   ├── google_reviews_tool.py # Google Business Profile
│   ├── social_media_tool.py # Meta (Instagram/Facebook) API
│   ├── seo_tool.py          # Google Search Console + keyword tools
│   ├── analytics_tool.py    # Google Analytics integration
│   └── email_tool.py        # Email (SMTP / SendGrid)
├── config/
│   ├── agents.yaml          # Agent definitions
│   ├── tasks.yaml           # Task definitions
│   └── settings.py          # API keys & config
├── dashboard/
│   └── app.py               # Streamlit web dashboard
├── templates/
│   ├── whatsapp_templates.json
│   └── email_templates.json
├── requirements.txt
├── .env.example
└── README.md
```

## 🚀 Quick Start

### 1. Clone & Install

```bash
cd ayurvedic-agents
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure API Keys

```bash
cp .env.example .env
# Edit .env with your actual API keys
```

### 3. Run the Agent System

```bash
# Run all agents (CLI mode)
python main.py

# Run the web dashboard
streamlit run dashboard/app.py
```

## 🔑 API Keys Required

| Service | Purpose | Get Key |
|---------|---------|---------|
| OpenAI / Anthropic | LLM backbone for agents | platform.openai.com or console.anthropic.com |
| WhatsApp Business | Patient messaging & nurture | developers.facebook.com |
| Google Business Profile | Review monitoring & response | console.cloud.google.com |
| Meta Graph API | Instagram/Facebook posting | developers.facebook.com |
| Google Search Console | SEO tracking | search.google.com/search-console |
| SendGrid | Email campaigns | sendgrid.com |
| Google Analytics | Traffic & conversion data | analytics.google.com |

## 🔄 Agent Orchestration Cycles

- **Hourly**: Reputation Guard scans for new reviews
- **Daily**: Content Sage generates + Community Weaver distributes
- **Weekly**: Insight Oracle produces strategy brief → adjusts all agents
- **Seasonal**: Content calendar rotates for Ritucharya alignment
