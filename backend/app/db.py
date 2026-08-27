import sqlite3
import os
import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

# Database path in workspace root so both backend and dashboard share it
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DB_PATH = os.path.join(BASE_DIR, "lead_management.db")


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initializes the SQLite database schema for leads and workflow errors."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Leads Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                company TEXT,
                requested_service TEXT NOT NULL,
                message TEXT NOT NULL,
                score INTEGER NOT NULL,
                classification TEXT NOT NULL,
                confidence REAL DEFAULT 1.0,
                analysis_mode TEXT DEFAULT 'rule_based',
                provider TEXT DEFAULT 'rule_engine',
                status TEXT DEFAULT 'PENDING_APPROVAL',
                priority TEXT DEFAULT 'Medium',
                next_action TEXT,
                suggested_reply TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Workflow Errors Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workflow_errors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id TEXT,
                error_type TEXT NOT NULL,
                error_message TEXT NOT NULL,
                payload TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()


def save_lead(lead_data: Dict[str, Any]) -> str:
    """Inserts or updates a lead record in the database."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()
        
        lead_id = lead_data.get("lead_id") or f"LEAD-{datetime.now().strftime('%Y%m%d')}-{abs(hash(lead_data.get('email', '')) % 9000 + 1000)}"
        score = int(lead_data.get("score", 0))
        classification = lead_data.get("classification", "cold").lower()
        priority = "High" if score >= 70 else ("Medium" if score >= 40 else "Low")
        
        cursor.execute("""
            INSERT INTO leads (
                lead_id, name, email, company, requested_service, message,
                score, classification, confidence, analysis_mode, provider,
                status, priority, next_action, suggested_reply, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(lead_id) DO UPDATE SET
                score = excluded.score,
                classification = excluded.classification,
                confidence = excluded.confidence,
                analysis_mode = excluded.analysis_mode,
                provider = excluded.provider,
                status = excluded.status,
                priority = excluded.priority,
                next_action = excluded.next_action,
                suggested_reply = excluded.suggested_reply,
                updated_at = excluded.updated_at
        """, (
            lead_id,
            lead_data.get("name", ""),
            lead_data.get("email", ""),
            lead_data.get("company", ""),
            lead_data.get("requested_service", "") or lead_data.get("service_requested", ""),
            lead_data.get("message", ""),
            score,
            classification,
            float(lead_data.get("confidence", 1.0)),
            lead_data.get("analysis_mode", "rule_based"),
            lead_data.get("provider", "rule_engine"),
            lead_data.get("status", "PENDING_APPROVAL"),
            priority,
            lead_data.get("next_action", ""),
            lead_data.get("suggested_reply", "") or lead_data.get("reply", ""),
            lead_data.get("created_at", now),
            now
        ))
        conn.commit()
        return lead_id


def log_workflow_error(error_type: str, error_message: str, lead_id: Optional[str] = None, payload: Optional[Any] = None):
    """Logs an error event into the database."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        payload_str = json.dumps(payload) if isinstance(payload, (dict, list)) else str(payload or "")
        cursor.execute("""
            INSERT INTO workflow_errors (lead_id, error_type, error_message, payload)
            VALUES (?, ?, ?, ?)
        """, (lead_id or "UNKNOWN", error_type, error_message, payload_str))
        conn.commit()


def get_all_leads() -> List[Dict[str, Any]]:
    """Retrieves all lead records ordered by created_at desc."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM leads ORDER BY created_at DESC")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_lead_by_id(lead_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a single lead by its lead_id."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM leads WHERE lead_id = ?", (lead_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def update_lead_status(lead_id: str, new_status: str) -> bool:
    """Updates the status of a specific lead."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()
        cursor.execute("""
            UPDATE leads SET status = ?, updated_at = ? WHERE lead_id = ?
        """, (new_status, now, lead_id))
        conn.commit()
        return cursor.rowcount > 0


def get_workflow_errors(limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieves recent workflow errors."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM workflow_errors ORDER BY created_at DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def seed_sample_leads_if_empty():
    """Seeds the database with diverse, realistic demo leads and errors if empty."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM leads")
        count = cursor.fetchone()[0]
        
        if count > 0:
            return  # Already has data

    sample_leads = [
        {
            "lead_id": "LEAD-20260827-1001",
            "name": "Rahul Das",
            "email": "rahul@example.com",
            "company": "North East Digital Agency",
            "requested_service": "CRM and AI automation",
            "message": "We urgently need help automating our customer support and lead follow-up process.",
            "score": 100,
            "classification": "hot",
            "confidence": 0.98,
            "analysis_mode": "ai",
            "provider": "google_gemini (gemini-1.5-flash)",
            "status": "OPEN",
            "priority": "High",
            "next_action": "Immediate direct callback within 15 minutes by Senior Automation Specialist",
            "suggested_reply": "Hello Rahul Das, thank you for reaching out urgently about CRM and AI automation. We have prioritized your request and our senior team is ready to assist.",
            "created_at": "2026-08-27 09:15:00"
        },
        {
            "lead_id": "LEAD-20260827-1002",
            "name": "Priya Sharma",
            "email": "priya@example.com",
            "company": "Bright SaaS",
            "requested_service": "SaaS operations",
            "message": "We would like to learn more about improving our onboarding workflow.",
            "score": 45,
            "classification": "warm",
            "confidence": 0.92,
            "analysis_mode": "rule_based",
            "provider": "rule_engine",
            "status": "PENDING_APPROVAL",
            "priority": "Medium",
            "next_action": "Send service portfolio deck and schedule standard discovery call within 24 hours",
            "suggested_reply": "Hello Priya Sharma, thank you for contacting us regarding SaaS operations. We would love to share our portfolio and discuss options.",
            "created_at": "2026-08-27 10:20:00"
        },
        {
            "lead_id": "LEAD-20260827-1003",
            "name": "Amit Kumar",
            "email": "amit@example.com",
            "company": "",
            "requested_service": "General inquiry",
            "message": "Please send info.",
            "score": 15,
            "classification": "cold",
            "confidence": 0.85,
            "analysis_mode": "rule_based",
            "provider": "rule_engine",
            "status": "CONTACTED",
            "priority": "Low",
            "next_action": "Enroll in automated nurture sequence",
            "suggested_reply": "Hello Amit Kumar, thank you for your inquiry. We have logged your request and sent over our general brochure.",
            "created_at": "2026-08-27 11:05:00"
        },
        {
            "lead_id": "LEAD-20260827-1004",
            "name": "Sarah Jenkins",
            "email": "sarah.j@apexlogistics.com",
            "company": "Apex Global Logistics",
            "requested_service": "AI & ERP Integration",
            "message": "Critical requirement: ASAP dispatch workflow overhaul across 3 warehouses. Budget approved.",
            "score": 95,
            "classification": "hot",
            "confidence": 0.97,
            "analysis_mode": "ai",
            "provider": "openai (gpt-4o-mini)",
            "status": "OPEN",
            "priority": "High",
            "next_action": "Immediate direct callback within 15 minutes by Senior Automation Specialist",
            "suggested_reply": "Hello Sarah, thank you for contacting us with high urgency regarding AI & ERP Integration. Our enterprise team is reviewing your requirements immediately.",
            "created_at": "2026-08-27 12:40:00"
        },
        {
            "lead_id": "LEAD-20260827-1005",
            "name": "Vikram Malhotra",
            "email": "vikram@fintechpulse.io",
            "company": "Fintech Pulse",
            "requested_service": "Customer Support Automation",
            "message": "Exploring AI chatbots to handle Tier-1 inbound ticketing.",
            "score": 65,
            "classification": "warm",
            "confidence": 0.90,
            "analysis_mode": "ai",
            "provider": "google_gemini (gemini-1.5-flash)",
            "status": "PENDING_APPROVAL",
            "priority": "Medium",
            "next_action": "Send service portfolio deck and schedule standard discovery call within 24 hours",
            "suggested_reply": "Hello Vikram, thank you for reaching out regarding Customer Support Automation. We have extensive experience building AI chatbots for fintech.",
            "created_at": "2026-08-27 13:10:00"
        }
    ]

    for lead in sample_leads:
        save_lead(lead)

    sample_errors = [
        {
            "lead_id": "LEAD-INVALID-001",
            "error_type": "VALIDATION_ERROR",
            "error_message": "Email format invalid: bad-email-format. Message too short (<5 chars).",
            "payload": {"name": "Test User", "email": "bad-email-format", "message": "Hi"}
        },
        {
            "lead_id": "LEAD-INVALID-002",
            "error_type": "MISSING_FIELD",
            "error_message": "Requested service is required and cannot be blank.",
            "payload": {"name": "Jane Doe", "email": "jane@example.com", "requested_service": ""}
        }
    ]

    for err in sample_errors:
        log_workflow_error(err["error_type"], err["error_message"], err["lead_id"], err["payload"])


def reset_database_clean():
    """Wipes all test leads and re-seeds clean, unique sample records."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM leads")
        cursor.execute("DELETE FROM workflow_errors")
        conn.commit()
    seed_sample_leads_if_empty()

