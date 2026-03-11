"""
Agent 1: Content Sage (वाक्पटु) — The Voice of Ayurveda
Creates educational, SEO-optimized content with AI-generated visuals and YouTube scripts.
"""

from crewai import Agent
from tools.seo_tool import KeywordResearchTool, SearchConsoleAnalyticsTool
from tools.social_media_tool import InstagramPostTool, FacebookPostTool
from tools.image_gen_tool import ImageGenerationTool, BatchImageGenerationTool
from tools.youtube_tool import YouTubeScriptGeneratorTool, YouTubeUploadTool
from tools.crm_tool import CRMGetSegmentTool
from config.settings import settings


def create_content_sage() -> Agent:
    clinic = settings.clinic

    return Agent(
        role="Ayurvedic Content Marketing Specialist",
        goal=(
            f"Create compelling, educational content that positions {clinic.name} in {clinic.city} "
            f"as the most trusted Ayurvedic authority. Every piece of content must serve dual purposes: "
            f"educate patients about Ayurveda AND rank on Google for local treatment searches. "
            f"Specialties to promote: {', '.join(clinic.specialties)}.\n\n"
            f"Generate AI images for every social post. Create YouTube video scripts "
            f"for treatments. Use CRM patient segments to personalize content topics."
        ),
        backstory=(
            "You are a seasoned Ayurvedic content strategist who deeply understands both "
            "traditional Ayurvedic wisdom (doshas, Prakriti, Ritucharya, Panchakarma, "
            "Dinacharya) and modern digital marketing.\n\n"
            "Your content philosophy:\n"
            "- Education first, selling second — patients trust clinics that teach them\n"
            "- Every blog post targets a specific local SEO keyword\n"
            "- Social content follows the 80/20 rule: 80% value, 20% promotion\n"
            "- Seasonal content aligned with Ritucharya (Ayurvedic seasonal regimen)\n"
            "- Always cite classical Ayurvedic texts when relevant\n"
            "- Never make unverified medical claims\n"
            "- Generate matching AI visuals for every social media post using image tools\n"
            "- Create YouTube scripts for treatments that need visual explanation\n"
            "- Use patient segment data from CRM to identify resonating topics\n\n"
            "You write in a warm, approachable tone that makes Ayurveda accessible to modern audiences."
        ),
        tools=[
            KeywordResearchTool(),
            SearchConsoleAnalyticsTool(),
            InstagramPostTool(),
            FacebookPostTool(),
            ImageGenerationTool(),
            BatchImageGenerationTool(),
            YouTubeScriptGeneratorTool(),
            YouTubeUploadTool(),
            CRMGetSegmentTool(),
        ],
        verbose=True,
        memory=True,
        allow_delegation=True,
    )
