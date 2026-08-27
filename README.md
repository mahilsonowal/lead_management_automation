# AI-Powered Lead Management and Follow-Up Automation System

> **Enterprise-grade Inbound Lead Qualification, Scoring, Multi-Model AI Analysis, and Analytics Platform**  
> Built with **n8n**, **Python (FastAPI & Pydantic v2)**, **SQLite**, and **Streamlit / Plotly**.

---

## 1. Executive Summary & Business Problem

### The Business Challenge
In fast-moving service agencies, SaaS startups, and consultancy practices, inbound leads often slip through the cracks or languish for hours before human review. Critical problems include:
* **Slow Speed-to-Lead:** Research shows contacting a lead within 15 minutes yields a 7x higher qualification conversion rate compared to an hour delay.
* **Unqualified Noise:** Sales teams spend valuable hours manually filtering spam, missing info, and low-budget inquiries.
* **Inconsistent Qualification:** Different representatives evaluate lead potential subjectively without standardized scoring rules.
* **High AI API Risk:** Relying purely on third-party AI APIs without fallbacks risks total pipeline downtime when rate limits or network outages occur.

### The Proposed Solution
An end-to-end, resilient automation ecosystem that:
1. **Captures and Validates:** Ingests leads through customizable forms, sanitizing and strictly validating email, message depth, and company details.
2. **Scores and Classifies:** Employs dual-mode intelligence — an AI provider abstraction layer (**Google Gemini / OpenAI / Ollama**) backed by a 100% deterministic rule-based fallback scoring engine (0–100 pts).
3. **Automates Operational Next Steps:** Dynamically generates prioritized follow-up tasks (15-min executive callback for Hot leads vs. nurture sequences for Cold leads) and drafts personalized email responses.
4. **Tracks and Audits:** Persists all submissions, status transitions, and validation rejections in SQLite, surfacing real-time telemetry through an executive **Streamlit & Plotly** dashboard.

---

## 2. System Architecture & Component Roles

```text
 ┌─────────────────────────┐
 │ Inbound Lead Submissions│
 └───────────┬─────────────┘
             │
             ▼
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │                                   n8n Workflow Engine                       │
 │  ┌───────────────────┐     ┌───────────────────┐     ┌───────────────────┐  │
 │  │ Lead Form Trigger │ ──> │ Normalize Fields  │ ──> │ Validate Schema   │  │
 │  └───────────────────┘     └───────────────────┘     └─────────┬─────────┘  │
 └────────────────────────────────────────────────────────────────┼────────────┘
                                                                  │ (HTTP POST)
                                                                  ▼
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │                             FastAPI Microservice (Port 8000)                │
 │  ┌───────────────────────────────────────────────────────────────────────┐  │
 │  │ Pydantic Request Validation (Field Cleaners, EmailStr, Min/Max Limits)│  │
 │  └──────────────────────────────────┬────────────────────────────────────┘  │
 │                                     │                                       │
 │                    /────────────────┴────────────────\                      │
 │                   < AI Provider Configured & Active?  >                     │
 │                    \────────────────┬────────────────/                      │
 │                                     │                                       │
 │                   [Yes]             │             [No / Failure]            │
 │                     │               │                    │                  │
 │                     ▼               │                    ▼                  │
 │         ┌───────────────────────┐   │        ┌───────────────────────┐      │
 │         │ Gemini / OpenAI/Ollama│   │        │ Deterministic Scoring │      │
 │         │ (Structured JSON Mode)│   │        │ Engine (0 to 100 pts) │      │
 │         └───────────┬───────────┘   │        └───────────┬───────────┘      │
 │                     │               │                    │                  │
 │                     ▼               │                    ▼                  │
 │        ┌────────────────────────────┴────────────────────────────┐          │
 │        │ Auto-Persistence Layer: Leads & Workflow Errors Tables │          │
 │        └────────────────────────────┬────────────────────────────┘          │
 └─────────────────────────────────────┼───────────────────────────────────────┘
                                       │ (SQLite DB: lead_management.db)
                                       ▼
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │                         Streamlit Analytics Hub (Port 8501)                 │
 │  ├── 📊 Executive Overview & Plotly Visualizations                          │
 │  ├── 📋 Lead Pipeline Table with Multi-Column Filters & CSV Export          │
 │  ├── 🔍 Lead Deep-Dive Profile & Interactive Status Management              │
 │  ├── ⚠️ Validation Error Logs & Malformed Payload Inspector                 │
 │  └── 🚀 Live Lead Intake Simulator                                          │
 └─────────────────────────────────────────────────────────────────────────────┘
```

### Architectural Roles:
* **n8n Workflow Canvas:** Orchestrates ingestion, field mapping, branch routing, mock email output, and error-trigger incident alerts.
* **Python FastAPI Service:** Encapsulates business logic, data models, AI provider abstraction, timeout/retry mechanics, and fallback scoring.
* **SQLite Database:** Zero-configuration, ACID-compliant persistence layer storing lead records and audit logs.
* **Streamlit Dashboard:** Real-time visual interface for executives and operations specialists to monitor KPIs, review drafts, and export pipeline data.

---

## 3. Qualification & Scoring Algorithm (0–100 Points)

| Rule | Signal Criteria | Points | Rationale |
|---|---|---|---|
| **Urgency Detection** | Contains keywords: *urgent, ASAP, immediately, emergency, deadline, critical* | **+30 pts** | Fast-tracks time-sensitive opportunities to senior specialists. |
| **High-Value Service** | Matches: *AI, automation, CRM, customer support, workflow, pipeline* | **+25 pts** | Prioritizes core high-revenue service offerings. |
| **Company Presence** | Legitimate company name supplied | **+20 pts** | Indicates B2B readiness and institutional budget. |
| **Email Validity** | Strict RFC-compliant email verification | **+15 pts** | Ensures deliverability and authentic domain reputation. |
| **Message Depth** | Inquiry message length $\ge$ 30 characters | **+10 pts** | Signals genuine intent and detailed project scope. |

