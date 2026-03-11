"""
Practo Integration Tool — Monitor reviews, track profile visibility, and analyze competitors.
Practo doesn't have a public API, so this uses web scraping via httpx + HTML parsing.
For production, consider using a headless browser (Playwright) for more reliable scraping.
"""

import json
import re
from typing import Type, Optional
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
from config.settings import settings

try:
    import httpx
    from html.parser import HTMLParser
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False


class PractoFetchReviewsInput(BaseModel):
    doctor_url: str = Field(
        description=(
            "Full Practo doctor profile URL, e.g. "
            "'https://www.practo.com/bengaluru/doctor/dr-name-ayurveda'"
        )
    )
    max_reviews: int = Field(default=20, description="Maximum number of reviews to fetch")


class PractoCompetitorInput(BaseModel):
    city: str = Field(description="City name, e.g. 'bengaluru'")
    specialty: str = Field(
        default="ayurveda",
        description="Specialty to search, e.g. 'ayurveda', 'panchakarma'"
    )
    max_results: int = Field(default=10, description="Number of competitor profiles to analyze")


class PractoMonitorInput(BaseModel):
    doctor_url: str = Field(description="Full Practo doctor profile URL")


class PractoFetchReviewsTool(BaseTool):
    name: str = "practo_fetch_reviews"
    description: str = (
        "Fetch patient reviews from a Practo doctor profile. Returns review text, "
        "rating, patient name, and date. Practo is the #1 platform where patients "
        "discover Ayurvedic doctors in India — monitoring it is critical. "
        "Input: doctor_url (full Practo profile URL), max_reviews."
    )
    args_schema: Type[BaseModel] = PractoFetchReviewsInput

    def _run(self, doctor_url: str, max_reviews: int = 20) -> str:
        if not HTTPX_AVAILABLE:
            return "ERROR: httpx not installed. Run: pip install httpx"

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-IN,en;q=0.9",
        }

        try:
            resp = httpx.get(doctor_url, headers=headers, timeout=30, follow_redirects=True)
            resp.raise_for_status()
            html = resp.text

            # Extract structured data from page (Practo embeds JSON-LD)
            reviews = []

            # Try JSON-LD extraction first
            json_ld_pattern = r'<script type="application/ld\+json">(.*?)</script>'
            json_ld_matches = re.findall(json_ld_pattern, html, re.DOTALL)

            for match in json_ld_matches:
                try:
                    data = json.loads(match)
                    if isinstance(data, dict) and data.get("@type") == "Physician":
                        aggregate = data.get("aggregateRating", {})
                        review_list = data.get("review", [])
                        for rev in review_list[:max_reviews]:
                            reviews.append({
                                "reviewer": rev.get("author", {}).get("name", "Anonymous"),
                                "rating": rev.get("reviewRating", {}).get("ratingValue", 0),
                                "text": rev.get("reviewBody", "(no text)"),
                                "date": rev.get("datePublished", ""),
                            })

                        result = {
                            "profile_url": doctor_url,
                            "overall_rating": aggregate.get("ratingValue", "N/A"),
                            "total_reviews": aggregate.get("reviewCount", "N/A"),
                            "reviews": reviews,
                        }
                        return json.dumps(result, indent=2, ensure_ascii=False)
                except json.JSONDecodeError:
                    continue

            # Fallback: basic regex extraction
            rating_match = re.search(r'"ratingValue"\s*:\s*"?([\d.]+)"?', html)
            count_match = re.search(r'"reviewCount"\s*:\s*"?(\d+)"?', html)

            return json.dumps({
                "profile_url": doctor_url,
                "overall_rating": rating_match.group(1) if rating_match else "N/A",
                "total_reviews": count_match.group(1) if count_match else "N/A",
                "reviews": reviews,
                "note": "Limited data extracted. Consider using Playwright for full scraping.",
            }, indent=2)

        except httpx.HTTPStatusError as e:
            return f"Practo HTTP error ({e.response.status_code}): Could not fetch profile"
        except Exception as e:
            return f"Error fetching Practo reviews: {str(e)}"


