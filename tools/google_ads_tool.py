"""
Google Ads Tool — Manage and analyze paid search campaigns.
Uses the Google Ads API for campaign performance data and budget management.
"""

import json
from typing import Type, Optional
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
from config.settings import settings

try:
    from google.ads.googleads.client import GoogleAdsClient
    GADS_AVAILABLE = True
except ImportError:
    GADS_AVAILABLE = False


class CampaignPerformanceInput(BaseModel):
    days: int = Field(default=30, description="Number of days to look back")
    campaign_name_filter: Optional[str] = Field(
        default=None, description="Filter by campaign name (partial match)"
    )


class KeywordPerformanceInput(BaseModel):
    days: int = Field(default=30, description="Number of days to look back")
    min_impressions: int = Field(default=10, description="Minimum impressions to include")


class AdCopyInput(BaseModel):
    headlines: list[str] = Field(
        description="List of ad headlines (max 30 chars each, provide 3-15)"
    )
    descriptions: list[str] = Field(
        description="List of ad descriptions (max 90 chars each, provide 2-4)"
    )
    final_url: str = Field(description="Landing page URL for the ad")
    campaign_name: str = Field(description="Target campaign name")


class BudgetRecommendationInput(BaseModel):
    days: int = Field(default=30, description="Analysis period in days")
    target_cpa: Optional[float] = Field(
        default=None, description="Target cost per acquisition in INR"
    )


class GoogleAdsCampaignPerformanceTool(BaseTool):
    name: str = "google_ads_campaign_performance"
    description: str = (
        "Fetch Google Ads campaign performance metrics — spend, clicks, impressions, "
        "CTR, CPC, conversions, and cost per conversion. Essential for the Insight Oracle "
        "to understand paid channel ROI. "
        "Input: days lookback, optional campaign_name_filter."
    )
    args_schema: Type[BaseModel] = CampaignPerformanceInput

    def _run(self, days: int = 30, campaign_name_filter: Optional[str] = None) -> str:
        gads_config = {
            "customer_id": settings.google_ads.customer_id if hasattr(settings, 'google_ads') else "",
            "developer_token": settings.google_ads.developer_token if hasattr(settings, 'google_ads') else "",
        }

        if not gads_config["customer_id"]:
            return "ERROR: Google Ads not configured. Set GOOGLE_ADS_CUSTOMER_ID in .env"

        if not GADS_AVAILABLE:
            return "ERROR: google-ads not installed. Run: pip install google-ads"

        try:
            client = GoogleAdsClient.load_from_dict({
                "developer_token": gads_config["developer_token"],
                "client_id": "",
                "client_secret": "",
                "refresh_token": "",
                "login_customer_id": gads_config["customer_id"],
            })

            ga_service = client.get_service("GoogleAdsService")

            query = f"""
                SELECT
                    campaign.name,
                    campaign.status,
                    metrics.impressions,
                    metrics.clicks,
                    metrics.ctr,
                    metrics.average_cpc,
                    metrics.cost_micros,
                    metrics.conversions,
                    metrics.cost_per_conversion
                FROM campaign
                WHERE segments.date DURING LAST_{days}_DAYS
                    AND campaign.status != 'REMOVED'
                ORDER BY metrics.cost_micros DESC
            """

            response = ga_service.search(
                customer_id=gads_config["customer_id"], query=query
            )

            campaigns = []
            for row in response:
                campaign_data = {
                    "name": row.campaign.name,
                    "status": row.campaign.status.name,
                    "impressions": row.metrics.impressions,
                    "clicks": row.metrics.clicks,
                    "ctr": round(row.metrics.ctr * 100, 2),
                    "avg_cpc_inr": round(row.metrics.average_cpc / 1_000_000, 2),
                    "total_spend_inr": round(row.metrics.cost_micros / 1_000_000, 2),
                    "conversions": round(row.metrics.conversions, 1),
                    "cost_per_conversion_inr": (
                        round(row.metrics.cost_per_conversion / 1_000_000, 2)
                        if row.metrics.conversions > 0 else None
                    ),
                }

                if campaign_name_filter:
                    if campaign_name_filter.lower() in campaign_data["name"].lower():
                        campaigns.append(campaign_data)
                else:
                    campaigns.append(campaign_data)

            total_spend = sum(c["total_spend_inr"] for c in campaigns)
            total_conversions = sum(c["conversions"] for c in campaigns)

            return json.dumps({
                "period": f"Last {days} days",
                "total_spend_inr": round(total_spend, 2),
                "total_conversions": round(total_conversions, 1),
                "avg_cpa_inr": round(total_spend / total_conversions, 2) if total_conversions > 0 else None,
                "campaigns": campaigns,
            }, indent=2)

        except Exception as e:
            return f"Error fetching Google Ads data: {str(e)}"


