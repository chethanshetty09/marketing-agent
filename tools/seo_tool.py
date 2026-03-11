"""
SEO Tools — keyword research and Google Search Console analytics.
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


class KeywordResearchInput(BaseModel):
    seed_keywords: list[str] = Field(
        description="List of seed keywords to research, e.g. ['panchakarma treatment', 'ayurvedic doctor']"
    )
    city: Optional[str] = Field(default=None, description="City for local SEO targeting")


class SearchConsoleInput(BaseModel):
    days: int = Field(default=28, description="Number of days to look back (7, 28, 90)")
    dimension: str = Field(
        default="query",
        description="Dimension to group by: 'query', 'page', 'device', or 'country'"
    )
    row_limit: int = Field(default=25, description="Max rows to return")


class KeywordResearchTool(BaseTool):
    name: str = "keyword_research"
    description: str = (
        "Research SEO keywords relevant to Ayurvedic treatments and local search. "
        "Generates keyword ideas with local modifiers based on seed keywords. "
        "Use for content planning, blog topic ideation, and landing page optimization. "
        "Input: seed_keywords list, optional city for local targeting."
    )
    args_schema: Type[BaseModel] = KeywordResearchInput

    def _run(self, seed_keywords: list[str], city: Optional[str] = None) -> str:
        target_city = city or settings.clinic.city

        # Generate keyword variations with local modifiers and long-tail patterns
        # In production, this would call Google Ads Keyword Planner API or SEMrush/Ahrefs API
        keyword_patterns = [
            "{kw} in {city}",
            "best {kw} {city}",
            "{kw} near me",
            "{kw} cost in {city}",
            "{kw} benefits",
            "{kw} treatment",
            "{kw} doctor {city}",
            "ayurvedic {kw}",
            "{kw} side effects",
            "{kw} reviews {city}",
        ]

        results = []
        for seed in seed_keywords:
            keyword_group = {
                "seed": seed,
                "variations": [],
            }
            for pattern in keyword_patterns:
                variation = pattern.format(kw=seed, city=target_city)
                keyword_group["variations"].append({
                    "keyword": variation,
                    "estimated_intent": self._classify_intent(pattern),
                })
            results.append(keyword_group)

        output = {
            "target_city": target_city,
            "keyword_groups": results,
            "recommendation": (
                f"Focus on high-intent local keywords combining treatments with '{target_city}'. "
                f"Create dedicated landing pages for each major treatment + city combination. "
                f"Use long-tail 'cost' and 'review' keywords in FAQ sections."
            ),
            "note": (
                "For actual search volume and competition data, integrate Google Ads "
                "Keyword Planner API or third-party tools like SEMrush/Ahrefs."
            ),
        }

        return json.dumps(output, indent=2)

    @staticmethod
    def _classify_intent(pattern: str) -> str:
        if "cost" in pattern or "near me" in pattern:
            return "transactional"
        elif "benefits" in pattern or "side effects" in pattern:
            return "informational"
        elif "reviews" in pattern or "best" in pattern:
            return "commercial"
        else:
            return "navigational"


class SearchConsoleAnalyticsTool(BaseTool):
    name: str = "search_console_analytics"
    description: str = (
        "Fetch Google Search Console data for the clinic's website. "
        "Returns search queries, impressions, clicks, CTR, and average position. "
        "Use to identify which keywords are driving traffic, which pages need optimization, "
        "and content gaps to fill. "
        "Input: days lookback (7/28/90), dimension (query/page), row_limit."
    )
    args_schema: Type[BaseModel] = SearchConsoleInput

    def _run(
        self, days: int = 28, dimension: str = "query", row_limit: int = 25
    ) -> str:
        if not GOOGLE_LIBS_AVAILABLE:
            return "ERROR: google-api-python-client not installed."

        cfg = settings.analytics
        if not cfg.gsc_site_url:
            return "ERROR: Google Search Console not configured. Set GSC_SITE_URL in .env"

        try:
            gcfg = settings.google_business
            credentials = service_account.Credentials.from_service_account_file(
                gcfg.service_account_json,
                scopes=["https://www.googleapis.com/auth/webmasters.readonly"],
            )
            service = build("searchconsole", "v1", credentials=credentials)

            from datetime import datetime, timedelta
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

            request_body = {
                "startDate": start_date,
                "endDate": end_date,
                "dimensions": [dimension],
                "rowLimit": row_limit,
                "dataState": "final",
            }

            response = service.searchanalytics().query(
                siteUrl=cfg.gsc_site_url, body=request_body
            ).execute()

            rows = response.get("rows", [])
            if not rows:
                return f"No Search Console data found for the last {days} days."

            results = []
            for row in rows:
                results.append({
                    dimension: row["keys"][0],
                    "clicks": row.get("clicks", 0),
                    "impressions": row.get("impressions", 0),
                    "ctr": round(row.get("ctr", 0) * 100, 2),
                    "position": round(row.get("position", 0), 1),
                })

            return json.dumps({
                "period": f"Last {days} days",
                "dimension": dimension,
                "data": results,
            }, indent=2)

        except Exception as e:
            return f"Error fetching Search Console data: {str(e)}"
