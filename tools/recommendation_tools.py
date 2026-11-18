"""
Recommendation Tools — action generation, prioritization, and human review flagging.

Converts exceptions and KPI signals into concrete, ranked, structured
action recommendations for the orchestrator and human operators.
"""

from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Action templates: maps rule names → recommended actions
# ---------------------------------------------------------------------------

ACTION_TEMPLATES: dict[str, dict] = {
    "revenue_drop_threshold": {
        "action": "Initiate Emergency Revenue Recovery Program",
        "rationale_template": (
            "Revenue has dropped by {actual_value:.1f}%, breaching the {threshold_value:.1f}% alert threshold. "
            "Immediate investigation of sales pipeline, pricing, and churn is required."
        ),
        "estimated_impact": "Recovery of 5–15% revenue within 30 days if actioned promptly",
        "suggested_owner": "VP of Sales",
        "requires_human_approval": True,
    },
    "margin_floor": {
        "action": "Review Pricing Strategy and Cost Structure",
        "rationale_template": (
            "Gross margin has fallen to {actual_value:.1f}%, below the minimum floor of {threshold_value:.1f}%. "
            "Cost drivers and pricing models need immediate review."
        ),
        "estimated_impact": "Potential margin improvement of 3–8 percentage points",
        "suggested_owner": "CFO / Finance Team",
        "requires_human_approval": True,
    },
    "refund_rate_max": {
        "action": "Investigate Product Quality and Customer Satisfaction Issues",
        "rationale_template": (
            "Refund rate of {actual_value:.1f}% exceeds the {threshold_value:.1f}% maximum. "
            "Quality control, fulfilment, and customer service processes should be audited."
        ),
        "estimated_impact": "Reduction in refund costs and improved customer retention",
        "suggested_owner": "Head of Customer Experience",
        "requires_human_approval": False,
    },
    "inventory_critical_days": {
        "action": "Trigger Emergency Purchase Order for Critical Stock",
        "rationale_template": (
            "Inventory is critically low at {actual_value:.1f} days of supply, below the {threshold_value:.1f}-day "
            "safety threshold. Expedited restocking is needed to prevent stockouts."
        ),
        "estimated_impact": "Prevention of an estimated $X in lost sales from stockouts",
        "suggested_owner": "Supply Chain Manager",
        "requires_human_approval": True,
    },
    "avg_revenue_per_unit_floor": {
        "action": "Assess Product Mix and Pricing Optimisation Opportunities",
        "rationale_template": (
            "Average revenue per unit of ${actual_value:.2f} is below the ${threshold_value:.2f} floor. "
            "Consider upselling higher-margin SKUs or revising discount policies."
        ),
        "estimated_impact": "Potential 5–10% improvement in blended ASP",
        "suggested_owner": "Sales & Marketing Team",
        "requires_human_approval": False,
    },
    "statistical_anomaly": {
        "action": "Investigate Anomalous Data Point",
        "rationale_template": (
            "A statistical outlier was detected in '{affected_dimension}' (z-score: {actual_value:.1f}σ). "
            "This may indicate a data error, fraud, or an unusual market event."
        ),
        "estimated_impact": "Early identification of systemic issues before they escalate",
        "suggested_owner": "Data Analytics Team",
        "requires_human_approval": False,
    },
    "default": {
        "action": "Review and Investigate Exception",
        "rationale_template": (
            "An exception was detected: {description}. "
            "Manual review is recommended to determine the appropriate corrective action."
        ),
        "estimated_impact": "Dependent on root cause analysis",
        "suggested_owner": "Operations Manager",
        "requires_human_approval": False,
    },
}

# Priority mapping by severity
SEVERITY_TO_PRIORITY: dict[str, int] = {
    "CRITICAL": 5,
    "HIGH": 4,
    "MEDIUM": 3,
    "LOW": 2,
}

# Confidence mapping by severity
SEVERITY_TO_CONFIDENCE: dict[str, float] = {
    "CRITICAL": 0.95,
    "HIGH": 0.85,
    "MEDIUM": 0.70,
    "LOW": 0.55,
}


