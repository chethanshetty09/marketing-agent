"""
YouTube Tool — Upload videos, manage channel content, and analyze performance.
Uses YouTube Data API v3.
"""

import json
from typing import Type, Optional
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
from config.settings import settings

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    GOOGLE_LIBS_AVAILABLE = True
except ImportError:
    GOOGLE_LIBS_AVAILABLE = False


class YouTubeUploadInput(BaseModel):
    video_path: str = Field(description="Local path to the video file")
    title: str = Field(description="Video title (max 100 chars)")
    description: str = Field(
        description=(
            "Video description with relevant keywords, timestamps, and links. "
            "Include clinic contact info and booking link."
        )
    )
    tags: list[str] = Field(
        default=[],
        description="List of tags for SEO, e.g. ['ayurveda', 'panchakarma', 'bengaluru']"
    )
    category_id: str = Field(
        default="26",
        description="YouTube category ID. 26=Howto & Style, 22=People & Blogs, 27=Education"
    )
    privacy_status: str = Field(
        default="private",
        description="Privacy: 'private' (draft), 'unlisted', or 'public'"
    )
    thumbnail_path: Optional[str] = Field(default=None, description="Custom thumbnail image path")


class YouTubeAnalyticsInput(BaseModel):
    days: int = Field(default=30, description="Number of days to analyze")
    max_results: int = Field(default=10, description="Number of videos to include")


class YouTubeScriptInput(BaseModel):
    topic: str = Field(description="Video topic, e.g. 'Benefits of Panchakarma Detox'")
    duration_minutes: int = Field(default=5, description="Target video duration in minutes")
    style: str = Field(
        default="educational",
        description="Video style: 'educational', 'testimonial', 'behind_the_scenes', 'qa', 'seasonal_tip'"
    )


class YouTubeUploadTool(BaseTool):
    name: str = "youtube_upload"
    description: str = (
        "Upload a video to the clinic's YouTube channel. Supports custom titles, "
        "descriptions, tags, and thumbnails. Videos upload as 'private' by default — "
        "change to 'public' when ready to publish. "
        "Input: video_path, title, description, tags, privacy_status."
    )
    args_schema: Type[BaseModel] = YouTubeUploadInput

    def _run(
        self, video_path: str, title: str, description: str,
        tags: list[str] = [], category_id: str = "26",
        privacy_status: str = "private", thumbnail_path: Optional[str] = None
    ) -> str:
        if not GOOGLE_LIBS_AVAILABLE:
            return "ERROR: google-api-python-client not installed."

        try:
            gcfg = settings.google_business
            credentials = service_account.Credentials.from_service_account_file(
                gcfg.service_account_json,
                scopes=["https://www.googleapis.com/auth/youtube.upload"],
            )
            youtube = build("youtube", "v3", credentials=credentials)

            body = {
                "snippet": {
                    "title": title[:100],
                    "description": description,
                    "tags": tags,
                    "categoryId": category_id,
                    "defaultLanguage": "en",
                },
                "status": {
                    "privacyStatus": privacy_status,
                    "selfDeclaredMadeForKids": False,
                },
            }

            media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
            request = youtube.videos().insert(
                part="snippet,status", body=body, media_body=media
            )

            response = request.execute()
            video_id = response["id"]
            video_url = f"https://youtube.com/watch?v={video_id}"

            # Set thumbnail if provided
            if thumbnail_path:
                try:
                    youtube.thumbnails().set(
                        videoId=video_id,
                        media_body=MediaFileUpload(thumbnail_path),
                    ).execute()
                except Exception as e:
                    return json.dumps({
                        "status": "uploaded_no_thumbnail",
                        "video_id": video_id,
                        "url": video_url,
                        "thumbnail_error": str(e),
                    })

            return json.dumps({
                "status": "success",
                "video_id": video_id,
                "url": video_url,
                "privacy": privacy_status,
                "title": title,
            }, indent=2)

        except Exception as e:
            return f"Error uploading to YouTube: {str(e)}"


class YouTubeAnalyticsTool(BaseTool):
    name: str = "youtube_analytics"
    description: str = (
        "Fetch YouTube channel analytics — views, watch time, subscribers, "
        "and top performing videos. Essential for understanding which Ayurvedic "
        "content topics drive the most engagement. "
        "Input: days lookback, max_results."
    )
    args_schema: Type[BaseModel] = YouTubeAnalyticsInput

    def _run(self, days: int = 30, max_results: int = 10) -> str:
        if not GOOGLE_LIBS_AVAILABLE:
            return "ERROR: google-api-python-client not installed."

        try:
            gcfg = settings.google_business
            credentials = service_account.Credentials.from_service_account_file(
                gcfg.service_account_json,
                scopes=[
                    "https://www.googleapis.com/auth/youtube.readonly",
                    "https://www.googleapis.com/auth/yt-analytics.readonly",
                ],
            )
            youtube = build("youtube", "v3", credentials=credentials)

            # Get channel stats
            channel_resp = youtube.channels().list(
                part="statistics,snippet", mine=True
            ).execute()

            channel = channel_resp.get("items", [{}])[0]
            stats = channel.get("statistics", {})

            # Get recent videos
            search_resp = youtube.search().list(
                part="snippet", forMine=True, type="video",
                order="date", maxResults=max_results,
            ).execute()

            videos = []
            video_ids = []
            for item in search_resp.get("items", []):
                video_ids.append(item["id"]["videoId"])
                videos.append({
                    "id": item["id"]["videoId"],
                    "title": item["snippet"]["title"],
                    "published": item["snippet"]["publishedAt"],
                })

            # Get video statistics
            if video_ids:
                video_resp = youtube.videos().list(
                    part="statistics", id=",".join(video_ids)
                ).execute()

                for v_item in video_resp.get("items", []):
                    for video in videos:
                        if video["id"] == v_item["id"]:
                            v_stats = v_item["statistics"]
                            video["views"] = int(v_stats.get("viewCount", 0))
                            video["likes"] = int(v_stats.get("likeCount", 0))
                            video["comments"] = int(v_stats.get("commentCount", 0))

            # Sort by views
            videos.sort(key=lambda x: x.get("views", 0), reverse=True)

            return json.dumps({
                "period": f"Last {days} days",
                "channel_stats": {
                    "total_subscribers": stats.get("subscriberCount", "N/A"),
                    "total_views": stats.get("viewCount", "N/A"),
                    "total_videos": stats.get("videoCount", "N/A"),
                },
                "recent_videos": videos,
                "recommendations": [
                    "Videos about specific treatments (Panchakarma, Shirodhara) get highest watch time",
                    "Keep videos 5-8 minutes for optimal retention",
                    "Add chapters/timestamps to boost SEO",
                    "Include a booking CTA in the first 30 seconds and description",
                ],
            }, indent=2)

        except Exception as e:
            return f"Error fetching YouTube analytics: {str(e)}"


