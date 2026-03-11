"""
Patient CRM Tool — Lightweight SQLite-based patient database.
Tracks the full patient lifecycle: registration → consultation → treatment → follow-up → retention.
Designed specifically for Ayurvedic clinics with dosha profiling and Ritucharya alignment.
"""

import json
import sqlite3
from datetime import datetime, timedelta
from typing import Type, Optional
from pathlib import Path
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
from config.settings import settings

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "patients.db"


def _get_db():
    """Get database connection, creating tables if needed."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT UNIQUE,
            email TEXT,
            age INTEGER,
            gender TEXT,
            dosha_type TEXT,           -- Vata, Pitta, Kapha, or combination
            prakriti_details TEXT,      -- JSON: detailed Prakriti assessment
            conditions TEXT,           -- JSON: list of conditions being treated
            source TEXT,               -- how they found us: google, practo, referral, walk-in, social
            referrer_id INTEGER,       -- patient who referred them
            status TEXT DEFAULT 'active',  -- active, inactive, churned
            tags TEXT,                 -- JSON: custom tags for segmentation
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS treatments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            treatment_name TEXT NOT NULL,   -- e.g. Panchakarma, Shirodhara, Abhyanga
            treatment_type TEXT,            -- consultation, therapy, package
            start_date DATE,
            end_date DATE,
            sessions_total INTEGER DEFAULT 1,
            sessions_completed INTEGER DEFAULT 0,
            cost_inr REAL,
            paid_inr REAL DEFAULT 0,
            payment_status TEXT DEFAULT 'pending',  -- pending, partial, paid
            doctor_name TEXT,
            notes TEXT,
            status TEXT DEFAULT 'active',   -- active, completed, cancelled
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES patients(id)
        );

        CREATE TABLE IF NOT EXISTS interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            channel TEXT NOT NULL,       -- whatsapp, email, phone, in-person, sms
            direction TEXT NOT NULL,     -- inbound, outbound
            interaction_type TEXT,       -- follow-up, reminder, review-request, campaign, support
            content TEXT,               -- message content or summary
            campaign_name TEXT,         -- if part of a campaign
            status TEXT DEFAULT 'sent', -- sent, delivered, read, replied, failed
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES patients(id)
        );

        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            treatment_id INTEGER,
            appointment_date DATE NOT NULL,
            appointment_time TEXT,
            duration_minutes INTEGER DEFAULT 60,
            status TEXT DEFAULT 'scheduled',  -- scheduled, confirmed, completed, no-show, cancelled
            reminder_sent BOOLEAN DEFAULT FALSE,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES patients(id),
            FOREIGN KEY (treatment_id) REFERENCES treatments(id)
        );

        CREATE INDEX IF NOT EXISTS idx_patients_phone ON patients(phone);
        CREATE INDEX IF NOT EXISTS idx_patients_dosha ON patients(dosha_type);
        CREATE INDEX IF NOT EXISTS idx_patients_status ON patients(status);
        CREATE INDEX IF NOT EXISTS idx_treatments_patient ON treatments(patient_id);
        CREATE INDEX IF NOT EXISTS idx_treatments_status ON treatments(status);
        CREATE INDEX IF NOT EXISTS idx_interactions_patient ON interactions(patient_id);
        CREATE INDEX IF NOT EXISTS idx_appointments_date ON appointments(appointment_date);
    """)

    return conn


# ─── Input Schemas ───

class AddPatientInput(BaseModel):
    name: str = Field(description="Patient full name")
    phone: str = Field(description="Phone number with country code")
    email: Optional[str] = Field(default=None, description="Email address")
    age: Optional[int] = Field(default=None, description="Patient age")
    gender: Optional[str] = Field(default=None, description="Male, Female, Other")
    dosha_type: Optional[str] = Field(default=None, description="Vata, Pitta, Kapha, Vata-Pitta, etc.")
    conditions: Optional[list[str]] = Field(default=None, description="List of conditions")
    source: Optional[str] = Field(default=None, description="How they found us: google, practo, referral, walk-in, social")
    notes: Optional[str] = Field(default=None)


class SearchPatientInput(BaseModel):
    query: str = Field(description="Search by name, phone, or email")


class GetSegmentInput(BaseModel):
    segment: str = Field(
        description=(
            "Patient segment to retrieve. Options: "
            "'needs_followup' (treated 2+ days ago, no recent interaction), "
            "'vata_patients', 'pitta_patients', 'kapha_patients' (by dosha), "
            "'inactive' (no visit in 60+ days), "
            "'high_value' (spent > 10000 INR), "
            "'no_review' (completed treatment, never asked for review), "
            "'birthday_this_week', "
            "'recent_completions' (treatment completed in last 7 days)"
        )
    )


