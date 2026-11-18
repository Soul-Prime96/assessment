"""
Smoke test — validates all tool functions without requiring a GEMINI_API_KEY.
Run from project root: python test_tools.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

def test_data_tools():
    from tools.data_tools import load_data, compute_kpis, detect_trends, detect_anomalies

    print("1. load_data...")
    result = load_data("data/sample_sales.csv")
    assert "error" not in result, f"load_data failed: {result.get('error')}"
    assert result["records_count"] == 1800
    print(f"   ✅ Loaded {result['records_count']} records. Date range: {result['date_range']}")

    print("2. compute_kpis...")
    kpis = compute_kpis(result)
    assert "total_revenue" in kpis, f"Missing total_revenue in {kpis.keys()}"
    assert "gross_margin_pct" in kpis
    rev = kpis["total_revenue"]["value"]
    margin = kpis["gross_margin_pct"]["value"]
    print(f"   ✅ Total Revenue: ${rev:,.2f} | Gross Margin: {margin:.1f}%")

    print("3. detect_trends...")
    trends = detect_trends(result)
    assert "trends" in trends
    print(f"   ✅ Trend columns: {list(trends['trends'].keys())}")

    print("4. detect_anomalies...")
    anomalies = detect_anomalies(result)
    n = anomalies["total_found"]
    print(f"   ✅ Found {n} anomaly/anomalies")
    return kpis, anomalies.get("anomalies", [])


def test_exception_tools(kpis, anomalies):
    from tools.exception_tools import load_business_rules, check_thresholds, log_exception, get_exception_summary

    print("5. load_business_rules...")
    rules = load_business_rules()
    assert "revenue_drop_threshold" in rules
    print(f"   ✅ Rules loaded: {list(rules.keys())}")

    print("6. check_thresholds...")
    kpis_with_anomalies = {**kpis, "anomalies": anomalies}
    result = check_thresholds(kpis_with_anomalies, rules)
    n = result["total_found"]
    print(f"   ✅ Exceptions found: {n} | By severity: {result['by_severity']}")
    for exc in result["exceptions"]:
        print(f"      [{exc['severity']:8s}] {exc['rule_name']}: {exc['description'][:60]}...")

    print("7. log_exception...")
    if result["exceptions"]:
        log_result = log_exception(result["exceptions"][0])
        assert log_result.get("status") == "logged"
        print(f"   ✅ Logged: {log_result['log_id']}")

    return result["exceptions"]


def test_recommendation_tools(exceptions):
    from tools.recommendation_tools import generate_recommendations, prioritize_actions, flag_for_human_review

    print("8. generate_recommendations...")
    recs_result = generate_recommendations(exceptions)
    recs = recs_result["recommendations"]
    print(f"   ✅ Recommendations: {recs_result['total']} | Requiring approval: {recs_result['requiring_approval']}")

    print("9. prioritize_actions...")
    ranked = prioritize_actions(recs)
    top = ranked.get("top_priority", {})
    if top:
        print(f"   ✅ Top priority: [{top.get('priority')}/5] {top.get('action')[:55]}...")

    print("10. flag_for_human_review...")
    critical = [r for r in recs if r["requires_human_approval"]]
    if critical:
        ticket = flag_for_human_review(critical[0])
        print(f"    ✅ Ticket: {ticket['ticket_id']} — {ticket['action'][:55]}...")
    return recs


def test_workflow_tools(kpis, exceptions, recs):
    from tools.workflow_tools import generate_report, schedule_notification, get_notification_queue

    print("11. generate_report (markdown)...")
    summary = {"kpis": kpis, "exceptions": exceptions[:2], "recommendations": recs[:2]}
    md_result = generate_report(summary, format="markdown", report_name="smoke_test_report")
    assert md_result["status"] == "COMPLETED"
    print(f"    ✅ Report: {md_result['output_path']}")

    print("12. generate_report (html)...")
    html_result = generate_report(summary, format="html", report_name="smoke_test_report")
    assert html_result["status"] == "COMPLETED"
    print(f"    ✅ Report: {html_result['output_path']}")

    print("13. schedule_notification...")
    notif = schedule_notification("🚨 CRITICAL exception detected!", priority="CRITICAL")
    assert notif["status"] == "QUEUED"
    print(f"    ✅ Notification queued: {notif['notification_id']}")

    print("14. get_notification_queue...")
    q = get_notification_queue()
    print(f"    ✅ Queue depth: {q['total']} total, {q['pending']} pending")


def test_schemas():
    print("15. Pydantic schemas...")
    from models.schemas import (
        DataSummary, ExceptionReport, ActionRecommendation,
        OrchestratorSummary, ExceptionSeverity, ActionPriority
    )
    exc = ExceptionReport(
        exception_id="EXC-001",
        rule_name="margin_floor",
        severity=ExceptionSeverity.HIGH,
        description="Margin below floor",
        affected_dimension="Overall",
        actual_value=18.5,
        threshold_value=25.0,
        unit="%",
    )
    assert exc.severity == ExceptionSeverity.HIGH
    print(f"    ✅ ExceptionReport validated: {exc.exception_id}")

    rec = ActionRecommendation(
        recommendation_id="REC-001",
        action="Fix margin",
        rationale="Margin too low",
        priority=ActionPriority.HIGH,
        confidence=0.9,
        requires_human_approval=True,
    )
    assert rec.requires_human_approval
    print(f"    ✅ ActionRecommendation validated: {rec.recommendation_id}")


if __name__ == "__main__":
    print("=" * 60)
    print("Business Ops AI Agent — Tool Smoke Test")
    print("=" * 60)
    try:
        kpis, anomalies = test_data_tools()
        exceptions = test_exception_tools(kpis, anomalies)
        recs = test_recommendation_tools(exceptions)
        test_workflow_tools(kpis, exceptions, recs)
        test_schemas()
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED — Tools are working correctly!")
        print("   Next step: add your GEMINI_API_KEY to .env and run main.py")
        print("=" * 60)
    except Exception as e:
        import traceback
        print(f"\n❌ TEST FAILED: {e}")
        traceback.print_exc()
        sys.exit(1)
