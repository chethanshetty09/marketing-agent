"""
Social Media Tools — post to Instagram and Facebook via Meta Graph API.
Supports text posts, image posts, and carousel posts.
"""

import json
import httpx
from typing import Type, Optional
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
from config.settings import settings


class InstagramPostInput(BaseModel):
    image_url: str = Field(description="Public URL of the image to post")
    caption: str = Field(description="Post caption including hashtags (max 2200 chars)")
    location_id: Optional[str] = Field(default=None, description="Facebook location ID for geotagging")


class FacebookPostInput(BaseModel):
    message: str = Field(description="Post text content")
    link: Optional[str] = Field(default=None, description="Optional URL to include in the post")
    image_url: Optional[str] = Field(default=None, description="Optional public image URL to attach")


class InstagramPostTool(BaseTool):
    name: str = "instagram_post"
    description: str = (
        "Publish a photo post to the clinic's Instagram account. "
        "Requires a public image URL and caption text. Good for treatment showcases, "
        "Ayurvedic tips carousels, herb spotlights, and clinic ambiance posts. "
        "Input: image_url (must be publicly accessible), caption (with hashtags)."
    )
    args_schema: Type[BaseModel] = InstagramPostInput

    def _run(
        self, image_url: str, caption: str, location_id: Optional[str] = None
    ) -> str:
        cfg = settings.meta
        if not cfg.access_token:
            return "ERROR: Meta API not configured. Set META_ACCESS_TOKEN in .env"

        api = cfg.api_url

        try:
            # Step 1: Create media container
            container_url = f"{api}/{cfg.instagram_account_id}/media"
            container_params = {
                "image_url": image_url,
                "caption": caption,
                "access_token": cfg.access_token,
            }
            if location_id:
                container_params["location_id"] = location_id

            resp = httpx.post(container_url, params=container_params, timeout=60)
            resp.raise_for_status()
            container_id = resp.json().get("id")

            if not container_id:
                return "Error: Failed to create media container."

            # Step 2: Publish the container
            publish_url = f"{api}/{cfg.instagram_account_id}/media_publish"
            publish_params = {
                "creation_id": container_id,
                "access_token": cfg.access_token,
            }

            resp = httpx.post(publish_url, params=publish_params, timeout=60)
            resp.raise_for_status()
            post_id = resp.json().get("id")

            return f"Instagram post published successfully! Post ID: {post_id}"

        except httpx.HTTPStatusError as e:
            return f"Instagram API error ({e.response.status_code}): {e.response.text}"
        except Exception as e:
            return f"Failed to post to Instagram: {str(e)}"


class FacebookPostTool(BaseTool):
    name: str = "facebook_post"
    description: str = (
        "Publish a post to the clinic's Facebook Page. Supports text, links, and images. "
        "Good for article sharing, event announcements, patient education, and clinic updates. "
        "Input: message text, optional link URL, optional image_url."
    )
    args_schema: Type[BaseModel] = FacebookPostInput

    def _run(
        self, message: str, link: Optional[str] = None, image_url: Optional[str] = None
    ) -> str:
        cfg = settings.meta
        if not cfg.access_token:
            return "ERROR: Meta API not configured. Set META_ACCESS_TOKEN in .env"

        api = cfg.api_url

        try:
            if image_url:
                # Photo post
                url = f"{api}/{cfg.page_id}/photos"
                params = {
                    "url": image_url,
                    "message": message,
                    "access_token": cfg.access_token,
                }
            else:
                # Text/link post
                url = f"{api}/{cfg.page_id}/feed"
                params = {
                    "message": message,
                    "access_token": cfg.access_token,
                }
                if link:
                    params["link"] = link

            resp = httpx.post(url, params=params, timeout=30)
            resp.raise_for_status()
            post_id = resp.json().get("id") or resp.json().get("post_id")

            return f"Facebook post published successfully! Post ID: {post_id}"

        except httpx.HTTPStatusError as e:
            return f"Facebook API error ({e.response.status_code}): {e.response.text}"
        except Exception as e:
            return f"Failed to post to Facebook: {str(e)}"