### Classification Tiers:
* 🔥 **HOT Lead (70–100 pts):** Operational Action: *Immediate direct callback within 15 minutes by Senior Automation Specialist.* Status: `OPEN`.
* ☀️ **WARM Lead (40–69 pts):** Operational Action: *Send service portfolio deck and schedule standard discovery call within 24 hours.* Status: `PENDING_APPROVAL`.
* ❄️ **COLD Lead (< 40 pts):** Operational Action: *Enroll in automated nurture sequence.* Status: `PENDING_APPROVAL`.

---

## 4. Multi-Model AI Provider Abstraction

The API features an extensible provider abstraction (`app/ai/`) supporting:
1. **Google Gemini API** (`gemini-1.5-flash`, `gemini-1.5-pro`): Native JSON output mode.
2. **OpenAI API** (`gpt-4o`, `gpt-4o-mini`): JSON object schema.
3. **Local Ollama** (`llama3.2`, `mistral`): 100% private, local offline execution.
4. **Deterministic Rule Engine** (`none`): Zero API latency, zero cost.

### Bulletproof Reliability & Fallbacks
* **Timeout Protection:** Configurable per-call timeout (`AI_TIMEOUT_SECONDS=8.0`).
* **Retry Loop:** Up to 2 exponential backoff retries on transient network faults.
* **Instant Fallback:** If any AI provider times out, encounters rate limits, has missing credentials, or produces malformed JSON, the system **automatically falls back to deterministic rule scoring** (`analysis_mode: "rule_based_fallback"`).

---

## 5. Security & Data Integrity

1. **API Key Isolation:** API credentials reside strictly in `.env` and are loaded via `python-dotenv`. They are never logged, serialized, or returned in HTTP responses.
2. **Strict Input Sanitization:** Pydantic validators strip whitespace, normalize casing, enforce length boundaries, and validate email syntax.
3. **Sanitized Telemetry:** Logging outputs only email domains (e.g. `@example.com`) and error classifications, avoiding PII exposure in server logs.
4. **CORS & Middleware:** Configured with standard security middleware and custom exception formatting.

---

## 6. Installation & Quick Start Guide

### Prerequisites
* Python 3.10+ (Tested on Python 3.13)
* Node.js & npm (optional, for localtunnel / n8n CLI)
* n8n Cloud account or local n8n instance

### Step 1: Clone and Set Up Virtual Environment
```powershell
# Open Windows PowerShell
cd c:\Users\mahil\OneDrive\Desktop\lead-management-automation\backend

# Create virtual environment
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Configure Environment Variables
Copy `.env.example` to `.env`:
```powershell
cp .env.example .env
```
*(Default settings run in high-speed deterministic rule mode. To activate Gemini/OpenAI, add your API key in `.env`).*

### Step 3: Run Automated Tests
```powershell
pytest -v
```
*(All 16 unit, integration, and reliability tests will execute and pass).*

### Step 4: Launch FastAPI Microservice
```powershell
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
* **Swagger API Docs:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* **Health Endpoint:** [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

### Step 5: Launch Streamlit Analytics Dashboard
Open a second PowerShell window:
```powershell
cd c:\Users\mahil\OneDrive\Desktop\lead-management-automation
.\backend\.venv\Scripts\Activate.ps1
streamlit run dashboard/app.py
```
* **Dashboard URL:** [http://localhost:8501](http://localhost:8501)

### Step 6: Import n8n Workflow
1. In your n8n dashboard, click **Add Workflow** → **Import from File**.
2. Select [`phase1_lead_management_workflow.json`](file:///c:/Users/mahil/OneDrive/Desktop/lead-management-automation/phase1_lead_management_workflow.json).
3. Import [`error_handling_workflow.json`](file:///c:/Users/mahil/OneDrive/Desktop/lead-management-automation/error_handling_workflow.json) for global incident handling.

---

## 7. Automated Test Suite Summary (16 Passed)

```text
============================= test session starts =============================
tests/test_ai_analysis.py::test_ai_structured_output_normalization PASSED [  6%]
tests/test_ai_analysis.py::test_ai_base_provider_markdown_fence_cleaning PASSED [ 12%]
tests/test_ai_analysis.py::test_ai_manager_fallback_on_timeout PASSED    [ 18%]
tests/test_ai_analysis.py::test_ai_manager_fallback_on_malformed_json PASSED [ 25%]
tests/test_ai_analysis.py::test_ai_manager_successful_ai_response PASSED [ 31%]
tests/test_analyze_lead.py::test_health_check PASSED                     [ 37%]
tests/test_analyze_lead.py::test_hot_lead_scoring PASSED                 [ 43%]
tests/test_analyze_lead.py::test_warm_lead_scoring PASSED                [ 50%]
tests/test_analyze_lead.py::test_cold_lead_scoring PASSED                [ 56%]
tests/test_analyze_lead.py::test_invalid_email_validation_error PASSED   [ 62%]
tests/test_analyze_lead.py::test_missing_name_validation_error PASSED    [ 68%]
tests/test_analyze_lead.py::test_missing_message_validation_error PASSED [ 75%]
tests/test_analyze_lead.py::test_missing_requested_service_validation_error PASSED [ 81%]
tests/test_reliability_phase5.py::test_duplicate_lead_upsert PASSED      [ 87%]
tests/test_reliability_phase5.py::test_database_graceful_error_handling PASSED [ 93%]
tests/test_reliability_phase5.py::test_error_logging_audit_trail PASSED  [100%]
======================= 16 passed in 6.53s =======================
```
