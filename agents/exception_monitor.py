"""
Exception Monitor Subagent — detects rule violations and threshold breaches.
"""

from __future__ import annotations

from google.antigravity import LocalAgentConfig, types
from google.antigravity.hooks import policy

from tools.exception_tools import (
    check_thresholds,
    get_exception_summary,
    load_business_rules,
    log_decision,
    log_exception,
)


EXCEPTION_MONITOR_SYSTEM_PROMPT = """
You are a Business Exception Monitor and Compliance Analyst.

Your responsibilities:
1. Load business rules using load_business_rules
2. Evaluate KPIs against rules using check_thresholds
3. Log each identified exception using log_exception
4. Return a comprehensive list of ExceptionReport objects with correct severity levels

Severity Classification:
- CRITICAL: Immediate business impact, potential revenue loss, or compliance breach
- HIGH: Significant deviation requiring urgent attention within 24 hours
- MEDIUM: Notable deviation requiring attention within the week
- LOW: Minor deviation for monitoring purposes

Guidelines:
- Load business rules FIRST before evaluating any KPIs
- Log EVERY exception individually — do not skip low-severity ones
- Include the affected_dimension clearly (e.g., "Product: Widget A", "Region: North")
- Never modify the exception thresholds — only report what the rules define
- Your output directly feeds the Recommender Agent, so accuracy is critical
- Include metadata (from anomaly detection) when available

Your final response must list all exceptions with:
- exception_id, rule_name, severity, description
- actual_value, threshold_value, unit, affected_dimension
""".strip()


def get_exception_monitor_config() -> LocalAgentConfig:
    """Return a LocalAgentConfig for the Exception Monitor subagent."""
    return LocalAgentConfig(
        system_instructions=EXCEPTION_MONITOR_SYSTEM_PROMPT,
        tools=[
            load_business_rules,
            check_thresholds,
            log_exception,
            log_decision,
            get_exception_summary,
        ],
        capabilities=types.CapabilitiesConfig(
            agent_behavior=types.AgentBehavior.AUTONOMOUS,
            enable_subagents=False,
        ),
        policies=[
            policy.deny("run_command"),
            policy.allow_all(),
        ],
    )