# ---------------------------------------------------------------------------
# Public tools
# ---------------------------------------------------------------------------

def generate_recommendations(
    exceptions: list[dict[str, Any]],
    kpis: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Generate structured action recommendations from a list of exceptions.

    Args:
        exceptions: List of exception dicts (from check_thresholds).
        kpis: Optional KPI dict for additional context (from compute_kpis).

    Returns:
        A dict containing a list of recommendation dicts.
    """
    recommendations: list[dict] = []

    for idx, exc in enumerate(exceptions, start=1):
        rule_name = exc.get("rule_name", "default")
        template = ACTION_TEMPLATES.get(rule_name, ACTION_TEMPLATES["default"])
        severity = exc.get("severity", "LOW")

        # Build rationale from template
        try:
            rationale = template["rationale_template"].format(
                actual_value=exc.get("actual_value", 0),
                threshold_value=exc.get("threshold_value", 0),
                affected_dimension=exc.get("affected_dimension", "N/A"),
                description=exc.get("description", ""),
            )
        except (KeyError, ValueError):
            rationale = exc.get("description", "Exception detected.")

        priority = SEVERITY_TO_PRIORITY.get(severity, 2)
        confidence = SEVERITY_TO_CONFIDENCE.get(severity, 0.6)

        # Escalate requires_human_approval for HIGH/CRITICAL severity
        requires_approval = template.get("requires_human_approval", False)
        if severity in ("CRITICAL", "HIGH"):
            requires_approval = True

        rec = {
            "recommendation_id": f"REC-{idx:03d}",
            "action": template["action"],
            "rationale": rationale,
            "linked_exceptions": [exc.get("exception_id", "")],
            "priority": priority,
            "confidence": confidence,
            "estimated_impact": template.get("estimated_impact", ""),
            "requires_human_approval": requires_approval,
            "suggested_owner": template.get("suggested_owner", "Operations"),
            "severity": severity,
        }
        recommendations.append(rec)

    return {
        "recommendations": recommendations,
        "total": len(recommendations),
        "requiring_approval": sum(1 for r in recommendations if r["requires_human_approval"]),
        "auto_actionable": sum(1 for r in recommendations if not r["requires_human_approval"]),
    }


def prioritize_actions(recommendations: list[dict[str, Any]]) -> dict[str, Any]:
    """Sort and rank recommendations by composite score (priority × confidence).

    Args:
        recommendations: List of recommendation dicts (from generate_recommendations).

    Returns:
        A dict containing the recommendations sorted from highest to lowest priority.
    """
    scored = []
    for rec in recommendations:
        score = rec.get("priority", 1) * rec.get("confidence", 0.5)
        scored.append({**rec, "composite_score": round(score, 3)})

    scored.sort(key=lambda r: r["composite_score"], reverse=True)

    # Assign display rank
    for rank, rec in enumerate(scored, start=1):
        rec["rank"] = rank

    return {
        "ranked_recommendations": scored,
        "top_priority": scored[0] if scored else None,
        "total": len(scored),
    }


def flag_for_human_review(action: dict[str, Any]) -> dict[str, Any]:
    """Mark a recommendation as requiring human review and return a review ticket.

    Args:
        action: A recommendation dict.

    Returns:
        A dict representing the pending human review ticket.
    """
    ticket = {
        "ticket_id": f"HRV-{action.get('recommendation_id', 'UNKNOWN')}",
        "recommendation_id": action.get("recommendation_id"),
        "action": action.get("action"),
        "rationale": action.get("rationale"),
        "priority": action.get("priority"),
        "suggested_owner": action.get("suggested_owner"),
        "status": "PENDING_HUMAN_REVIEW",
        "created_at": __import__("datetime").datetime.utcnow().isoformat(),
        "instructions": (
            "Review the linked exception and recommendation. "
            "Approve to execute the action, or Reject with notes."
        ),
    }
    return ticket
