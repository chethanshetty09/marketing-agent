"""
Email Campaign Tool — send marketing emails via SendGrid.
Supports single sends and batch campaigns with personalization.
"""

import json
from typing import Type, Optional
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
from config.settings import settings

try:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail, To, Personalization
    SENDGRID_AVAILABLE = True
except ImportError:
    SENDGRID_AVAILABLE = False


class EmailCampaignInput(BaseModel):
    recipients: list[dict] = Field(
        description=(
            "List of recipient dicts with 'email', 'name', and optional personalization fields. "
            "Example: [{'email': 'patient@example.com', 'name': 'Priya', 'dosha': 'Vata'}]"
        )
    )
    subject: str = Field(description="Email subject line (personalization with {{name}} supported)")
    html_content: str = Field(
        description="HTML email body. Use {{name}}, {{dosha}}, etc. for personalization."
    )
    campaign_name: Optional[str] = Field(default=None, description="Internal campaign name for tracking")


class SendEmailCampaignTool(BaseTool):
    name: str = "send_email_campaign"
    description: str = (
        "Send a marketing email campaign to a list of patients via SendGrid. "
        "Supports HTML content with personalization tags like {{name}} and {{dosha}}. "
        "Use for welcome sequences, seasonal promotions, newsletter, event invitations, "
        "and post-treatment follow-ups. "
        "Input: recipients list (with email, name, custom fields), subject, html_content."
    )
    args_schema: Type[BaseModel] = EmailCampaignInput

    def _run(
        self,
        recipients: list[dict],
        subject: str,
        html_content: str,
        campaign_name: Optional[str] = None,
    ) -> str:
        if not SENDGRID_AVAILABLE:
            return "ERROR: sendgrid not installed. Run: pip install sendgrid"

        cfg = settings.sendgrid
        if not cfg.api_key:
            return "ERROR: SendGrid not configured. Set SENDGRID_API_KEY in .env"

        try:
            sg = SendGridAPIClient(cfg.api_key)
            sent_count = 0
            errors = []

            for recipient in recipients:
                email = recipient.get("email")
                if not email:
                    continue

                # Apply personalization
                personalized_subject = subject
                personalized_body = html_content
                for key, value in recipient.items():
                    placeholder = "{{" + key + "}}"
                    personalized_subject = personalized_subject.replace(placeholder, str(value))
                    personalized_body = personalized_body.replace(placeholder, str(value))

                message = Mail(
                    from_email=(cfg.from_email, cfg.from_name),
                    to_emails=email,
                    subject=personalized_subject,
                    html_content=personalized_body,
                )

                # Add tracking category
                if campaign_name:
                    message.category = [campaign_name]

                try:
                    response = sg.send(message)
                    if response.status_code in (200, 201, 202):
                        sent_count += 1
                    else:
                        errors.append(f"{email}: HTTP {response.status_code}")
                except Exception as e:
                    errors.append(f"{email}: {str(e)}")

            result = {
                "campaign": campaign_name or "unnamed",
                "total_recipients": len(recipients),
                "sent_successfully": sent_count,
                "errors": errors[:5] if errors else [],  # Cap error list
            }
            return json.dumps(result, indent=2)

        except Exception as e:
            return f"Email campaign error: {str(e)}"