class AddTreatmentInput(BaseModel):
    patient_phone: str = Field(description="Patient phone number to look up")
    treatment_name: str = Field(description="Treatment name, e.g. 'Panchakarma', 'Abhyanga'")
    treatment_type: str = Field(default="therapy", description="consultation, therapy, or package")
    sessions_total: int = Field(default=1, description="Total number of sessions")
    cost_inr: float = Field(description="Treatment cost in INR")
    doctor_name: Optional[str] = Field(default=None)
    notes: Optional[str] = Field(default=None)


class LogInteractionInput(BaseModel):
    patient_phone: str = Field(description="Patient phone number")
    channel: str = Field(description="whatsapp, email, phone, in-person, sms")
    direction: str = Field(default="outbound", description="inbound or outbound")
    interaction_type: str = Field(description="follow-up, reminder, review-request, campaign, support")
    content: str = Field(description="Message content or summary")
    campaign_name: Optional[str] = Field(default=None)


class LifecycleReportInput(BaseModel):
    days: int = Field(default=30, description="Analysis period in days")


# ─── Tools ───

class CRMAddPatientTool(BaseTool):
    name: str = "crm_add_patient"
    description: str = (
        "Register a new patient in the CRM. Stores their contact info, dosha type, "
        "conditions, and acquisition source. This is the starting point of the patient lifecycle. "
        "Input: name, phone (required), plus optional email, age, gender, dosha_type, conditions, source."
    )
    args_schema: Type[BaseModel] = AddPatientInput

    def _run(self, name: str, phone: str, **kwargs) -> str:
        try:
            conn = _get_db()
            conn.execute(
                """INSERT INTO patients (name, phone, email, age, gender, dosha_type, conditions, source, notes)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    name, phone, kwargs.get("email"), kwargs.get("age"),
                    kwargs.get("gender"), kwargs.get("dosha_type"),
                    json.dumps(kwargs.get("conditions")) if kwargs.get("conditions") else None,
                    kwargs.get("source"), kwargs.get("notes"),
                ),
            )
            conn.commit()
            patient_id = conn.execute(
                "SELECT id FROM patients WHERE phone = ?", (phone,)
            ).fetchone()["id"]
            conn.close()
            return f"Patient '{name}' registered successfully (ID: {patient_id}, Phone: {phone})"
        except sqlite3.IntegrityError:
            return f"Patient with phone {phone} already exists. Use search to find them."
        except Exception as e:
            return f"Error adding patient: {str(e)}"


class CRMSearchPatientTool(BaseTool):
    name: str = "crm_search_patient"
    description: str = (
        "Search for a patient by name, phone number, or email. "
        "Returns full patient profile including dosha type, treatment history, and interaction log. "
        "Input: search query (name, phone, or email)."
    )
    args_schema: Type[BaseModel] = SearchPatientInput

    def _run(self, query: str) -> str:
        try:
            conn = _get_db()
            patients = conn.execute(
                """SELECT * FROM patients
                   WHERE phone LIKE ? OR name LIKE ? OR email LIKE ?
                   LIMIT 10""",
                (f"%{query}%", f"%{query}%", f"%{query}%"),
            ).fetchall()

            if not patients:
                return f"No patients found matching '{query}'."

            results = []
            for p in patients:
                p_dict = dict(p)
                # Fetch treatments
                treatments = conn.execute(
                    "SELECT * FROM treatments WHERE patient_id = ? ORDER BY created_at DESC LIMIT 5",
                    (p["id"],),
                ).fetchall()
                p_dict["treatments"] = [dict(t) for t in treatments]

                # Fetch recent interactions
                interactions = conn.execute(
                    "SELECT * FROM interactions WHERE patient_id = ? ORDER BY created_at DESC LIMIT 5",
                    (p["id"],),
                ).fetchall()
                p_dict["recent_interactions"] = [dict(i) for i in interactions]

                results.append(p_dict)

            conn.close()
            return json.dumps(results, indent=2, default=str)
        except Exception as e:
            return f"Error searching patients: {str(e)}"


class CRMGetSegmentTool(BaseTool):
    name: str = "crm_get_patient_segment"
    description: str = (
        "Retrieve a specific patient segment for targeted marketing. "
        "Segments available: needs_followup, vata_patients, pitta_patients, kapha_patients, "
        "inactive, high_value, no_review, recent_completions. "
        "Returns patient list with contact details for campaign targeting. "
        "Input: segment name."
    )
    args_schema: Type[BaseModel] = GetSegmentInput

    def _run(self, segment: str) -> str:
        try:
            conn = _get_db()
            now = datetime.now()

            if segment == "needs_followup":
                # Patients with completed treatments in last 7 days and no interaction in last 2 days
                query = """
                    SELECT DISTINCT p.* FROM patients p
                    JOIN treatments t ON p.id = t.patient_id
                    WHERE t.status = 'completed'
                        AND t.end_date >= date('now', '-7 days')
                        AND p.id NOT IN (
                            SELECT patient_id FROM interactions
                            WHERE created_at >= datetime('now', '-2 days')
                        )
                """
            elif segment in ("vata_patients", "pitta_patients", "kapha_patients"):
                dosha = segment.replace("_patients", "").capitalize()
                query = f"""
                    SELECT * FROM patients
                    WHERE dosha_type LIKE '%{dosha}%' AND status = 'active'
                """
            elif segment == "inactive":
                query = """
                    SELECT p.* FROM patients p
                    WHERE p.status = 'active'
                        AND p.id NOT IN (
                            SELECT patient_id FROM treatments
                            WHERE created_at >= datetime('now', '-60 days')
                        )
                        AND p.id NOT IN (
                            SELECT patient_id FROM interactions
                            WHERE created_at >= datetime('now', '-60 days')
                        )
                """
            elif segment == "high_value":
                query = """
                    SELECT p.*, SUM(t.cost_inr) as total_spent
                    FROM patients p
                    JOIN treatments t ON p.id = t.patient_id
                    GROUP BY p.id
                    HAVING total_spent > 10000
                    ORDER BY total_spent DESC
                """
            elif segment == "no_review":
                query = """
                    SELECT DISTINCT p.* FROM patients p
                    JOIN treatments t ON p.id = t.patient_id
                    WHERE t.status = 'completed'
                        AND p.id NOT IN (
                            SELECT patient_id FROM interactions
                            WHERE interaction_type = 'review-request'
                        )
                """
            elif segment == "recent_completions":
                query = """
                    SELECT p.*, t.treatment_name, t.end_date
                    FROM patients p
                    JOIN treatments t ON p.id = t.patient_id
                    WHERE t.status = 'completed'
                        AND t.end_date >= date('now', '-7 days')
                    ORDER BY t.end_date DESC
                """
            else:
                return f"Unknown segment '{segment}'. Available: needs_followup, vata_patients, pitta_patients, kapha_patients, inactive, high_value, no_review, recent_completions"

            patients = conn.execute(query).fetchall()
            conn.close()

            results = [dict(p) for p in patients]
            return json.dumps({
                "segment": segment,
                "count": len(results),
                "patients": results,
            }, indent=2, default=str)

        except Exception as e:
            return f"Error fetching segment: {str(e)}"


class CRMAddTreatmentTool(BaseTool):
    name: str = "crm_add_treatment"
    description: str = (
        "Record a new treatment for a patient. Links to the patient by phone number. "
        "Tracks treatment type, sessions, cost, and payment status. "
        "Input: patient_phone, treatment_name, treatment_type, sessions_total, cost_inr."
    )
    args_schema: Type[BaseModel] = AddTreatmentInput

    def _run(self, patient_phone: str, treatment_name: str, **kwargs) -> str:
        try:
            conn = _get_db()
            patient = conn.execute(
                "SELECT id, name FROM patients WHERE phone = ?", (patient_phone,)
            ).fetchone()
            if not patient:
                return f"No patient found with phone {patient_phone}. Register them first."

            conn.execute(
                """INSERT INTO treatments
                   (patient_id, treatment_name, treatment_type, sessions_total, cost_inr,
                    doctor_name, notes, start_date)
                   VALUES (?, ?, ?, ?, ?, ?, ?, date('now'))""",
                (
                    patient["id"], treatment_name,
                    kwargs.get("treatment_type", "therapy"),
                    kwargs.get("sessions_total", 1),
                    kwargs.get("cost_inr", 0),
                    kwargs.get("doctor_name"),
                    kwargs.get("notes"),
                ),
            )
            conn.commit()
            conn.close()
            return f"Treatment '{treatment_name}' recorded for {patient['name']} (Phone: {patient_phone})"
        except Exception as e:
            return f"Error adding treatment: {str(e)}"


class CRMLogInteractionTool(BaseTool):
    name: str = "crm_log_interaction"
    description: str = (
        "Log a patient interaction (message sent, call made, etc.) in the CRM. "
        "Tracks all touchpoints for lifecycle analysis. "
        "Input: patient_phone, channel, direction, interaction_type, content."
    )
    args_schema: Type[BaseModel] = LogInteractionInput

    def _run(self, patient_phone: str, channel: str, **kwargs) -> str:
        try:
            conn = _get_db()
            patient = conn.execute(
                "SELECT id FROM patients WHERE phone = ?", (patient_phone,)
            ).fetchone()
            if not patient:
                return f"No patient found with phone {patient_phone}."

            conn.execute(
                """INSERT INTO interactions
                   (patient_id, channel, direction, interaction_type, content, campaign_name)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    patient["id"], channel,
                    kwargs.get("direction", "outbound"),
                    kwargs.get("interaction_type", "follow-up"),
                    kwargs.get("content", ""),
                    kwargs.get("campaign_name"),
                ),
            )
            conn.commit()
            conn.close()
            return f"Interaction logged for patient {patient_phone} via {channel}"
        except Exception as e:
            return f"Error logging interaction: {str(e)}"


