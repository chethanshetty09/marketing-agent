"""
Google Analytics 4 Tool — fetch website traffic, conversion, and audience data.
"""

import json
from typing import Type, Optional
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
from config.settings import settings

try:
    from google.oauth2 import service_account
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.analytics.data_v1beta.types import (
        RunReportRequest, DateRange, Dimension, Metric, OrderBy
    )
    GA_AVAILABLE = True
except ImportError:
    GA_AVAILABLE = False


class AnalyticsInput(BaseModel):
    days: int = Field(default=30, description="Number of days to look back")
    report_type: str = Field(
        default="overview",
        description="Type of report: 'overview', 'top_pages', 'traffic_sources', 'conversions'"
    )


class GoogleAnalyticsTool(BaseTool):
    name: str = "google_analytics_report"
    description: str = (
        "Fetch Google Analytics 4 data for the clinic's website. "
        "Supports reports: overview (sessions, users, bounce rate), "
        "top_pages (most visited pages), traffic_sources (where visitors come from), "
        "conversions (goal completions like appointment bookings). "
        "Input: days lookback and report_type."
    )
    args_schema: Type[BaseModel] = AnalyticsInput

    def _run(self, days: int = 30, report_type: str = "overview") -> str:
        if not GA_AVAILABLE:
            return (
                "ERROR: Google Analytics libraries not installed. "
                "Run: pip install google-analytics-data"
            )

        cfg = settings.analytics
        if not cfg.ga_property_id:
            return "ERROR: Google Analytics not configured. Set GA_PROPERTY_ID in .env"

        try:
            gcfg = settings.google_business
            credentials = service_account.Credentials.from_service_account_file(
                gcfg.service_account_json,
                scopes=["https://www.googleapis.com/auth/analytics.readonly"],
            )
            client = BetaAnalyticsDataClient(credentials=credentials)
            property_id = f"properties/{cfg.ga_property_id}"

            date_range = DateRange(start_date=f"{days}daysAgo", end_date="today")

            # Build report based on type
            if report_type == "overview":
                request = RunReportRequest(
                    property=property_id,
                    date_ranges=[date_range],
                    metrics=[
                        Metric(name="sessions"),
                        Metric(name="totalUsers"),
                        Metric(name="newUsers"),
                        Metric(name="bounceRate"),
                        Metric(name="averageSessionDuration"),
                        Metric(name="screenPageViews"),
                    ],
                )
            elif report_type == "top_pages":
                request = RunReportRequest(
                    property=property_id,
                    date_ranges=[date_range],
                    dimensions=[Dimension(name="pagePath")],
                    metrics=[
                        Metric(name="screenPageViews"),
                        Metric(name="totalUsers"),
                        Metric(name="bounceRate"),
                    ],
                    order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="screenPageViews"), desc=True)],
                    limit=20,
                )
            elif report_type == "traffic_sources":
                request = RunReportRequest(
                    property=property_id,
                    date_ranges=[date_range],
                    dimensions=[
                        Dimension(name="sessionSource"),
                        Dimension(name="sessionMedium"),
                    ],
                    metrics=[
                        Metric(name="sessions"),
                        Metric(name="totalUsers"),
                        Metric(name="conversions"),
                    ],
                    order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)],
                    limit=15,
                )
            elif report_type == "conversions":
                request = RunReportRequest(
                    property=property_id,
                    date_ranges=[date_range],
                    dimensions=[Dimension(name="eventName")],
                    metrics=[
                        Metric(name="eventCount"),
                        Metric(name="totalUsers"),
                    ],
                    order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="eventCount"), desc=True)],
                    limit=10,
                )
            else:
                return f"Unknown report_type '{report_type}'. Use: overview, top_pages, traffic_sources, conversions"

            response = client.run_report(request)

            # Parse response
            if report_type == "overview":
                row = response.rows[0] if response.rows else None
                if not row:
                    return "No analytics data found."
                metrics = response.metric_headers
                data = {
                    metrics[i].name: row.metric_values[i].value
                    for i in range(len(metrics))
                }
                return json.dumps({"period": f"Last {days} days", "metrics": data}, indent=2)
            else:
                results = []
                for row in response.rows:
                    entry = {}
                    for i, dim in enumerate(response.dimension_headers):
                        entry[dim.name] = row.dimension_values[i].value
                    for i, met in enumerate(response.metric_headers):
                        entry[met.name] = row.metric_values[i].value
                    results.append(entry)
                return json.dumps({
                    "period": f"Last {days} days",
                    "report": report_type,
                    "data": results,
                }, indent=2)

        except Exception as e:
            return f"Error fetching analytics: {str(e)}"
