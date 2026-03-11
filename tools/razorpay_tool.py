"""
Razorpay Payment Tracking Tool — Track payments, refunds, and revenue analytics.
Uses Razorpay API for payment data that feeds into the Insight Oracle's ROI calculations.
"""

import json
import httpx
import base64
from typing import Type, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
from config.settings import settings


class PaymentFetchInput(BaseModel):
    days: int = Field(default=30, description="Number of days to look back")
    status: Optional[str] = Field(
        default=None,
        description="Filter by status: 'captured' (successful), 'refunded', 'failed'"
    )


class RevenueReportInput(BaseModel):
    days: int = Field(default=30, description="Analysis period in days")
    group_by: str = Field(
        default="day",
        description="Group revenue by: 'day', 'week', 'month', 'treatment'"
    )


class PaymentLinkInput(BaseModel):
    amount_inr: float = Field(description="Payment amount in INR")
    patient_name: str = Field(description="Patient name for the payment link")
    treatment_name: str = Field(description="Treatment/service description")
    patient_phone: Optional[str] = Field(default=None, description="Patient phone for SMS notification")
    patient_email: Optional[str] = Field(default=None, description="Patient email for notification")
    expiry_minutes: int = Field(default=1440, description="Link expiry time in minutes (default 24 hours)")


