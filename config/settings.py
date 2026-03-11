"""
Central configuration — loads .env and exposes typed settings.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import Optional

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


class ClinicConfig(BaseModel):
    name: str = Field(default_factory=lambda: os.getenv("CLINIC_NAME", "Ayurvedic Wellness Clinic"))
    city: str = Field(default_factory=lambda: os.getenv("CLINIC_CITY", "Bengaluru"))
    phone: str = Field(default_factory=lambda: os.getenv("CLINIC_PHONE", ""))
    website: str = Field(default_factory=lambda: os.getenv("CLINIC_WEBSITE", ""))
    specialties: list[str] = Field(
        default_factory=lambda: os.getenv(
            "CLINIC_SPECIALTIES", "Panchakarma,Prakriti Analysis"
        ).split(",")
    )


class LLMConfig(BaseModel):
    provider: str = Field(default_factory=lambda: os.getenv("LLM_PROVIDER", "openai"))
    model: str = Field(default_factory=lambda: os.getenv("LLM_MODEL", "gpt-4o"))
    openai_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY"))
    anthropic_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY"))


class WhatsAppConfig(BaseModel):
    phone_number_id: str = Field(default_factory=lambda: os.getenv("WHATSAPP_PHONE_NUMBER_ID", ""))
    access_token: str = Field(default_factory=lambda: os.getenv("WHATSAPP_ACCESS_TOKEN", ""))
    business_account_id: str = Field(default_factory=lambda: os.getenv("WHATSAPP_BUSINESS_ACCOUNT_ID", ""))
    api_url: str = "https://graph.facebook.com/v21.0"


class GoogleBusinessConfig(BaseModel):
    account_id: str = Field(default_factory=lambda: os.getenv("GOOGLE_BUSINESS_ACCOUNT_ID", ""))
    location_id: str = Field(default_factory=lambda: os.getenv("GOOGLE_BUSINESS_LOCATION_ID", ""))
    service_account_json: str = Field(default_factory=lambda: os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", ""))


class MetaConfig(BaseModel):
    page_id: str = Field(default_factory=lambda: os.getenv("META_PAGE_ID", ""))
    instagram_account_id: str = Field(default_factory=lambda: os.getenv("META_INSTAGRAM_ACCOUNT_ID", ""))
    access_token: str = Field(default_factory=lambda: os.getenv("META_ACCESS_TOKEN", ""))
    api_url: str = "https://graph.facebook.com/v21.0"


class SendGridConfig(BaseModel):
    api_key: str = Field(default_factory=lambda: os.getenv("SENDGRID_API_KEY", ""))
    from_email: str = Field(default_factory=lambda: os.getenv("SENDGRID_FROM_EMAIL", ""))
    from_name: str = Field(default_factory=lambda: os.getenv("SENDGRID_FROM_NAME", ""))


class AnalyticsConfig(BaseModel):
    ga_property_id: str = Field(default_factory=lambda: os.getenv("GA_PROPERTY_ID", ""))
    gsc_site_url: str = Field(default_factory=lambda: os.getenv("GSC_SITE_URL", ""))


class GoogleAdsConfig(BaseModel):
    customer_id: str = Field(default_factory=lambda: os.getenv("GOOGLE_ADS_CUSTOMER_ID", ""))
    developer_token: str = Field(default_factory=lambda: os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN", ""))
    refresh_token: str = Field(default_factory=lambda: os.getenv("GOOGLE_ADS_REFRESH_TOKEN", ""))


class PractoConfig(BaseModel):
    doctor_url: str = Field(default_factory=lambda: os.getenv("PRACTO_DOCTOR_URL", ""))


class YouTubeConfig(BaseModel):
    channel_id: str = Field(default_factory=lambda: os.getenv("YOUTUBE_CHANNEL_ID", ""))


class RazorpayConfig(BaseModel):
    key_id: str = Field(default_factory=lambda: os.getenv("RAZORPAY_KEY_ID", ""))
    key_secret: str = Field(default_factory=lambda: os.getenv("RAZORPAY_KEY_SECRET", ""))


class Settings(BaseModel):
    clinic: ClinicConfig = Field(default_factory=ClinicConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    whatsapp: WhatsAppConfig = Field(default_factory=WhatsAppConfig)
    google_business: GoogleBusinessConfig = Field(default_factory=GoogleBusinessConfig)
    meta: MetaConfig = Field(default_factory=MetaConfig)
    sendgrid: SendGridConfig = Field(default_factory=SendGridConfig)
    analytics: AnalyticsConfig = Field(default_factory=AnalyticsConfig)
    google_ads: GoogleAdsConfig = Field(default_factory=GoogleAdsConfig)
    practo: PractoConfig = Field(default_factory=PractoConfig)
    youtube: YouTubeConfig = Field(default_factory=YouTubeConfig)
    razorpay: RazorpayConfig = Field(default_factory=RazorpayConfig)


# Singleton
settings = Settings()