class PractoCompetitorAnalysisTool(BaseTool):
    name: str = "practo_competitor_analysis"
    description: str = (
        "Analyze competing Ayurvedic doctors/clinics on Practo in your city. "
        "Returns competitor profiles with ratings, review counts, consultation fees, "
        "and specializations. Essential for competitive positioning. "
        "Input: city, specialty, max_results."
    )
    args_schema: Type[BaseModel] = PractoCompetitorInput

    def _run(
        self, city: str = "bengaluru", specialty: str = "ayurveda", max_results: int = 10
    ) -> str:
        if not HTTPX_AVAILABLE:
            return "ERROR: httpx not installed."

        search_url = f"https://www.practo.com/{city.lower()}/doctors-for-{specialty}"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml",
        }

        try:
            resp = httpx.get(search_url, headers=headers, timeout=30, follow_redirects=True)
            resp.raise_for_status()
            html = resp.text

            # Extract doctor cards from search results
            competitors = []

            # Look for JSON-LD data
            json_ld_pattern = r'<script type="application/ld\+json">(.*?)</script>'
            json_ld_matches = re.findall(json_ld_pattern, html, re.DOTALL)

            for match in json_ld_matches:
                try:
                    data = json.loads(match)
                    if isinstance(data, list):
                        for item in data[:max_results]:
                            if item.get("@type") in ("Physician", "MedicalBusiness"):
                                competitors.append({
                                    "name": item.get("name", "Unknown"),
                                    "rating": item.get("aggregateRating", {}).get("ratingValue", "N/A"),
                                    "review_count": item.get("aggregateRating", {}).get("reviewCount", 0),
                                    "address": item.get("address", {}).get("streetAddress", ""),
                                    "url": item.get("url", ""),
                                })
                    elif isinstance(data, dict) and data.get("@type") in ("Physician", "MedicalBusiness"):
                        competitors.append({
                            "name": data.get("name", "Unknown"),
                            "rating": data.get("aggregateRating", {}).get("ratingValue", "N/A"),
                            "review_count": data.get("aggregateRating", {}).get("reviewCount", 0),
                            "url": data.get("url", ""),
                        })
                except json.JSONDecodeError:
                    continue

            return json.dumps({
                "city": city,
                "specialty": specialty,
                "search_url": search_url,
                "competitors_found": len(competitors),
                "competitors": competitors[:max_results],
                "analysis_tip": (
                    "Focus on doctors with high review counts but lower ratings — "
                    "these are vulnerable competitors. Also look for gaps in specialization "
                    "that you can fill."
                ),
            }, indent=2, ensure_ascii=False)

        except Exception as e:
            return f"Error analyzing Practo competitors: {str(e)}"


class PractoProfileMonitorTool(BaseTool):
    name: str = "practo_profile_monitor"
    description: str = (
        "Monitor your Practo profile metrics — rating, review count, profile completeness, "
        "and visibility signals. Use weekly to track reputation growth on Practo. "
        "Input: doctor_url."
    )
    args_schema: Type[BaseModel] = PractoMonitorInput

    def _run(self, doctor_url: str) -> str:
        if not HTTPX_AVAILABLE:
            return "ERROR: httpx not installed."

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
        }

        try:
            resp = httpx.get(doctor_url, headers=headers, timeout=30, follow_redirects=True)
            resp.raise_for_status()
            html = resp.text

            # Extract key profile signals
            metrics = {
                "profile_url": doctor_url,
                "page_accessible": True,
                "has_photo": bool(re.search(r'doctor-profile-image|profile-photo', html)),
                "has_services": bool(re.search(r'services|specialization', html, re.I)),
                "has_faq": bool(re.search(r'frequently.asked|faq', html, re.I)),
                "has_timings": bool(re.search(r'clinic-timings|availability', html, re.I)),
            }

            # Extract rating
            rating_match = re.search(r'"ratingValue"\s*:\s*"?([\d.]+)"?', html)
            count_match = re.search(r'"reviewCount"\s*:\s*"?(\d+)"?', html)
            metrics["rating"] = float(rating_match.group(1)) if rating_match else None
            metrics["review_count"] = int(count_match.group(1)) if count_match else None

            # Profile completeness score
            completeness_checks = [
                metrics["has_photo"],
                metrics["has_services"],
                metrics["has_faq"],
                metrics["has_timings"],
                metrics["rating"] is not None,
            ]
            metrics["completeness_score"] = f"{sum(completeness_checks)}/{len(completeness_checks)}"

            # Recommendations
            recs = []
            if not metrics["has_photo"]:
                recs.append("Add a professional profile photo — profiles with photos get 3x more views")
            if not metrics["has_faq"]:
                recs.append("Add an FAQ section — it improves SEO and patient trust")
            if metrics["review_count"] and metrics["review_count"] < 50:
                recs.append("Increase review collection — aim for 50+ reviews for top visibility")
            if metrics["rating"] and metrics["rating"] < 4.5:
                recs.append("Focus on service quality to improve rating above 4.5 stars")
            metrics["recommendations"] = recs

            return json.dumps(metrics, indent=2)

        except Exception as e:
            return f"Error monitoring Practo profile: {str(e)}"
