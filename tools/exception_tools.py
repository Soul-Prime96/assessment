"""
Exception Tools — business rule engine, threshold checks, audit logging.

Loads configurable rules from data/business_rules.json and evaluates KPIs
against them. All exceptions are logged to output/audit_log.json.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).parent.parent
RULES_FILE = BASE_DIR / "data" / "business_rules.json"
OUTPUT_DIR = BASE_DIR / "output"
AUDIT_LOG_FILE = OUTPUT_DIR / "audit_log.json"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_audit_log() -> list[dict]:
    if AUDIT_LOG_FILE.exists():
        with open(AUDIT_LOG_FILE, encoding="utf-8") as f:
            return json.load(f)
    return []


def _save_audit_log(log: list[dict]) -> None:
    with open(AUDIT_LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2)


def _make_exception_id(index: int) -> str:
    return f"EXC-{index:03d}"


# ---------------------------------------------------------------------------
# Public tools
# ---------------------------------------------------------------------------

def load_business_rules() -> dict[str, Any]:
    """Load the configurable business rules from data/business_rules.json.

    Returns:
        A dict of rule names mapped to their threshold configurations.
    """
    if not RULES_FILE.exists():
        # Return sensible defaults if file is missing
        return {
            "revenue_drop_threshold": 0.15,
            "margin_floor_pct": 20.0,
            "inventory_critical_days": 7,
            "refund_rate_max_pct": 5.0,
            "avg_revenue_per_unit_floor": 10.0,
        }
    with open(RULES_FILE, encoding="utf-8") as f:
        return json.load(f)


def check_thresholds(
    kpis: dict[str, Any],
    rules: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate computed KPIs against business rules and identify exceptions.

    Args:
        kpis: Output dict from compute_kpis().
        rules: Optional rules dict (from load_business_rules()). Loaded automatically if None.

    Returns:
        A dict containing a list of detected exception dicts.
    """
    if rules is None:
        rules = load_business_rules()

    exceptions: list[dict] = []
    exc_index = 1

    # --- Revenue growth ---
    rev_growth = kpis.get("revenue_growth_pct", {})
    if isinstance(rev_growth, dict) and "value" in rev_growth:
        growth = rev_growth["value"]
        threshold = -(rules.get("revenue_drop_threshold", 0.15) * 100)  # convert to %
        if growth < threshold:
            severity = "CRITICAL" if growth < threshold * 2 else "HIGH"
            exceptions.append({
                "exception_id": _make_exception_id(exc_index),
                "rule_name": "revenue_drop_threshold",
                "severity": severity,
                "description": (
                    f"Revenue declined by {abs(growth):.1f}% — exceeds the {abs(threshold):.1f}% drop threshold"
                ),
                "affected_dimension": "Overall Revenue",
                "actual_value": round(growth, 2),
                "threshold_value": round(threshold, 2),
                "unit": "%",
                "detected_at": datetime.utcnow().isoformat(),
            })
            exc_index += 1

    # --- Gross margin ---
    margin = kpis.get("gross_margin_pct", {})
    if isinstance(margin, dict) and "value" in margin:
        margin_val = margin["value"]
        floor = rules.get("margin_floor_pct", 20.0)
        if margin_val < floor:
            severity = "CRITICAL" if margin_val < floor * 0.7 else "HIGH"
            exceptions.append({
                "exception_id": _make_exception_id(exc_index),
                "rule_name": "margin_floor",
                "severity": severity,
                "description": (
                    f"Gross margin {margin_val:.1f}% is below the minimum floor of {floor:.1f}%"
                ),
                "affected_dimension": "Gross Margin",
                "actual_value": round(margin_val, 2),
                "threshold_value": float(floor),
                "unit": "%",
                "detected_at": datetime.utcnow().isoformat(),
            })
            exc_index += 1

    # --- Refund rate ---
    refund = kpis.get("refund_rate_pct", {})
    if isinstance(refund, dict) and "value" in refund:
        refund_val = refund["value"]
        max_refund = rules.get("refund_rate_max_pct", 5.0)
        if refund_val > max_refund:
            severity = "HIGH" if refund_val > max_refund * 1.5 else "MEDIUM"
            exceptions.append({
                "exception_id": _make_exception_id(exc_index),
                "rule_name": "refund_rate_max",
                "severity": severity,
                "description": (
                    f"Refund rate {refund_val:.1f}% exceeds maximum allowed {max_refund:.1f}%"
                ),
                "affected_dimension": "Refund Rate",
                "actual_value": round(refund_val, 2),
                "threshold_value": float(max_refund),
                "unit": "%",
                "detected_at": datetime.utcnow().isoformat(),
            })
            exc_index += 1

    # --- Inventory days ---
    inv = kpis.get("avg_inventory_days", {})
    if isinstance(inv, dict) and "value" in inv:
        inv_val = inv["value"]
        critical_days = rules.get("inventory_critical_days", 7)
        if inv_val < critical_days:
            exceptions.append({
                "exception_id": _make_exception_id(exc_index),
                "rule_name": "inventory_critical_days",
                "severity": "CRITICAL" if inv_val < critical_days * 0.5 else "HIGH",
                "description": (
                    f"Average inventory of {inv_val:.1f} days is below critical threshold of {critical_days} days"
                ),
                "affected_dimension": "Inventory Level",
                "actual_value": round(inv_val, 2),
                "threshold_value": float(critical_days),
                "unit": "days",
                "detected_at": datetime.utcnow().isoformat(),
            })
            exc_index += 1

    # --- Avg revenue per unit ---
    arpu = kpis.get("avg_revenue_per_unit", {})
    if isinstance(arpu, dict) and "value" in arpu:
        arpu_val = arpu["value"]
        floor = rules.get("avg_revenue_per_unit_floor", 10.0)
        if arpu_val < floor:
            exceptions.append({
                "exception_id": _make_exception_id(exc_index),
                "rule_name": "avg_revenue_per_unit_floor",
                "severity": "MEDIUM",
                "description": (
                    f"Avg revenue per unit ${arpu_val:.2f} is below the ${floor:.2f} floor"
                ),
                "affected_dimension": "Pricing / Mix",
                "actual_value": round(arpu_val, 2),
                "threshold_value": float(floor),
                "unit": "$",
                "detected_at": datetime.utcnow().isoformat(),
            })
            exc_index += 1

    # --- Anomaly-based LOW exceptions (passthrough) ---
    anomalies = kpis.get("anomalies", [])
    for anomaly in anomalies:
        exceptions.append({
            "exception_id": _make_exception_id(exc_index),
            "rule_name": "statistical_anomaly",
            "severity": "MEDIUM" if anomaly.get("z_score", 0) < 3.5 else "HIGH",
            "description": anomaly.get("description", "Statistical anomaly detected"),
            "affected_dimension": anomaly.get("metric", "unknown"),
            "actual_value": anomaly.get("value", 0),
            "threshold_value": anomaly.get("z_score", 0),
            "unit": "σ",
            "detected_at": datetime.utcnow().isoformat(),
            "metadata": anomaly,
        })
        exc_index += 1

    return {
        "exceptions": exceptions,
        "total_found": len(exceptions),
        "by_severity": {
            "CRITICAL": sum(1 for e in exceptions if e["severity"] == "CRITICAL"),
            "HIGH": sum(1 for e in exceptions if e["severity"] == "HIGH"),
            "MEDIUM": sum(1 for e in exceptions if e["severity"] == "MEDIUM"),
            "LOW": sum(1 for e in exceptions if e["severity"] == "LOW"),
        },
    }


