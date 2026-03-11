"""
WhatsApp Business API Tools — send messages and template campaigns to patients.
Uses the official Cloud API (graph.facebook.com).
"""

import json
import httpx
from typing import Type
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
from config.settings import settings


class WhatsAppMessageInput(BaseModel):
    phone_number: str = Field(description="Patient phone number with country code, e.g. +919876543210")
    message: str = Field(description="Text message to send to the patient")


class WhatsAppTemplateInput(BaseModel):
    phone_number: str = Field(description="Patient phone number with country code")
    template_name: str = Field(description="Name of the approved WhatsApp template")
    template_params: list[str] = Field(
        default=[],
        description="List of parameter values to fill in the template placeholders"
    )
    language_code: str = Field(default="en", description="Template language code")


class WhatsAppSendMessageTool(BaseTool):
    name: str = "whatsapp_send_message"
    description: str = (
        "Send a WhatsApp text message to a patient. Use for personalized follow-ups, "
        "appointment reminders, and one-on-one communication. "
        "Input: phone_number (with country code) and message text."
    )
    args_schema: Type[BaseModel] = WhatsAppMessageInput

    def _run(self, phone_number: str, message: str) -> str:
        cfg = settings.whatsapp
        if not cfg.access_token:
            return "ERROR: WhatsApp API not configured. Set WHATSAPP_ACCESS_TOKEN in .env"

        url = f"{cfg.api_url}/{cfg.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {cfg.access_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": phone_number.replace("+", "").replace(" ", ""),
            "type": "text",
            "text": {"body": message},
        }

        try:
            resp = httpx.post(url, headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            msg_id = data.get("messages", [{}])[0].get("id", "unknown")
            return f"Message sent successfully to {phone_number}. Message ID: {msg_id}"
        except httpx.HTTPStatusError as e:
            return f"WhatsApp API error ({e.response.status_code}): {e.response.text}"
        except Exception as e:
            return f"Failed to send WhatsApp message: {str(e)}"


class WhatsAppSendTemplateTool(BaseTool):
    name: str = "whatsapp_send_template"
    description: str = (
        "Send a pre-approved WhatsApp template message to a patient. "
        "Use for campaigns, review requests, appointment confirmations, seasonal promotions. "
        "Templates must be pre-approved in WhatsApp Business Manager. "
        "Input: phone_number, template_name, and optional template_params list."
    )
    args_schema: Type[BaseModel] = WhatsAppTemplateInput

    def _run(
        self, phone_number: str, template_name: str,
        template_params: list[str] = [], language_code: str = "en"
    ) -> str:
        cfg = settings.whatsapp
        if not cfg.access_token:
            return "ERROR: WhatsApp API not configured. Set WHATSAPP_ACCESS_TOKEN in .env"

        url = f"{cfg.api_url}/{cfg.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {cfg.access_token}",
            "Content-Type": "application/json",
        }

        # Build template components
        components = []
        if template_params:
            parameters = [
                {"type": "text", "text": param} for param in template_params
            ]
            components.append({"type": "body", "parameters": parameters})

        payload = {
            "messaging_product": "whatsapp",
            "to": phone_number.replace("+", "").replace(" ", ""),
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language_code},
                "components": components,
            },
        }

        try:
            resp = httpx.post(url, headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            msg_id = data.get("messages", [{}])[0].get("id", "unknown")
            return f"Template '{template_name}' sent to {phone_number}. Message ID: {msg_id}"
        except httpx.HTTPStatusError as e:
            return f"WhatsApp API error ({e.response.status_code}): {e.response.text}"
        except Exception as e:
            return f"Failed to send WhatsApp template: {str(e)}"
