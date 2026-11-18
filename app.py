"""
Business Operations AI Agent — Streamlit Web Dashboard
Streamlines business operations by analyzing data, managing routine workflows,
identifying exceptions, and recommending actions with human oversight.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
import pandas as pd
import streamlit as st

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.data_tools import load_data, compute_kpis, detect_trends, detect_anomalies
from tools.exception_tools import load_business_rules, check_thresholds, log_exception, get_exception_summary
from tools.recommendation_tools import generate_recommendations, prioritize_actions, flag_for_human_review
from tools.workflow_tools import generate_report, schedule_notification, get_notification_queue

# ---------------------------------------------------------------------------
# Page Configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="BizOps AI Agent | Executive Dashboard",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E293B;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #64748B;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 1rem;
        text-align: center;
    }
    .badge-critical {
        background-color: #FEE2E2;
        color: #991B1B;
        padding: 2px 8px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.8rem;
    }
    .badge-high {
        background-color: #FFEDD5;
        color: #9A3412;
        padding: 2px 8px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.8rem;
    }
    .badge-medium {
        background-color: #FEF3C7;
        color: #92400E;
        padding: 2px 8px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.8rem;
    }
    .badge-low {
        background-color: #E0E7FF;
        color: #3730A3;
        padding: 2px 8px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 0.8rem;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Session State Initialization
# ---------------------------------------------------------------------------
if "decisions" not in st.session_state:
    st.session_state.decisions = {}
if "audit_trail" not in st.session_state:
    st.session_state.audit_trail = []

# ---------------------------------------------------------------------------
# Sidebar Controls
# ---------------------------------------------------------------------------
with st.sidebar:
    st.title("🤖 BizOps Controls")
    st.markdown("Automated monitoring & human oversight")
    
    st.markdown("---")
    st.subheader("📁 Data Source")
    uploaded_file = st.file_uploader("Upload Business Data (CSV / JSON)", type=["csv", "json"])
    
    default_data_path = PROJECT_ROOT / "data" / "sample_sales.csv"
    data_source_path = str(default_data_path)
    
    if uploaded_file is not None:
        temp_dir = PROJECT_ROOT / "output" / "uploads"
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_path = temp_dir / uploaded_file.name
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        data_source_path = str(temp_path)
        st.success(f"Loaded: {uploaded_file.name}")
    else:
        st.info("Using demo dataset: `sample_sales.csv` (1,800 records)")

    st.markdown("---")
    st.subheader("⚙️ Business Thresholds")
    rule_rev_drop = st.slider("Max Revenue Drop (%)", min_value=5, max_value=40, value=15, step=1)
    rule_margin_floor = st.slider("Gross Margin Floor (%)", min_value=10, max_value=60, value=25, step=1)
    rule_inventory_days = st.slider("Critical Inventory Alert (Days)", min_value=1, max_value=30, value=7, step=1)
    rule_refund_max = st.slider("Max Refund Rate (%)", min_value=1.0, max_value=15.0, value=5.0, step=0.5)

    custom_rules = {
        "revenue_drop_threshold": rule_rev_drop / 100.0,
        "margin_floor_pct": float(rule_margin_floor),
        "inventory_critical_days": int(rule_inventory_days),
        "refund_rate_max_pct": float(rule_refund_max),
        "avg_revenue_per_unit_floor": 15.0
    }

    st.markdown("---")
    st.caption("Google Antigravity SDK & Gemini powered agent")

# ---------------------------------------------------------------------------
# Core Analysis Pipeline Execution
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def run_pipeline(source_path: str, rules_json: str):
    rules = json.loads(rules_json)
    data_res = load_data(source_path)
    if "error" in data_res:
        return {"error": data_res["error"]}
    
    kpis = compute_kpis(data_res)
    trends = detect_trends(data_res)
    anomalies = detect_anomalies(data_res)
    
    kpis_combined = {**kpis, "anomalies": anomalies.get("anomalies", [])}
    exceptions_res = check_thresholds(kpis_combined, rules)
    exceptions = exceptions_res.get("exceptions", [])
    
    recs_res = generate_recommendations(exceptions)
    recs = recs_res.get("recommendations", [])
    ranked_recs = prioritize_actions(recs)
    
    return {
        "data_info": data_res,
        "kpis": kpis,
        "trends": trends,
        "anomalies": anomalies,
        "exceptions": exceptions,
        "exceptions_summary": exceptions_res.get("by_severity", {}),
        "recommendations": recs,
        "ranked_recommendations": ranked_recs
    }

# Run the cached analysis
with st.spinner("Analyzing operational metrics & evaluating business rules..."):
    results = run_pipeline(data_source_path, json.dumps(custom_rules))

if "error" in results:
    st.error(f"Error loading data: {results['error']}")
    st.stop()

kpis = results["kpis"]
exceptions = results["exceptions"]
exceptions_summary = results["exceptions_summary"]
recs = results["recommendations"]
data_info = results["data_info"]

# ---------------------------------------------------------------------------
# Main Layout & Header
# ---------------------------------------------------------------------------
st.markdown('<div class="main-header">📊 Business Operations AI Agent</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Autonomous data ingestion, anomaly detection, business rules evaluation, and human-in-the-loop oversight.</div>', unsafe_allow_html=True)

# Top KPI Metric Cards
col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric(
        label="Total Revenue",
        value=f"${kpis['total_revenue']['value']:,.2f}" if "total_revenue" in kpis else "$0.00",
        delta=f"{kpis.get('revenue_trend_pct', {}).get('value', 0):+.1f}% vs prior"
    )
with col2:
    st.metric(
        label="Gross Margin",
        value=f"{kpis['gross_margin_pct']['value']:.1f}%" if "gross_margin_pct" in kpis else "0.0%",
        delta=f"Floor: {custom_rules['margin_floor_pct']}%",
        delta_color="normal" if kpis.get("gross_margin_pct", {}).get("value", 0) >= custom_rules['margin_floor_pct'] else "inverse"
    )
with col3:
    st.metric(
        label="Units Sold",
        value=f"{int(kpis['total_units_sold']['value']):,}" if "total_units_sold" in kpis else "0"
    )
with col4:
    st.metric(
        label="Avg Order Value",
        value=f"${kpis['avg_revenue_per_unit']['value']:.2f}" if "avg_revenue_per_unit" in kpis else "$0.00"
    )
with col5:
    exc_count = len(exceptions)
    st.metric(
        label="Exceptions Flagged",
        value=f"{exc_count}",
        delta=f"{exceptions_summary.get('HIGH', 0) + exceptions_summary.get('CRITICAL', 0)} High Priority",
        delta_color="inverse" if exc_count > 0 else "normal"
    )

# ---------------------------------------------------------------------------
# Navigation Tabs
# ---------------------------------------------------------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📈 Analytics & Trends",
    "🚨 Exceptions Monitor",
    "💡 Action Recommendations (Human Oversight)",
    "⚙️ Automated Workflows",
    "📜 Audit Trail"
])

# TAB 1: Analytics & Trends
with tab1:
    st.subheader("Operational Trends & Time Series")
    
    # Load DataFrame for chart
    df = pd.DataFrame(data_info.get("records", []))
    if not df.empty and "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
        daily = df.groupby("date").agg({
            "revenue": "sum",
            "units_sold": "sum",
            "cost": "sum",
            "refunds": "sum"
        }).reset_index()
        
        st.markdown("**Daily Revenue & Cost Over Time**")
        st.line_chart(daily.set_index("date")[["revenue", "cost"]], use_container_width=True)
        
        c_left, c_right = st.columns(2)
        with c_left:
            st.markdown("**Revenue by Region**")
            if "region" in df.columns:
                by_reg = df.groupby("region")["revenue"].sum().reset_index()
                st.bar_chart(by_reg.set_index("region"), use_container_width=True)
        with c_right:
            st.markdown("**Revenue by Product**")
            if "product" in df.columns:
                by_prod = df.groupby("product")["revenue"].sum().reset_index()
                st.bar_chart(by_prod.set_index("product"), use_container_width=True)
    else:
        st.info("No time series data available for charting.")

# TAB 2: Exceptions Monitor
with tab2:
    st.subheader("Detected Exceptions & Rule Violations")
    
    # Severity filters
    col_f1, col_f2 = st.columns([3, 1])
    with col_f1:
        severity_filter = st.multiselect(
            "Filter by Severity",
            options=["CRITICAL", "HIGH", "MEDIUM", "LOW"],
            default=["CRITICAL", "HIGH", "MEDIUM"]
        )
    with col_f2:
        st.markdown(f"**Total Detected:** {len(exceptions)}")
        st.markdown(f"🔴 Critical: `{exceptions_summary.get('CRITICAL', 0)}` | 🟠 High: `{exceptions_summary.get('HIGH', 0)}` | 🟡 Med: `{exceptions_summary.get('MEDIUM', 0)}`")
    
    filtered_exc = [e for e in exceptions if e.get("severity") in severity_filter]
    
    if filtered_exc:
        exc_table = []
        for e in filtered_exc:
            exc_table.append({
                "ID": e.get("exception_id"),
                "Severity": e.get("severity"),
                "Rule": e.get("rule_name"),
                "Affected": e.get("affected_dimension", "Global"),
                "Actual": f"{e.get('actual_value', 0):.2f} {e.get('unit', '')}",
                "Threshold": f"{e.get('threshold_value', 0):.2f} {e.get('unit', '')}",
                "Description": e.get("description")
            })
        st.dataframe(pd.DataFrame(exc_table), use_container_width=True)
    else:
        st.success("No exceptions found matching current filters.")

# TAB 3: Action Recommendations & Human Oversight
with tab3:
    st.subheader("Action Recommendations & Operator Oversight Gate")
    st.markdown("Review and authorize high-impact actions. Critical operations require explicit human sign-off.")
    
    if recs:
        for i, r in enumerate(recs[:10]):  # Show top 10
            rec_id = r.get("recommendation_id", f"REC-{i+1}")
            priority = r.get("priority", 3)
            requires_approval = r.get("requires_human_approval", False)
            current_status = st.session_state.decisions.get(rec_id, "PENDING")
            
            with st.container():
                st.markdown("---")
                rc1, rc2 = st.columns([4, 1.2])
                with rc1:
                    badge_color = "badge-critical" if priority >= 4 else "badge-medium"
                    st.markdown(
                        f"**{r.get('action')}** <span class='{badge_color}'>Priority {priority}/5</span> "
                        f"{'🚨 <b>Approval Required</b>' if requires_approval else '🟢 Auto-executable'}",
                        unsafe_allow_html=True
                    )
                    st.write(f"**Rationale:** {r.get('rationale')}")
                    st.caption(f"Confidence: {int(r.get('confidence', 0.8) * 100)}% | Target Dimension: {r.get('affected_dimension', 'Overall')}")
                
                with rc2:
                    if current_status == "APPROVED":
                        st.success("✅ APPROVED")
                    elif current_status == "REJECTED":
                        st.error("❌ REJECTED")
                    else:
                        st.info("⏳ PENDING REVIEW")
                        b_col1, b_col2 = st.columns(2)
                        with b_col1:
                            if st.button("Approve", key=f"app_{rec_id}"):
                                st.session_state.decisions[rec_id] = "APPROVED"
                                log_entry = {
                                    "timestamp": datetime.now().isoformat(),
                                    "recommendation_id": rec_id,
                                    "action": r.get("action"),
                                    "decision": "APPROVED",
                                    "operator": "Dashboard Operator"
                                }
                                st.session_state.audit_trail.append(log_entry)
                                st.rerun()
                        with b_col2:
                            if st.button("Reject", key=f"rej_{rec_id}"):
                                st.session_state.decisions[rec_id] = "REJECTED"
                                log_entry = {
                                    "timestamp": datetime.now().isoformat(),
                                    "recommendation_id": rec_id,
                                    "action": r.get("action"),
                                    "decision": "REJECTED",
                                    "operator": "Dashboard Operator"
                                }
                                st.session_state.audit_trail.append(log_entry)
                                st.rerun()
    else:
        st.info("No recommendations generated for current data.")

# TAB 4: Automated Workflows
with tab4:
    st.subheader("Routine Workflow Execution")
    
    w_col1, w_col2 = st.columns(2)
    with w_col1:
        st.markdown("### 📄 Generate Stakeholder Report")
        report_format = st.radio("Select Report Format", ["Markdown (.md)", "HTML (.html)"], horizontal=True)
        if st.button("Generate Fresh Report", type="primary"):
            summary_payload = {
                "kpis": kpis,
                "exceptions": exceptions[:10],
                "recommendations": recs[:10]
            }
            fmt = "markdown" if "Markdown" in report_format else "html"
            rep_res = generate_report(summary_payload, format=fmt, report_name="executive_ops_report")
            if rep_res.get("status") == "COMPLETED":
                st.success(f"Generated: `{rep_res.get('output_path')}`")
                
                # Provide download button
                out_path = Path(rep_res.get("output_path"))
                if out_path.exists():
                    with open(out_path, "r", encoding="utf-8") as f:
                        file_content = f.read()
                    mime_type = "text/markdown" if fmt == "markdown" else "text/html"
                    st.download_button(
                        label=f"⬇️ Download {fmt.upper()} Report",
                        data=file_content,
                        file_name=out_path.name,
                        mime=mime_type
                    )
    
    with w_col2:
        st.markdown("### 🔔 Operations Notification Queue")
        new_alert = st.text_input("Send Custom Ops Alert", placeholder="e.g. Price review scheduled for Friday")
        alert_pri = st.selectbox("Alert Priority", ["LOW", "MEDIUM", "HIGH", "CRITICAL"])
        if st.button("Queue Notification"):
            if new_alert:
                n_res = schedule_notification(new_alert, priority=alert_pri)
                st.success(f"Notification {n_res.get('notification_id')} queued successfully!")
            else:
                st.warning("Please type an alert message first.")
        
        q = get_notification_queue()
        st.markdown(f"**Current Pending Notifications:** `{q.get('pending', 0)}`")
        if q.get("notifications"):
            st.json(q.get("notifications")[-3:])

# TAB 5: Audit Trail
with tab5:
    st.subheader("Immutable Audit Trail & Compliance Log")
    st.markdown("Every automated rule check, threshold evaluation, and operator decision is recorded.")
    
    audit_summary = get_exception_summary()
    st.markdown(f"**Persisted Audit Logs on Disk:** `{audit_summary.get('total_logged', 0)}` entries")
    
    if st.session_state.audit_trail:
        st.markdown("#### Live Session Decisions")
        st.dataframe(pd.DataFrame(st.session_state.audit_trail), use_container_width=True)
    
    # Read persisted audit log file if available
    audit_file = PROJECT_ROOT / "output" / "audit_log.json"
    if audit_file.exists():
        with st.expander("View Stored audit_log.json", expanded=False):
            try:
                with open(audit_file, "r", encoding="utf-8") as f:
                    stored_audit = json.load(f)
                st.json(stored_audit)
            except Exception as e:
                st.write(f"Could not read audit log: {e}")
