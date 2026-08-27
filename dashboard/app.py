import os
import sys
import json
from datetime import datetime
import pandas as pd
# pyrefly: ignore [missing-import]
import plotly.express as px
# pyrefly: ignore [missing-import]
import plotly.graph_objects as go
# pyrefly: ignore [missing-import]
import streamlit as st

# Ensure backend package can be imported
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# pyrefly: ignore [missing-import]
from app.db import (
    init_db,
    get_all_leads,
    get_lead_by_id,
    update_lead_status,
    get_workflow_errors,
    seed_sample_leads_if_empty,
    save_lead,
    log_workflow_error
)
# pyrefly: ignore [missing-import]
from app.scorer import analyze_lead_rules
# pyrefly: ignore [missing-import]
from app.models import LeadInput

# -----------------------------------------------------------------------------
# Streamlit Page Configuration & Styling
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="AI Lead Intelligence Hub",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern, premium aesthetics
st.markdown("""
<style>
    /* Metric Card Styling */
    .metric-container {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 20px;
        color: white;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
        margin-bottom: 15px;
    }
    .metric-value {
        font-size: 2.2rem;
        font-weight: 700;
        margin: 5px 0;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .badge-hot {
        background-color: #ef4444;
        color: white;
        padding: 4px 10px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.8rem;
    }
    .badge-warm {
        background-color: #f59e0b;
        color: white;
        padding: 4px 10px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.8rem;
    }
    .badge-cold {
        background-color: #3b82f6;
        color: white;
        padding: 4px 10px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.8rem;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 10px 20px;
        border-radius: 8px 8px 0 0;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# Initialize and seed database if empty
init_db()
seed_sample_leads_if_empty()


# -----------------------------------------------------------------------------
# Data Loader Functions
# -----------------------------------------------------------------------------
def load_leads_df() -> pd.DataFrame:
    leads = get_all_leads()
    if not leads:
        return pd.DataFrame()
    df = pd.DataFrame(leads)
    if "created_at" in df.columns:
        df["created_at"] = pd.to_datetime(df["created_at"], format="mixed", utc=True, errors="coerce")
    return df


def load_errors_df() -> pd.DataFrame:
    errors = get_workflow_errors()
    if not errors:
        return pd.DataFrame()
    df = pd.DataFrame(errors)
    if "created_at" in df.columns:
        df["created_at"] = pd.to_datetime(df["created_at"], format="mixed", utc=True, errors="coerce")
    return df


leads_df = load_leads_df()
errors_df = load_errors_df()


# -----------------------------------------------------------------------------
# Sidebar Navigation & System Telemetry
# -----------------------------------------------------------------------------
with st.sidebar:
    st.title("Lead Automation")
    st.caption("AI-Powered Ingestion & Intelligence Hub")
    
    st.markdown("---")
    
    navigation = st.radio(
        "Navigation",
        [
            "Executive Overview",
            "Lead Pipeline Table",
            "Lead Deep-Dive Profile",
            "Error & Audit Logs",
            "Lead Intake Simulator"
        ]
    )
    
    st.markdown("---")
    st.subheader("System Telemetry")
    st.write(f"📁 **Database:** `lead_management.db`")
    st.write(f"📦 **Total Leads:** `{len(leads_df)} records`")
    st.write(f"🚨 **Logged Errors:** `{len(errors_df)} events`")
    
    if st.button("🌱 Refresh & Seed Sample Data"):
        seed_sample_leads_if_empty()
        st.success("Sample leads verified!")
        st.rerun()


# -----------------------------------------------------------------------------
# TAB 1: EXECUTIVE OVERVIEW
# -----------------------------------------------------------------------------
if "Executive Overview" in navigation:
    st.title("📊 Executive Lead Intelligence Overview")
    st.markdown("Real-time pipeline metrics, AI qualification breakdown, and inbound demand analytics.")

    if leads_df.empty:
        st.info("No lead records found in database. Use the Simulator or click 'Seed Sample Data' in the sidebar.")
    else:
        total_leads = len(leads_df)
        hot_leads = len(leads_df[leads_df["classification"].str.lower() == "hot"])
        warm_leads = len(leads_df[leads_df["classification"].str.lower() == "warm"])
        cold_leads = len(leads_df[leads_df["classification"].str.lower() == "cold"])
        
        open_followups = len(leads_df[leads_df["status"].isin(["OPEN", "PENDING_APPROVAL"])])
        avg_score = leads_df["score"].mean() if total_leads > 0 else 0

        # KPI Metric Cards
        col1, col2, col3, col4, col5, col6 = st.columns(6)

        with col1:
            st.markdown(f"""
            <div class="metric-container">
                <div class="metric-label">Total Leads</div>
                <div class="metric-value">{total_leads}</div>
                <span style="color: #38bdf8;">100% Ingested</span>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            hot_pct = (hot_leads / total_leads * 100) if total_leads else 0
            st.markdown(f"""
            <div class="metric-container">
                <div class="metric-label">Hot Leads</div>
                <div class="metric-value" style="color: #ef4444;">{hot_leads}</div>
                <span style="color: #ef4444;">{hot_pct:.1f}% High Priority</span>
            </div>
            """, unsafe_allow_html=True)

        with col3:
            warm_pct = (warm_leads / total_leads * 100) if total_leads else 0
            st.markdown(f"""
            <div class="metric-container">
                <div class="metric-label">Warm Leads</div>
                <div class="metric-value" style="color: #f59e0b;">{warm_leads}</div>
                <span style="color: #f59e0b;">{warm_pct:.1f}% Discovery</span>
            </div>
            """, unsafe_allow_html=True)

        with col4:
            cold_pct = (cold_leads / total_leads * 100) if total_leads else 0
            st.markdown(f"""
            <div class="metric-container">
                <div class="metric-label">Cold Leads</div>
                <div class="metric-value" style="color: #3b82f6;">{cold_leads}</div>
                <span style="color: #3b82f6;">{cold_pct:.1f}% Nurturing</span>
            </div>
            """, unsafe_allow_html=True)

        with col5:
            st.markdown(f"""
            <div class="metric-container">
                <div class="metric-label">Pending Follow-Ups</div>
                <div class="metric-value" style="color: #a855f7;">{open_followups}</div>
                <span style="color: #c084fc;">Action Required</span>
            </div>
            """, unsafe_allow_html=True)

        with col6:
            st.markdown(f"""
            <div class="metric-container">
                <div class="metric-label">Avg Lead Score</div>
                <div class="metric-value" style="color: #10b981;">{avg_score:.1f}</div>
                <span style="color: #34d399;">Out of 100 pts</span>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")

        # Row 1: Charts
        chart_col1, chart_col2 = st.columns(2)

        with chart_col1:
            st.subheader("🎯 Lead Classification Distribution")
            class_counts = leads_df["classification"].str.capitalize().value_counts().reset_index()
            class_counts.columns = ["Classification", "Count"]
            
            color_map = {"Hot": "#ef4444", "Warm": "#f59e0b", "Cold": "#3b82f6"}
            fig_pie = px.pie(
                class_counts,
                names="Classification",
                values="Count",
                color="Classification",
                color_discrete_map=color_map,
                hole=0.45
            )
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            fig_pie.update_layout(margin=dict(t=20, b=20, l=20, r=20), height=320)
            st.plotly_chart(fig_pie, use_container_width=True)

        with chart_col2:
            st.subheader("💼 Inbound Demand by Requested Service")
            service_counts = leads_df["requested_service"].value_counts().reset_index()
            service_counts.columns = ["Service", "Inquiries"]
            
            fig_bar = px.bar(
                service_counts,
                x="Inquiries",
                y="Service",
                orientation="h",
                color="Inquiries",
                color_continuous_scale="Blues"
            )
            fig_bar.update_layout(yaxis={'categoryorder':'total ascending'}, margin=dict(t=20, b=20, l=20, r=20), height=320)
            st.plotly_chart(fig_bar, use_container_width=True)

        # Row 2: Charts
        chart_col3, chart_col4 = st.columns(2)

        with chart_col3:
            st.subheader("📈 Lead Score Distribution (0-100)")
            fig_hist = px.histogram(
                leads_df,
                x="score",
                nbins=10,
                color="classification",
                color_discrete_map={"hot": "#ef4444", "warm": "#f59e0b", "cold": "#3b82f6"},
                labels={"score": "Qualification Score"}
            )
            fig_hist.update_layout(margin=dict(t=20, b=20, l=20, r=20), height=300)
            st.plotly_chart(fig_hist, use_container_width=True)

        with chart_col4:
            st.subheader("⚡ Pipeline Status Breakdown")
            status_counts = leads_df["status"].value_counts().reset_index()
            status_counts.columns = ["Status", "Count"]
            fig_status = px.bar(
                status_counts,
                x="Status",
                y="Count",
                color="Status",
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig_status.update_layout(margin=dict(t=20, b=20, l=20, r=20), height=300)
            st.plotly_chart(fig_status, use_container_width=True)


# -----------------------------------------------------------------------------
# TAB 2: LEAD PIPELINE TABLE
# -----------------------------------------------------------------------------
elif "Lead Pipeline Table" in navigation:
    st.title("📋 Lead Pipeline Management")
    st.markdown("Filter, search, inspect, and export all inbound lead records.")

    if leads_df.empty:
        st.info("No leads available.")
    else:
        # Filter controls
        filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)

        with filter_col1:
            class_filter = st.selectbox("Classification Filter", ["All", "Hot", "Warm", "Cold"])
        with filter_col2:
            status_filter = st.selectbox("Status Filter", ["All"] + sorted(leads_df["status"].unique().tolist()))
        with filter_col3:
            priority_filter = st.selectbox("Priority Filter", ["All", "High", "Medium", "Low"])
        with filter_col4:
            search_query = st.text_input("🔍 Search (Name, Email, Company)", "")

        filtered_df = leads_df.copy()

        if class_filter != "All":
            filtered_df = filtered_df[filtered_df["classification"].str.lower() == class_filter.lower()]
        if status_filter != "All":
            filtered_df = filtered_df[filtered_df["status"] == status_filter]
        if priority_filter != "All":
            filtered_df = filtered_df[filtered_df["priority"] == priority_filter]
        if search_query:
            query = search_query.lower()
            filtered_df = filtered_df[
                filtered_df["name"].str.lower().str.contains(query) |
                filtered_df["email"].str.lower().str.contains(query) |
                filtered_df["company"].str.lower().str.contains(query) |
                filtered_df["requested_service"].str.lower().str.contains(query)
            ]

        st.caption(f"Showing **{len(filtered_df)}** of **{len(leads_df)}** total leads.")

        # Display table
        display_columns = [
            "lead_id", "name", "email", "company", "requested_service",
            "score", "classification", "priority", "status", "created_at"
        ]
        available_cols = [c for c in display_columns if c in filtered_df.columns]
        
        st.dataframe(
            filtered_df[available_cols],
            use_container_width=True,
            hide_index=True
        )

        # Export CSV Button
        csv = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Export Filtered Leads to CSV",
            data=csv,
            file_name=f"leads_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )


# -----------------------------------------------------------------------------
# TAB 3: LEAD DEEP-DIVE PROFILE
# -----------------------------------------------------------------------------
elif "Lead Deep-Dive Profile" in navigation:
    st.title("🔍 Lead Deep-Dive & Action Center")
    st.markdown("Detailed breakdown of lead scoring, AI qualification analysis, and drafted response.")

    if leads_df.empty:
        st.info("No leads available.")
    else:
        lead_options = [f"{row['lead_id']} - {row['name']} ({row['company'] or 'Independent'})" for _, row in leads_df.iterrows()]
        selected_option = st.selectbox("Select Lead to Inspect:", lead_options)
        selected_lead_id = selected_option.split(" - ")[0]

        lead = get_lead_by_id(selected_lead_id)

        if lead:
            col_left, col_right = st.columns([1.2, 1])

            with col_left:
                st.subheader(f"👤 {lead['name']}")
                st.write(f"📧 **Email:** [{lead['email']}](mailto:{lead['email']})")
                st.write(f"🏢 **Company:** {lead['company'] or 'Not provided (Independent)'}")
                st.write(f"🛠️ **Requested Service:** `{lead['requested_service']}`")
                st.write(f"🕒 **Received At:** `{lead['created_at']}`")
                st.write(f"🤖 **Analysis Mode:** `{lead['analysis_mode']}` via `{lead['provider']}`")
                
                st.markdown("#### 💬 Submitted Inquiry Message:")
                st.info(f"\"{lead['message']}\"")

            with col_right:
                st.subheader("⚡ Qualification Scorecard")
                
                # Badge color logic
                score = lead["score"]
                classification = lead["classification"].upper()
                badge_color = "#ef4444" if score >= 70 else ("#f59e0b" if score >= 40 else "#3b82f6")
                
                st.markdown(f"""
                <div style="background-color: {badge_color}; color: white; padding: 15px; border-radius: 10px; text-align: center; margin-bottom: 15px;">
                    <h2 style="margin: 0; color: white;">{score} / 100 PTS</h2>
                    <h4 style="margin: 5px 0 0 0; color: white;">[{classification} LEAD] • Priority: {lead['priority']}</h4>
                </div>
                """, unsafe_allow_html=True)

                st.markdown(f"**🎯 Recommended Operational Action:**")
                st.success(f"{lead['next_action']}")

                # Status management
                st.markdown("#### 🔄 Update Lead Status:")
                new_status = st.selectbox(
                    "Current Status:",
                    ["PENDING_APPROVAL", "OPEN", "CONTACTED", "CLOSED"],
                    index=["PENDING_APPROVAL", "OPEN", "CONTACTED", "CLOSED"].index(lead["status"]) if lead["status"] in ["PENDING_APPROVAL", "OPEN", "CONTACTED", "CLOSED"] else 0
                )
                if st.button("Save Status Change"):
                    update_lead_status(lead["lead_id"], new_status)
                    st.success(f"Status updated to '{new_status}'!")
                    st.rerun()

            st.markdown("---")
            st.subheader("✉️ Contextual Email Response Draft")
            st.text_area("Drafted Reply Message", value=lead["suggested_reply"], height=120)
            
            email_col1, email_col2 = st.columns([1, 4])
            with email_col1:
                if st.button("✅ Approve & Mark Contacted"):
                    update_lead_status(lead["lead_id"], "CONTACTED")
                    st.success("Lead updated to 'CONTACTED'!")
                    st.rerun()


# -----------------------------------------------------------------------------
# TAB 4: ERROR & AUDIT LOGS
# -----------------------------------------------------------------------------
elif "Error & Audit Logs" in navigation:
    st.title("⚠️ Workflow Error Logs & Audit Trail")
    st.markdown("Monitor ingestion validation errors, pipeline issues, and raw malformed payloads.")

    if errors_df.empty:
        st.success("🎉 No workflow errors recorded! Pipeline is 100% healthy.")
    else:
        err_col1, err_col2 = st.columns([1, 3])
        with err_col1:
            st.metric("Total Logged Failures", len(errors_df))
        with err_col2:
            st.caption("All validation failures and malformed payloads are automatically logged by the API error handlers.")

        st.dataframe(
            errors_df[["id", "lead_id", "error_type", "error_message", "created_at"]],
            use_container_width=True,
            hide_index=True
        )

        st.markdown("---")
        st.subheader("Inspect Malformed Payload")
        error_options = [f"Error #{row['id']} - {row['error_type']} ({row['lead_id']})" for _, row in errors_df.iterrows()]
        selected_err_str = st.selectbox("Select error to inspect:", error_options)
        selected_err_id = int(selected_err_str.split(" - ")[0].replace("Error #", ""))

        selected_row = errors_df[errors_df["id"] == selected_err_id].iloc[0]
        st.write(f"**Error Message:** `{selected_row['error_message']}`")
        st.write(f"**Timestamp:** `{selected_row['created_at']}`")
        st.code(selected_row["payload"], language="json")


# -----------------------------------------------------------------------------
# TAB 5: LEAD INTAKE SIMULATOR
# -----------------------------------------------------------------------------
elif "Lead Intake Simulator" in navigation:
    st.title("🚀 Live Lead Ingestion Simulator")
    st.markdown("Simulate lead form submissions directly to test qualification scoring and database storage.")

    # Preset profiles
    p_col1, p_col2, p_col3 = st.columns(3)
    
    preset_name = ""
    preset_email = ""
    preset_company = ""
    preset_service = ""
    preset_message = ""

    if p_col1.button("🔥 Load Hot Lead (Rahul Das)"):
        preset_name = "Rahul Das"
        preset_email = "rahul@example.com"
        preset_company = "North East Digital Agency"
        preset_service = "CRM and AI automation"
        preset_message = "We urgently need help automating our customer support and lead follow-up process."

    if p_col2.button("☀️ Load Warm Lead (Priya Sharma)"):
        preset_name = "Priya Sharma"
        preset_email = "priya@example.com"
        preset_company = "Bright SaaS"
        preset_service = "SaaS operations"
        preset_message = "We would like to learn more about improving our onboarding workflow."

    if p_col3.button("❄️ Load Cold Lead (Amit Kumar)"):
        preset_name = "Amit Kumar"
        preset_email = "amit@example.com"
        preset_company = ""
        preset_service = "General inquiry"
        preset_message = "Please send info."

    with st.form("lead_simulation_form"):
        form_name = st.text_input("Full Name *", value=preset_name)
        form_email = st.text_input("Email Address *", value=preset_email)
        form_company = st.text_input("Company Name", value=preset_company)
        form_service = st.text_input("Requested Service *", value=preset_service)
        form_message = st.text_area("Inquiry Message *", value=preset_message)
        
        submitted = st.form_submit_button("🚀 Ingest and Analyze Lead")

        if submitted:
            if not form_name or not form_email or not form_service or not form_message:
                st.error("Please fill all required fields (*).")
            else:
                try:
                    lead_input = LeadInput(
                        name=form_name,
                        email=form_email,
                        company=form_company,
                        requested_service=form_service,
                        message=form_message
                    )
                    
                    # Run qualification analysis
                    res = analyze_lead_rules(lead_input)
                    
                    # Persist to database
                    lead_dict = {
                        "name": lead_input.name,
                        "email": lead_input.email,
                        "company": lead_input.company,
                        "requested_service": lead_input.requested_service,
                        "message": lead_input.message,
                        "score": res.score,
                        "classification": res.classification,
                        "confidence": 1.0,
                        "analysis_mode": "simulator",
                        "provider": "rule_engine",
                        "status": "OPEN" if res.score >= 70 else "PENDING_APPROVAL",
                        "next_action": res.next_action,
                        "suggested_reply": res.reply
                    }
                    new_id = save_lead(lead_dict)
                    
                    st.success(f"🎉 Lead successfully analyzed and saved! (Assigned Lead ID: `{new_id}`)")
                    st.json({
                        "classification": res.classification,
                        "score": res.score,
                        "next_action": res.next_action,
                        "reply": res.reply
                    })
                except Exception as exc:
                    st.error(f"Validation Failed: {exc}")
                    log_workflow_error(
                        error_type="SIMULATOR_VALIDATION_ERROR",
                        error_message=str(exc),
                        payload={"name": form_name, "email": form_email}
                    )