class RazorpayFetchPaymentsTool(BaseTool):
    name: str = "razorpay_fetch_payments"
    description: str = (
        "Fetch recent payments from Razorpay. Returns payment details including "
        "amount, status, method, patient info, and timestamps. "
        "Use to track revenue, identify failed payments, and reconcile with CRM. "
        "Input: days lookback, optional status filter."
    )
    args_schema: Type[BaseModel] = PaymentFetchInput

    def _run(self, days: int = 30, status: Optional[str] = None) -> str:
        key_id = getattr(settings, 'razorpay', None)
        if not key_id:
            return "ERROR: Razorpay not configured. Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET in .env"

        rz_key = settings.razorpay.key_id if hasattr(settings, 'razorpay') else ""
        rz_secret = settings.razorpay.key_secret if hasattr(settings, 'razorpay') else ""

        if not rz_key:
            return "ERROR: Razorpay not configured. Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET in .env"

        try:
            # Calculate timestamp range
            from_ts = int((datetime.now() - timedelta(days=days)).timestamp())
            to_ts = int(datetime.now().timestamp())

            auth = base64.b64encode(f"{rz_key}:{rz_secret}".encode()).decode()
            headers = {"Authorization": f"Basic {auth}"}

            params = {
                "from": from_ts,
                "to": to_ts,
                "count": 100,
            }

            resp = httpx.get(
                "https://api.razorpay.com/v1/payments",
                headers=headers, params=params, timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()

            payments = []
            total_captured = 0
            total_refunded = 0
            total_failed = 0

            for item in data.get("items", []):
                payment_status = item.get("status", "unknown")

                if status and payment_status != status:
                    continue

                amount_inr = item.get("amount", 0) / 100  # Razorpay stores in paise

                payment = {
                    "id": item.get("id"),
                    "amount_inr": amount_inr,
                    "status": payment_status,
                    "method": item.get("method", "unknown"),
                    "email": item.get("email", ""),
                    "contact": item.get("contact", ""),
                    "description": item.get("description", ""),
                    "created_at": datetime.fromtimestamp(
                        item.get("created_at", 0)
                    ).isoformat(),
                    "notes": item.get("notes", {}),
                }
                payments.append(payment)

                if payment_status == "captured":
                    total_captured += amount_inr
                elif payment_status == "refunded":
                    total_refunded += amount_inr
                elif payment_status == "failed":
                    total_failed += amount_inr

            return json.dumps({
                "period": f"Last {days} days",
                "summary": {
                    "total_revenue_inr": round(total_captured, 2),
                    "total_refunded_inr": round(total_refunded, 2),
                    "failed_amount_inr": round(total_failed, 2),
                    "net_revenue_inr": round(total_captured - total_refunded, 2),
                    "transaction_count": len(payments),
                },
                "payments": payments[:50],  # Cap at 50 for readability
            }, indent=2)

        except httpx.HTTPStatusError as e:
            return f"Razorpay API error ({e.response.status_code}): {e.response.text}"
        except Exception as e:
            return f"Error fetching payments: {str(e)}"


class RazorpayRevenueReportTool(BaseTool):
    name: str = "razorpay_revenue_report"
    description: str = (
        "Generate a revenue analytics report from Razorpay data. Shows revenue trends, "
        "payment method breakdown, average transaction value, and treatment-level revenue. "
        "Essential for the Insight Oracle to calculate true marketing ROI. "
        "Input: days, group_by ('day', 'week', 'month', 'treatment')."
    )
    args_schema: Type[BaseModel] = RevenueReportInput

    def _run(self, days: int = 30, group_by: str = "day") -> str:
        # First fetch raw payments
        fetch_tool = RazorpayFetchPaymentsTool()
        raw_result = fetch_tool._run(days=days, status="captured")

        try:
            raw_data = json.loads(raw_result)
        except json.JSONDecodeError:
            return raw_result  # Return the error message

        if "error" in raw_result.lower():
            return raw_result

        payments = raw_data.get("payments", [])
        if not payments:
            return json.dumps({
                "period": f"Last {days} days",
                "message": "No captured payments found in this period.",
            })

        # Group and analyze
        method_breakdown = {}
        daily_revenue = {}

        for p in payments:
            method = p.get("method", "unknown")
            method_breakdown[method] = method_breakdown.get(method, 0) + p["amount_inr"]

            date_str = p["created_at"][:10]  # YYYY-MM-DD
            daily_revenue[date_str] = daily_revenue.get(date_str, 0) + p["amount_inr"]

        amounts = [p["amount_inr"] for p in payments]

        report = {
            "period": f"Last {days} days",
            "total_revenue_inr": round(sum(amounts), 2),
            "transaction_count": len(payments),
            "average_transaction_inr": round(sum(amounts) / len(amounts), 2),
            "highest_transaction_inr": round(max(amounts), 2),
            "payment_method_breakdown": {
                k: round(v, 2) for k, v in
                sorted(method_breakdown.items(), key=lambda x: x[1], reverse=True)
            },
            "daily_revenue": dict(sorted(daily_revenue.items())),
            "insights": [],
        }

        # Auto-generate insights
        avg = report["average_transaction_inr"]
        if avg < 1000:
            report["insights"].append(
                "Low average transaction value. Consider upselling package treatments."
            )
        if "upi" in method_breakdown and method_breakdown["upi"] > sum(amounts) * 0.5:
            report["insights"].append(
                "UPI dominates payments. Ensure smooth UPI payment experience."
            )

        return json.dumps(report, indent=2)


class RazorpayCreatePaymentLinkTool(BaseTool):
    name: str = "razorpay_create_payment_link"
    description: str = (
        "Create a Razorpay payment link to send to a patient via WhatsApp or email. "
        "Useful for collecting advance payments, treatment fees, or package bookings. "
        "Input: amount_inr, patient_name, treatment_name, optional phone/email."
    )
    args_schema: Type[BaseModel] = PaymentLinkInput

    def _run(
        self, amount_inr: float, patient_name: str, treatment_name: str,
        patient_phone: Optional[str] = None, patient_email: Optional[str] = None,
        expiry_minutes: int = 1440,
    ) -> str:
        rz_key = settings.razorpay.key_id if hasattr(settings, 'razorpay') else ""
        rz_secret = settings.razorpay.key_secret if hasattr(settings, 'razorpay') else ""

        if not rz_key:
            return "ERROR: Razorpay not configured. Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET in .env"

        try:
            auth = base64.b64encode(f"{rz_key}:{rz_secret}".encode()).decode()
            headers = {
                "Authorization": f"Basic {auth}",
                "Content-Type": "application/json",
            }

            expire_by = int((datetime.now() + timedelta(minutes=expiry_minutes)).timestamp())

            payload = {
                "amount": int(amount_inr * 100),  # Convert to paise
                "currency": "INR",
                "description": f"{treatment_name} — {settings.clinic.name}",
                "customer": {
                    "name": patient_name,
                },
                "notify": {
                    "sms": bool(patient_phone),
                    "email": bool(patient_email),
                },
                "reminder_enable": True,
                "expire_by": expire_by,
                "notes": {
                    "clinic": settings.clinic.name,
                    "treatment": treatment_name,
                    "patient": patient_name,
                },
            }

            if patient_phone:
                payload["customer"]["contact"] = patient_phone
            if patient_email:
                payload["customer"]["email"] = patient_email

            resp = httpx.post(
                "https://api.razorpay.com/v1/payment_links",
                headers=headers, json=payload, timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()

            return json.dumps({
                "status": "success",
                "payment_link": data.get("short_url"),
                "payment_link_id": data.get("id"),
                "amount_inr": amount_inr,
                "patient": patient_name,
                "treatment": treatment_name,
                "expires_at": datetime.fromtimestamp(expire_by).isoformat(),
                "notification_sent": {
                    "sms": bool(patient_phone),
                    "email": bool(patient_email),
                },
            }, indent=2)

        except httpx.HTTPStatusError as e:
            return f"Razorpay API error ({e.response.status_code}): {e.response.text}"
        except Exception as e:
            return f"Error creating payment link: {str(e)}"
