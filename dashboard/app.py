import os
import sys
import json
from datetime import datetime
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Ensure backend package can be imported
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

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
from app.scorer import analyze_lead_rules
from app.models import LeadInput

# -----------------------------------------------------------------------------
# Streamlit Page Configuration
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Lead Console - Admin Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# Clean White Enterprise UI Theme (Matching Dropbox Admin Console)
# -----------------------------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    /* Global Pure White Theme */
    html, body, [class*="css"], .stApp {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
        background-color: #ffffff !important;
        color: #111827 !important;
    }

    /* Override Default Streamlit Header */
    header[data-testid="stHeader"] {
        background-color: #ffffff !important;
        border-bottom: 1px solid #f3f4f6 !important;
        height: 3.5rem !important;
        z-index: 50 !important;
    }

    [data-testid="stToolbar"] {
        color: #111827 !important;
    }

    /* Container Responsive Padding (Clearance for top navigation) */
    .block-container {
        padding-top: 5rem !important;
        padding-bottom: 2.5rem !important;
        padding-left: clamp(1rem, 3vw, 2.5rem) !important;
        padding-right: clamp(1rem, 3vw, 2.5rem) !important;
        max-width: 1320px !important;
    }

    /* Clean Light Off-White Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #f9fafb !important;
        border-right: 1px solid #e5e7eb !important;
    }
    
    section[data-testid="stSidebar"] * {
        color: #374151 !important;
    }

    section[data-testid="stSidebar"] hr {
        border-color: #e5e7eb !important;
        margin: 12px 0 !important;
    }

    /* Hide ugly circular radio buttons; make sidebar items sleek clickable pills */
    div[data-testid="stRadio"] label > div:first-child {
        display: none !important;
    }

    div[data-testid="stRadio"] [role="radiogroup"] {
        gap: 3px !important;
    }

    div[data-testid="stRadio"] label {
        padding: 9px 14px !important;
        border-radius: 6px !important;
        cursor: pointer !important;
        transition: all 0.15s ease !important;
        margin-bottom: 2px !important;
        background-color: transparent !important;
        border: 1px solid transparent !important;
    }

    div[data-testid="stRadio"] label:hover {
        background-color: #f3f4f6 !important;
    }

    div[data-testid="stRadio"] label:has(input:checked),
    div[data-testid="stRadio"] label[data-checked="true"] {
        background-color: #edeef0 !important;
        border: 1px solid #e2e4e8 !important;
    }

    div[data-testid="stRadio"] label:has(input:checked) p,
    div[data-testid="stRadio"] label[data-checked="true"] p {
        color: #111827 !important;
        font-weight: 600 !important;
    }

    /* Responsive Top Header Bar */
    .top-header-bar {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        margin-bottom: 20px;
        padding-bottom: 14px;
        border-bottom: 1px solid #f3f4f6;
    }

    .search-pill-container {
        flex: 1 1 320px;
        max-width: 580px;
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 20px;
        padding: 7px 16px;
        display: flex;
        align-items: center;
        box-shadow: 0 1px 2px rgba(0,0,0,0.03);
    }

    .search-pill-container input {
        border: none;
        outline: none;
        width: 100%;
        font-size: 0.85rem;
        color: #4b5563;
        background: transparent;
    }

    .user-avatar-badge {
        width: 32px;
        height: 32px;
        border-radius: 50%;
        background-color: #ea580c;
        color: #ffffff;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 600;
        font-size: 0.8rem;
    }

    /* To-Do Alert Banners (Directly matching screenshot) */
    .todo-banner {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 12px 16px;
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        justify-content: space-between;
        gap: 10px;
        margin-bottom: 10px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.02);
    }

    .todo-icon-amber {
        background-color: #fef3c7;
        color: #b45309;
        width: 34px;
        height: 34px;
        border-radius: 6px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        font-size: 0.95rem;
        flex-shrink: 0;
    }

    .todo-icon-blue {
        background-color: #e0f2fe;
        color: #0369a1;
        width: 34px;
        height: 34px;
        border-radius: 6px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        font-size: 0.95rem;
        flex-shrink: 0;
    }

    .todo-content {
        flex: 1 1 240px;
    }

    .todo-title {
        font-size: 0.88rem;
        font-weight: 600;
        color: #111827;
    }

    .todo-subtitle {
        font-size: 0.78rem;
        color: #6b7280;
    }

    .badge-recommended {
        background-color: #2563eb;
        color: #ffffff;
        font-size: 0.68rem;
        font-weight: 600;
        padding: 2px 6px;
        border-radius: 4px;
        margin-left: 6px;
    }

    /* Executive White Card Container */
    .white-card {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: clamp(14px, 2vw, 20px);
        margin-bottom: 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.03);
    }

    .card-title {
        font-size: 0.95rem;
        font-weight: 700;
        color: #111827;
        margin-bottom: 2px;
    }

    .card-subtitle {
        font-size: 0.8rem;
        color: #6b7280;
        margin-bottom: 12px;
    }

    /* Status Badges */
    .status-badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .badge-hot { background-color: #fef2f2; color: #dc2626; border: 1px solid #fecaca; }
    .badge-warm { background-color: #fffbeb; color: #d97706; border: 1px solid #fde68a; }
    .badge-cold { background-color: #eff6ff; color: #2563eb; border: 1px solid #bfdbfe; }
    .badge-success { background-color: #f0fdf4; color: #16a34a; border: 1px solid #bbf7d0; }

    /* Button Styling */
    .stButton > button {
        border-radius: 6px !important;
        font-weight: 500 !important;
        font-size: 0.82rem !important;
        padding: 5px 12px !important;
        border: 1px solid #d1d5db !important;
        background-color: #ffffff !important;
        color: #111827 !important;
        transition: all 0.12s ease !important;
    }
    .stButton > button:hover {
        background-color: #f9fafb !important;
        border-color: #9ca3af !important;
    }

    /* Media queries */
    @media (max-width: 768px) {
        .search-pill-container { max-width: 100%; }
        .todo-banner { flex-direction: column; align-items: flex-start; }
    }
</style>
""", unsafe_allow_html=True)

# Initialize database
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
# Clean Sidebar Navigation (No Radio Dots)
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("""
    <div style="display: flex; align-items: center; margin-bottom: 16px; padding-top: 4px;">
        <div style="width: 28px; height: 28px; background: #2563eb; border-radius: 6px; display: flex; align-items: center; justify-content: center; color: white; font-weight: 700; font-size: 14px; margin-right: 10px;">L</div>
        <div>
            <div style="color: #111827; font-weight: 700; font-size: 0.98rem; line-height: 1.2;">Admin Console</div>
            <div style="color: #6b7280; font-size: 0.74rem;">Lead Operations</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<p style='font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.08em; color: #9ca3af !important; font-weight: 700; margin: 14px 0 4px 0;'>Navigation</p>", unsafe_allow_html=True)
    
    navigation = st.radio(
        "Navigation",
        [
            "Dashboard Overview",
            "Lead Pipeline Table",
            "Lead Detail Profile",
            "Incident & Audit Logs",
            "Lead Intake Simulator"
        ],
        label_visibility="collapsed"
    )
    
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("<p style='font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.08em; color: #9ca3af !important; font-weight: 700; margin: 10px 0 4px 0;'>System Telemetry</p>", unsafe_allow_html=True)
    
    st.markdown(f"""
    <div style="font-size: 0.8rem; color: #4b5563; line-height: 1.8;">
        <div>Database: <span style="font-weight: 600; color: #111827;">SQLite</span></div>
        <div>Total Leads: <span style="font-weight: 600; color: #111827;">{len(leads_df)}</span></div>
        <div>Incidents: <span style="font-weight: 600; color: #111827;">{len(errors_df)}</span></div>
        <div>Status: <span style="color: #16a34a; font-weight: 600;">● Active</span></div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<div style='margin-top: 18px;'></div>", unsafe_allow_html=True)
    if st.button("Refresh Sample Data"):
        seed_sample_leads_if_empty()
        st.success("Data reloaded.")
        st.rerun()


# -----------------------------------------------------------------------------
# Top Universal Search Bar & Header
# -----------------------------------------------------------------------------
st.markdown("""
<div class="top-header-bar">
    <div class="search-pill-container">
        <span style="color: #9ca3af; margin-right: 8px; font-size: 13px;">🔍</span>
        <input type="text" placeholder="Search for a lead, company, service, or team task..." disabled>
    </div>
    <div style="display: flex; align-items: center; gap: 8px;">
        <span style="color: #4b5563; font-size: 0.82rem; font-weight: 500;">Admin</span>
        <div class="user-avatar-badge">MS</div>
    </div>
</div>
""", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# TAB 1: DASHBOARD OVERVIEW (Clean White Layout matching screenshot)
# -----------------------------------------------------------------------------
if "Dashboard" in navigation or "Overview" in navigation:
    st.markdown("<h1 style='font-size: 1.65rem; font-weight: 700; color: #111827; margin: 0 0 16px 0;'>Dashboard</h1>", unsafe_allow_html=True)

    if leads_df.empty:
        st.info("No lead records available. Ingest leads via the Simulator or click 'Refresh Sample Data'.")
    else:
        total_leads = len(leads_df)
        hot_leads = len(leads_df[leads_df["classification"].str.lower() == "hot"])
        warm_leads = len(leads_df[leads_df["classification"].str.lower() == "warm"])
        cold_leads = len(leads_df[leads_df["classification"].str.lower() == "cold"])
        avg_score = leads_df["score"].mean() if total_leads > 0 else 0

        # ---------------------------------------------------------------------
        # To-Do Action Cards (Matching Screenshot)
        # ---------------------------------------------------------------------
        st.markdown("<div style='font-size: 0.9rem; font-weight: 700; color: #111827; margin-bottom: 8px;'>To do (2)</div>", unsafe_allow_html=True)

        col_t1, col_t2 = st.columns(2)
        with col_t1:
            st.markdown(f"""
            <div class="todo-banner">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <div class="todo-icon-amber">!</div>
                    <div class="todo-content">
                        <div class="todo-title">Hot Leads Need Immediate Review ({hot_leads})</div>
                        <div class="todo-subtitle">High priority inbound inquiries waiting for callback.</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        with col_t2:
            st.markdown(f"""
            <div class="todo-banner">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <div class="todo-icon-blue">✓</div>
                    <div class="todo-content">
                        <div class="todo-title">Review Discovery Portfolio <span class="badge-recommended">Recommended</span></div>
                        <div class="todo-subtitle">{warm_leads} Warm leads ready for standard 24-hr follow-up.</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<div style='margin-top: 12px;'></div>", unsafe_allow_html=True)

        # ---------------------------------------------------------------------
        # Top 2 Summary Cards (Licenses & Storage style)
        # ---------------------------------------------------------------------
        card1, card2 = st.columns(2)

        with card1:
            st.markdown("""
            <div class="white-card">
                <div class="card-title">Qualification Rate</div>
                <div style="display: flex; align-items: center; justify-content: space-between; margin-top: 12px; gap: 14px; flex-wrap: wrap;">
                    <div style="width: 76px; height: 76px; border-radius: 50%; border: 6px solid #dc2626; display: flex; align-items: center; justify-content: center; font-size: 1.15rem; font-weight: 700; color: #111827; flex-shrink: 0;">
                        100%
                    </div>
                    <div style="flex: 1 1 160px;">
                        <div style="font-size: 0.9rem; font-weight: 600; color: #111827;">All Inbound Leads Qualified</div>
                        <div style="font-size: 0.78rem; color: #6b7280; margin-top: 2px;">Dual AI and rule engine active</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        with card2:
            st.markdown(f"""
            <div class="white-card">
                <div class="card-title">Average Lead Score</div>
                <div style="display: flex; align-items: center; justify-content: space-between; margin-top: 12px; gap: 14px; flex-wrap: wrap;">
                    <div style="width: 76px; height: 76px; border-radius: 50%; border: 6px solid #2563eb; display: flex; align-items: center; justify-content: center; font-size: 1.15rem; font-weight: 700; color: #111827; flex-shrink: 0;">
                        {avg_score:.0f}
                    </div>
                    <div style="flex: 1 1 160px;">
                        <div style="font-size: 0.9rem; font-weight: 600; color: #111827;">{avg_score:.1f} / 100 Index</div>
                        <div style="font-size: 0.78rem; color: #6b7280; margin-top: 2px;">{total_leads} Total records stored in database</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # ---------------------------------------------------------------------
        # Storage Details / Lead Breakdown Card (Screenshot style)
        # ---------------------------------------------------------------------
        st.markdown("<div style='font-size: 0.95rem; font-weight: 700; color: #111827; margin: 14px 0 8px 0;'>Lead Breakdown Details</div>", unsafe_allow_html=True)

        st.markdown("<div class='white-card'>", unsafe_allow_html=True)
        b_col1, b_col2 = st.columns([1, 1.2])

        class_counts = leads_df["classification"].str.capitalize().value_counts().reset_index()
        class_counts.columns = ["Classification", "Count"]
        color_map = {"Hot": "#f59e0b", "Warm": "#c084fc", "Cold": "#60a5fa"}

        with b_col1:
            fig_donut = px.pie(
                class_counts,
                names="Classification",
                values="Count",
                color="Classification",
                color_discrete_map=color_map,
                hole=0.62
            )
            fig_donut.update_traces(textposition='none', hoverinfo='label+percent+value')
            fig_donut.update_layout(
                annotations=[dict(text=f"<b>{total_leads}</b><br><span style='font-size:11px; color:#6b7280;'>Total Leads</span>", x=0.5, y=0.5, font_size=18, showarrow=False)],
                margin=dict(t=8, b=8, l=8, r=8),
                height=260,
                showlegend=False,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig_donut, use_container_width=True)

        with b_col2:
            st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
            for _, row in class_counts.iterrows():
                cat = row["Classification"]
                count = row["Count"]
                pct = (count / total_leads * 100) if total_leads else 0
                bar_color = color_map.get(cat, "#3b82f6")
                
                st.markdown(f"""
                <div style="display: flex; align-items: center; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #f3f4f6;">
                    <div style="display: flex; align-items: center;">
                        <div style="width: 4px; height: 24px; background-color: {bar_color}; border-radius: 2px; margin-right: 12px;"></div>
                        <div>
                            <div style="font-size: 0.88rem; font-weight: 600; color: #111827;">{cat} Leads</div>
                            <div style="font-size: 0.75rem; color: #6b7280;">{pct:.1f}% of inbound pipeline</div>
                        </div>
                    </div>
                    <div style="font-size: 0.9rem; font-weight: 700; color: #111827;">{count} leads</div>
                </div>
                """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        # ---------------------------------------------------------------------
        # Bottom History Row (Lavender Area Chart & Service Bar Chart)
        # ---------------------------------------------------------------------
        hist_col1, hist_col2 = st.columns(2)

        with hist_col1:
            st.markdown("""
            <div class="white-card">
                <div class="card-title">Usage & Score Trend</div>
                <div class="card-subtitle">Lead qualification score over time</div>
            """, unsafe_allow_html=True)
            
            timeline_df = leads_df.copy()
            fig_area = px.area(
                timeline_df,
                x="created_at",
                y="score",
                color_discrete_sequence=["#d8b4fe"]
            )
            fig_area.update_layout(
                margin=dict(t=6, b=6, l=6, r=6),
                height=210,
                xaxis_title="",
                yaxis_title="Score",
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig_area, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with hist_col2:
            st.markdown("""
            <div class="white-card">
                <div class="card-title">Demand by Service</div>
                <div class="card-subtitle">Inbound service distribution</div>
            """, unsafe_allow_html=True)
            
            service_counts = leads_df["requested_service"].value_counts().reset_index()
            service_counts.columns = ["Service", "Count"]
            
            fig_hbar = px.bar(
                service_counts,
                x="Count",
                y="Service",
                orientation="h",
                color_discrete_sequence=["#c084fc"]
            )
            fig_hbar.update_layout(
                yaxis={'categoryorder':'total ascending'},
                margin=dict(t=6, b=6, l=6, r=6),
                height=210,
                xaxis_title="Count",
                yaxis_title="",
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig_hbar, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# TAB 2: LEAD PIPELINE TABLE (Responsive Clean White Table)
# -----------------------------------------------------------------------------
elif "Table" in navigation or "Pipeline" in navigation:
    st.markdown("<h1 style='font-size: 1.65rem; font-weight: 700; color: #111827; margin: 0 0 16px 0;'>Lead Pipeline Management</h1>", unsafe_allow_html=True)

    if leads_df.empty:
        st.info("No leads available.")
    else:
        st.markdown("<div class='white-card'>", unsafe_allow_html=True)
        
        f1, f2, f3, f4 = st.columns(4)
        with f1:
            class_filter = st.selectbox("Classification", ["All", "Hot", "Warm", "Cold"])
        with f2:
            status_filter = st.selectbox("Status", ["All"] + sorted(leads_df["status"].unique().tolist()))
        with f3:
            priority_filter = st.selectbox("Priority", ["All", "High", "Medium", "Low"])
        with f4:
            search_query = st.text_input("Filter", placeholder="Search name, company, email...")

        filtered_df = leads_df.copy()

        if class_filter != "All":
            filtered_df = filtered_df[filtered_df["classification"].str.lower() == class_filter.lower()]
        if status_filter != "All":
            filtered_df = filtered_df[filtered_df["status"] == status_filter]
        if priority_filter != "All":
            filtered_df = filtered_df[filtered_df["priority"] == priority_filter]
        if search_query:
            q = search_query.lower()
            filtered_df = filtered_df[
                filtered_df["name"].str.lower().str.contains(q) |
                filtered_df["email"].str.lower().str.contains(q) |
                filtered_df["company"].str.lower().str.contains(q) |
                filtered_df["requested_service"].str.lower().str.contains(q)
            ]

        st.caption(f"Showing **{len(filtered_df)}** of **{len(leads_df)}** lead entries.")

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

        csv = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Export Filtered Leads (CSV)",
            data=csv,
            file_name=f"leads_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
        st.markdown("</div>", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# TAB 3: LEAD DETAIL PROFILE
# -----------------------------------------------------------------------------
elif "Detail" in navigation or "Profile" in navigation:
    st.markdown("<h1 style='font-size: 1.65rem; font-weight: 700; color: #111827; margin: 0 0 16px 0;'>Lead Detail Profile</h1>", unsafe_allow_html=True)

    if leads_df.empty:
        st.info("No leads available.")
    else:
        st.markdown("<div class='white-card'>", unsafe_allow_html=True)
        lead_options = [f"{row['lead_id']} - {row['name']} ({row['company'] or 'Independent'})" for _, row in leads_df.iterrows()]
        selected_option = st.selectbox("Select Lead Record:", lead_options)
        selected_lead_id = selected_option.split(" - ")[0]

        lead = get_lead_by_id(selected_lead_id)

        if lead:
            col_l, col_r = st.columns([1.2, 1])

            with col_l:
                st.markdown(f"### {lead['name']}")
                st.markdown(f"**Email:** [{lead['email']}](mailto:{lead['email']})")
                st.markdown(f"**Company:** {lead['company'] or 'Independent'}")
                st.markdown(f"**Requested Service:** `{lead['requested_service']}`")
                st.markdown(f"**Ingestion Date:** `{lead['created_at']}`")
                st.markdown(f"**Engine Mode:** `{lead['analysis_mode']}` ({lead['provider']})")
                
                st.markdown("#### Inquiry Message:")
                st.info(f"\"{lead['message']}\"")

            with col_r:
                score = lead["score"]
                classification = lead["classification"].upper()
                badge_class = "badge-hot" if score >= 70 else ("badge-warm" if score >= 40 else "badge-cold")

                st.markdown(f"""
                <div style="background-color: #f9fafb; border: 1px solid #e5e7eb; padding: 16px; border-radius: 8px; margin-bottom: 14px;">
                    <div style="font-size: 1.8rem; font-weight: 700; color: #111827;">{score} <span style="font-size: 0.95rem; color: #6b7280;">/ 100 PTS</span></div>
                    <div style="margin-top: 4px;"><span class="status-badge {badge_class}">{classification} LEAD</span> • Priority: <b>{lead['priority']}</b></div>
                </div>
                """, unsafe_allow_html=True)

                st.markdown("**Recommended Next Action:**")
                st.success(f"{lead['next_action']}")

                st.markdown("#### Update Follow-Up Status:")
                new_status = st.selectbox(
                    "Status:",
                    ["PENDING_APPROVAL", "OPEN", "CONTACTED", "CLOSED"],
                    index=["PENDING_APPROVAL", "OPEN", "CONTACTED", "CLOSED"].index(lead["status"]) if lead["status"] in ["PENDING_APPROVAL", "OPEN", "CONTACTED", "CLOSED"] else 0
                )
                if st.button("Save Status Update"):
                    update_lead_status(lead["lead_id"], new_status)
                    st.success(f"Status updated to '{new_status}'.")
                    st.rerun()

            st.markdown("---")
            st.markdown("#### Pre-Drafted Email Response:")
            st.text_area("Response Draft", value=lead["suggested_reply"], height=100)
            
            if st.button("Approve & Mark Sent"):
                update_lead_status(lead["lead_id"], "CONTACTED")
                st.success("Lead marked as Contacted.")
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# TAB 4: INCIDENT & AUDIT LOGS
# -----------------------------------------------------------------------------
elif "Audit" in navigation or "Error" in navigation or "Logs" in navigation:
    st.markdown("<h1 style='font-size: 1.65rem; font-weight: 700; color: #111827; margin: 0 0 16px 0;'>Security & Incident Audit Logs</h1>", unsafe_allow_html=True)

    if errors_df.empty:
        st.success("No workflow incidents recorded. System is fully operational.")
    else:
        st.markdown("<div class='white-card'>", unsafe_allow_html=True)
        st.dataframe(
            errors_df[["id", "lead_id", "error_type", "error_message", "created_at"]],
            use_container_width=True,
            hide_index=True
        )

        st.markdown("---")
        st.markdown("#### Inspect Malformed Payload")
        error_options = [f"Event #{row['id']} - {row['error_type']} ({row['lead_id']})" for _, row in errors_df.iterrows()]
        selected_err_str = st.selectbox("Select Incident Event:", error_options)
        selected_err_id = int(selected_err_str.split(" - ")[0].replace("Event #", ""))

        selected_row = errors_df[errors_df["id"] == selected_err_id].iloc[0]
        st.write(f"**Error Description:** `{selected_row['error_message']}`")
        st.code(selected_row["payload"], language="json")
        st.markdown("</div>", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# TAB 5: LEAD INTAKE SIMULATOR
# -----------------------------------------------------------------------------
elif "Simulator" in navigation:
    st.markdown("<h1 style='font-size: 1.65rem; font-weight: 700; color: #111827; margin: 0 0 16px 0;'>Live Lead Intake Simulator</h1>", unsafe_allow_html=True)

    st.markdown("<div class='white-card'>", unsafe_allow_html=True)
    st.markdown("Select a preset profile or enter custom submission data to test real-time qualification scoring and database storage.")

    p1, p2, p3 = st.columns(3)
    preset_name = ""
    preset_email = ""
    preset_company = ""
    preset_service = ""
    preset_message = ""

    if p1.button("Load Hot Lead (Rahul Das)"):
        preset_name = "Rahul Das"
        preset_email = "rahul@example.com"
        preset_company = "North East Digital Agency"
        preset_service = "CRM and AI automation"
        preset_message = "We urgently need help automating our customer support and lead follow-up process."

    if p2.button("Load Warm Lead (Priya Sharma)"):
        preset_name = "Priya Sharma"
        preset_email = "priya@example.com"
        preset_company = "Bright SaaS"
        preset_service = "SaaS operations"
        preset_message = "We would like to learn more about improving our onboarding workflow."

    if p3.button("Load Cold Lead (Amit Kumar)"):
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
        
        submitted = st.form_submit_button("Ingest and Qualify Lead")

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
                    
                    res = analyze_lead_rules(lead_input)
                    
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
                    
                    st.success(f"Lead successfully analyzed and persisted. (Lead ID: `{new_id}`)")
                    st.json({
                        "classification": res.classification,
                        "score": res.score,
                        "next_action": res.next_action,
                        "reply": res.reply
                    })
                except Exception as exc:
                    st.error(f"Validation Error: {exc}")
                    log_workflow_error(
                        error_type="SIMULATOR_VALIDATION_ERROR",
                        error_message=str(exc),
                        payload={"name": form_name, "email": form_email}
                    )
    st.markdown("</div>", unsafe_allow_html=True)