class GoogleAdsKeywordPerformanceTool(BaseTool):
    name: str = "google_ads_keyword_performance"
    description: str = (
        "Fetch keyword-level performance data from Google Ads. Shows which search terms "
        "are driving clicks and conversions, and which are wasting budget. "
        "Critical for optimizing ad spend on high-intent Ayurvedic treatment keywords. "
        "Input: days lookback, min_impressions filter."
    )
    args_schema: Type[BaseModel] = KeywordPerformanceInput

    def _run(self, days: int = 30, min_impressions: int = 10) -> str:
        gads_config = {
            "customer_id": settings.google_ads.customer_id if hasattr(settings, 'google_ads') else "",
        }
        if not gads_config["customer_id"]:
            return "ERROR: Google Ads not configured. Set GOOGLE_ADS_CUSTOMER_ID in .env"

        if not GADS_AVAILABLE:
            return "ERROR: google-ads not installed. Run: pip install google-ads"

        try:
            client = GoogleAdsClient.load_from_dict({
                "developer_token": "",
                "login_customer_id": gads_config["customer_id"],
            })

            ga_service = client.get_service("GoogleAdsService")

            query = f"""
                SELECT
                    search_term_view.search_term,
                    campaign.name,
                    metrics.impressions,
                    metrics.clicks,
                    metrics.ctr,
                    metrics.average_cpc,
                    metrics.cost_micros,
                    metrics.conversions
                FROM search_term_view
                WHERE segments.date DURING LAST_{days}_DAYS
                    AND metrics.impressions >= {min_impressions}
                ORDER BY metrics.conversions DESC, metrics.clicks DESC
                LIMIT 50
            """

            response = ga_service.search(
                customer_id=gads_config["customer_id"], query=query
            )

            keywords = []
            for row in response:
                keywords.append({
                    "search_term": row.search_term_view.search_term,
                    "campaign": row.campaign.name,
                    "impressions": row.metrics.impressions,
                    "clicks": row.metrics.clicks,
                    "ctr": round(row.metrics.ctr * 100, 2),
                    "avg_cpc_inr": round(row.metrics.average_cpc / 1_000_000, 2),
                    "spend_inr": round(row.metrics.cost_micros / 1_000_000, 2),
                    "conversions": round(row.metrics.conversions, 1),
                })

            # Categorize keywords
            high_performers = [k for k in keywords if k["conversions"] > 0]
            wasted_spend = [
                k for k in keywords
                if k["conversions"] == 0 and k["spend_inr"] > 100
            ]

            return json.dumps({
                "period": f"Last {days} days",
                "total_keywords": len(keywords),
                "high_performers": high_performers[:15],
                "wasted_spend_keywords": wasted_spend[:10],
                "recommendation": (
                    "Increase bids on converting keywords. Add wasted-spend keywords "
                    "as negative keywords or pause them. Focus budget on treatment-specific "
                    "keywords with local intent."
                ),
            }, indent=2)

        except Exception as e:
            return f"Error fetching keyword data: {str(e)}"


class GoogleAdsBudgetRecommendationTool(BaseTool):
    name: str = "google_ads_budget_recommendation"
    description: str = (
        "Analyze Google Ads spend efficiency and recommend budget changes. "
        "Identifies which campaigns to scale up, scale down, or pause. "
        "Provides specific budget recommendations based on CPA targets. "
        "Input: days for analysis period, optional target_cpa in INR."
    )
    args_schema: Type[BaseModel] = BudgetRecommendationInput

    def _run(self, days: int = 30, target_cpa: Optional[float] = None) -> str:
        # This tool synthesizes data from the campaign performance tool
        # In production, it would pull live data; here we define the recommendation logic

        return json.dumps({
            "analysis_period": f"Last {days} days",
            "target_cpa_inr": target_cpa or "Not set — recommend setting based on avg treatment value",
            "recommendation_framework": {
                "scale_up": (
                    "Campaigns with CPA below target and conversion volume. "
                    "Increase daily budget by 20% weekly until CPA rises to target."
                ),
                "optimize": (
                    "Campaigns with CPA near target. Focus on ad copy A/B testing, "
                    "landing page improvements, and negative keyword additions."
                ),
                "scale_down": (
                    "Campaigns with CPA above 1.5x target. Reduce budget by 25%, "
                    "pause low-performing ad groups, review keyword match types."
                ),
                "pause": (
                    "Campaigns with zero conversions after 2 weeks of spend. "
                    "Reallocate budget to performing campaigns."
                ),
            },
            "ayurvedic_clinic_benchmarks": {
                "avg_cpc_inr": "15-45 for treatment keywords",
                "avg_cpa_inr": "300-800 for appointment bookings",
                "recommended_daily_budget_inr": "500-2000 depending on city competition",
                "best_performing_keywords": [
                    "panchakarma treatment [city]",
                    "ayurvedic doctor near me",
                    "ayurvedic treatment for [condition]",
                    "best ayurvedic clinic [city]",
                ],
            },
            "note": "Connect Google Ads API for real-time recommendations based on actual data.",
        }, indent=2)