def log_exception(exception: dict[str, Any]) -> dict[str, Any]:
    """Append an exception record to the persistent audit log.

    Args:
        exception: An exception dict (as returned by check_thresholds).

    Returns:
        A dict confirming the log entry.
    """
    try:
        log = _load_audit_log()
        entry = {
            "log_id": f"LOG-{len(log) + 1:05d}",
            "log_type": "EXCEPTION",
            "logged_at": datetime.utcnow().isoformat(),
            "data": exception,
        }
        log.append(entry)
        _save_audit_log(log)
        return {"status": "logged", "log_id": entry["log_id"]}
    except Exception as exc:
        return {"status": "FAILED", "error": str(exc)}


def log_decision(decision: dict[str, Any]) -> dict[str, Any]:
    """Append a human or automated decision to the audit log.

    Args:
        decision: A dict describing the decision (recommendation_id, approved, reviewer, notes).

    Returns:
        A dict confirming the log entry.
    """
    try:
        log = _load_audit_log()
        entry = {
            "log_id": f"LOG-{len(log) + 1:05d}",
            "log_type": "DECISION",
            "logged_at": datetime.utcnow().isoformat(),
            "data": decision,
        }
        log.append(entry)
        _save_audit_log(log)
        return {"status": "logged", "log_id": entry["log_id"]}
    except Exception as exc:
        return {"status": "FAILED", "error": str(exc)}


def get_exception_summary() -> dict[str, Any]:
    """Return all exceptions logged in the current audit log session.

    Returns:
        A dict with all exception entries and severity counts.
    """
    log = _load_audit_log()
    exceptions = [e["data"] for e in log if e.get("log_type") == "EXCEPTION"]
    return {
        "total_exceptions": len(exceptions),
        "exceptions": exceptions,
        "audit_log_path": str(AUDIT_LOG_FILE),
    }