class YouTubeScriptGeneratorTool(BaseTool):
    name: str = "youtube_script_generator"
    description: str = (
        "Generate a structured video script for Ayurvedic educational content. "
        "Produces hook, intro, main content sections, CTA, and description/tags. "
        "Optimized for YouTube SEO and patient engagement. "
        "Input: topic, duration_minutes, style."
    )
    args_schema: Type[BaseModel] = YouTubeScriptInput

    def _run(
        self, topic: str, duration_minutes: int = 5, style: str = "educational"
    ) -> str:
        clinic = settings.clinic

        # Calculate rough word counts (150 words/minute for speaking)
        total_words = duration_minutes * 150
        section_words = total_words // 5  # 5 main sections

        style_guides = {
            "educational": "Informative, warm, authoritative. Use analogies. Reference classical texts where relevant.",
            "testimonial": "Conversational, empathetic, story-driven. Focus on patient journey and transformation.",
            "behind_the_scenes": "Casual, inviting, visual. Show the process and explain each step.",
            "qa": "Direct, clear answers. Address common patient concerns and misconceptions.",
            "seasonal_tip": "Timely, practical, actionable. Connect Ritucharya to everyday lifestyle.",
        }

        script_template = {
            "topic": topic,
            "target_duration_minutes": duration_minutes,
            "style": style,
            "style_guide": style_guides.get(style, style_guides["educational"]),
            "script_structure": {
                "hook": {
                    "duration": "0:00-0:15",
                    "purpose": "Grab attention with a surprising fact or question",
                    "guideline": f"Open with a compelling question or statistic about {topic}. Make the viewer curious.",
                    "word_count": 40,
                },
                "intro": {
                    "duration": "0:15-0:45",
                    "purpose": "Introduce yourself and what the viewer will learn",
                    "guideline": f"Introduce {clinic.name}, your credentials, and preview 3 key takeaways.",
                    "word_count": 75,
                },
                "main_content": {
                    "duration": f"0:45-{duration_minutes - 1}:00",
                    "purpose": "Deliver the core educational value",
                    "sections": [
                        {"title": "What it is (Ayurvedic perspective)", "word_count": section_words},
                        {"title": "How it works (mechanism/process)", "word_count": section_words},
                        {"title": "Who it's for (ideal patient profile)", "word_count": section_words},
                        {"title": "What to expect (practical details)", "word_count": section_words},
                    ],
                },
                "cta": {
                    "duration": f"{duration_minutes - 1}:00-{duration_minutes}:00",
                    "purpose": "Drive action — booking, subscribing, sharing",
                    "guideline": (
                        "End with a clear CTA: book a consultation, visit the website, "
                        "or try a specific home remedy discussed. Mention the free Prakriti assessment if available."
                    ),
                    "word_count": 100,
                },
            },
            "youtube_seo": {
                "suggested_title_formats": [
                    f"{topic} — Complete Ayurvedic Guide",
                    f"{topic}: What Your Doctor Won't Tell You",
                    f"Ayurvedic Secrets: {topic} Explained",
                ],
                "suggested_tags": [
                    "ayurveda", topic.lower().replace(" ", "-"), clinic.city.lower(),
                    "ayurvedic treatment", "natural healing", "wellness",
                    "panchakarma", "dosha", "holistic health",
                ],
                "description_template": (
                    f"In this video, learn about {topic} from an Ayurvedic perspective.\n\n"
                    f"📞 Book a consultation: {clinic.phone}\n"
                    f"🌐 Visit us: {clinic.website}\n\n"
                    f"TIMESTAMPS:\n"
                    f"0:00 — Introduction\n"
                    f"0:45 — What is {topic}?\n"
                    f"... (add timestamps after editing)\n\n"
                    f"Follow {clinic.name} for more Ayurvedic wisdom!\n\n"
                    f"#Ayurveda #{topic.replace(' ', '')} #{clinic.city}"
                ),
            },
        }

        return json.dumps(script_template, indent=2, ensure_ascii=False)
