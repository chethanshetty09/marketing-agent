"""
Google Business Profile Reviews Tools — fetch reviews, analyze sentiment, reply.
Uses the Google My Business API (Business Profile API).
"""

import json
from typing import Type, Optional
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
from config.settings import settings

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    GOOGLE_LIBS_AVAILABLE = True
except ImportError:
    GOOGLE_LIBS_AVAILABLE = False


def _get_google_service():
    """Build authenticated Google My Business service."""
    cfg = settings.google_business
    credentials = service_account.Credentials.from_service_account_file(
        cfg.service_account_json,
        scopes=["https://www.googleapis.com/auth/business.manage"],
    )
    return build("mybusinessaccountmanagement", "v1", credentials=credentials)


def _get_reviews_service():
    """Build reviews-specific service."""
    cfg = settings.google_business
    credentials = service_account.Credentials.from_service_account_file(
        cfg.service_account_json,
        scopes=["https://www.googleapis.com/auth/business.manage"],
    )
    # The reviews endpoint uses a different API surface
    return build("mybusiness", "v4", credentials=credentials)


class FetchReviewsInput(BaseModel):
    max_results: int = Field(default=20, description="Maximum number of reviews to fetch (1-50)")
    min_rating: Optional[int] = Field(default=None, description="Filter: minimum star rating (1-5)")


class ReplyReviewInput(BaseModel):
    review_id: str = Field(description="The Google review ID to reply to")
    reply_text: str = Field(description="The reply text to post (should be empathetic and professional)")


class GoogleReviewsFetchTool(BaseTool):
    name: str = "google_reviews_fetch"
    description: str = (
        "Fetch recent Google Reviews for the clinic. Returns review text, rating, "
        "reviewer name, and date. Use this to monitor patient sentiment, identify "
        "negative reviews that need responses, and find testimonials to promote. "
        "Input: max_results (default 20), optional min_rating filter."
    )
    args_schema: Type[BaseModel] = FetchReviewsInput

    def _run(self, max_results: int = 20, min_rating: Optional[int] = None) -> str:
        if not GOOGLE_LIBS_AVAILABLE:
            return "ERROR: google-api-python-client not installed. Run: pip install google-api-python-client google-auth-oauthlib"

        cfg = settings.google_business
        if not cfg.service_account_json:
            return "ERROR: Google Business not configured. Set GOOGLE_SERVICE_ACCOUNT_JSON in .env"

        try:
            service = _get_reviews_service()
            location_name = f"accounts/{cfg.account_id}/locations/{cfg.location_id}"

            response = service.accounts().locations().reviews().list(
                parent=location_name,
                pageSize=min(max_results, 50),
            ).execute()

            reviews = response.get("reviews", [])
            if not reviews:
                return "No reviews found for this location."

            results = []
            for rev in reviews:
                rating = rev.get("starRating", "UNKNOWN")
                # Convert enum to number
                rating_map = {"ONE": 1, "TWO": 2, "THREE": 3, "FOUR": 4, "FIVE": 5}
                rating_num = rating_map.get(rating, 0)

                if min_rating and rating_num < min_rating:
                    continue

                review_data = {
                    "review_id": rev.get("reviewId", ""),
                    "reviewer": rev.get("reviewer", {}).get("displayName", "Anonymous"),
                    "rating": rating_num,
                    "text": rev.get("comment", "(no text)"),
                    "create_time": rev.get("createTime", ""),
                    "has_reply": "reviewReply" in rev,
                    "reply_text": rev.get("reviewReply", {}).get("comment", ""),
                }
                results.append(review_data)

            return json.dumps(results, indent=2, ensure_ascii=False)

        except Exception as e:
            return f"Error fetching reviews: {str(e)}"


class GoogleReviewsReplyTool(BaseTool):
    name: str = "google_reviews_reply"
    description: str = (
        "Reply to a Google Review on behalf of the clinic. Use for responding to "
        "both positive reviews (with gratitude) and negative reviews (with empathy "
        "and resolution). The reply should reflect the clinic's compassionate Ayurvedic values. "
        "Input: review_id and reply_text."
    )
    args_schema: Type[BaseModel] = ReplyReviewInput

    def _run(self, review_id: str, reply_text: str) -> str:
        if not GOOGLE_LIBS_AVAILABLE:
            return "ERROR: google-api-python-client not installed."

        cfg = settings.google_business
        if not cfg.service_account_json:
            return "ERROR: Google Business not configured. Set GOOGLE_SERVICE_ACCOUNT_JSON in .env"

        try:
            service = _get_reviews_service()
            review_name = (
                f"accounts/{cfg.account_id}/locations/{cfg.location_id}/reviews/{review_id}"
            )

            service.accounts().locations().reviews().updateReply(
                name=review_name,
                body={"comment": reply_text},
            ).execute()

            return f"Successfully replied to review {review_id}."

        except Exception as e:
            return f"Error replying to review: {str(e)}"