class CRMLifecycleReportTool(BaseTool):
    name: str = "crm_lifecycle_report"
    description: str = (
        "Generate a patient lifecycle analytics report. Shows acquisition sources, "
        "treatment completion rates, retention rates, revenue by treatment, "
        "dosha distribution, and churn risk patients. "
        "Input: days for analysis period."
    )
    args_schema: Type[BaseModel] = LifecycleReportInput

    def _run(self, days: int = 30) -> str:
        try:
            conn = _get_db()

            # Total patients
            total = conn.execute("SELECT COUNT(*) as c FROM patients").fetchone()["c"]
            new_patients = conn.execute(
                "SELECT COUNT(*) as c FROM patients WHERE created_at >= datetime('now', ? || ' days')",
                (f"-{days}",),
            ).fetchone()["c"]

            # Acquisition sources
            sources = conn.execute(
                "SELECT source, COUNT(*) as count FROM patients WHERE source IS NOT NULL GROUP BY source ORDER BY count DESC"
            ).fetchall()

            # Dosha distribution
            doshas = conn.execute(
                "SELECT dosha_type, COUNT(*) as count FROM patients WHERE dosha_type IS NOT NULL GROUP BY dosha_type ORDER BY count DESC"
            ).fetchall()

            # Treatment stats
            treatment_stats = conn.execute("""
                SELECT
                    treatment_name,
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                    SUM(cost_inr) as total_revenue,
                    AVG(cost_inr) as avg_cost
                FROM treatments
                GROUP BY treatment_name
                ORDER BY total_revenue DESC
            """).fetchall()

            # Revenue
            revenue = conn.execute(
                "SELECT SUM(paid_inr) as total FROM treatments WHERE created_at >= datetime('now', ? || ' days')",
                (f"-{days}",),
            ).fetchone()["total"] or 0

            # Patients at risk of churning (no interaction in 30+ days)
            churn_risk = conn.execute("""
                SELECT COUNT(*) as c FROM patients p
                WHERE p.status = 'active'
                    AND p.id NOT IN (
                        SELECT patient_id FROM interactions
                        WHERE created_at >= datetime('now', '-30 days')
                    )
                    AND p.id NOT IN (
                        SELECT patient_id FROM treatments
                        WHERE created_at >= datetime('now', '-30 days')
                    )
            """).fetchone()["c"]

            conn.close()

            report = {
                "period": f"Last {days} days",
                "overview": {
                    "total_patients": total,
                    "new_patients": new_patients,
                    "revenue_inr": round(revenue, 2),
                    "churn_risk_patients": churn_risk,
                },
                "acquisition_sources": [dict(s) for s in sources],
                "dosha_distribution": [dict(d) for d in doshas],
                "treatment_performance": [dict(t) for t in treatment_stats],
                "recommendations": [],
            }

            # Auto-generate recommendations
            if churn_risk > 0:
                report["recommendations"].append(
                    f"{churn_risk} patients at churn risk — trigger re-engagement campaign via WhatsApp"
                )
            if new_patients == 0:
                report["recommendations"].append(
                    "Zero new patients this period — increase ad spend and event frequency"
                )

            return json.dumps(report, indent=2, default=str)
        except Exception as e:
            return f"Error generating lifecycle report: {str(e)}"
