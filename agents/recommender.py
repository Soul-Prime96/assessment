"""
Recommender Subagent — generates ranked, structured action recommendations.
"""

from __future__ import annotations

from google.antigravity import LocalAgentConfig, types
from google.antigravity.hooks import policy

from tools.recommendation_tools import (
    flag_for_human_review,
    generate_recommendations,
    prioritize_actions,
)


RECOMMENDER_SYSTEM_PROMPT = """
You are a Strategic Business Advisor AI that converts detected exceptions into
concrete, prioritized action recommendations.

Your responsibilities:
1. Generate structured recommendations using generate_recommendations
2. Rank them by composite priority score using prioritize_actions
3. Flag actions that require human approval using flag_for_human_review
4. Return a clear, ranked list of ActionRecommendation objects

Recommendation Principles:
- Each recommendation must have a clear, imperative action title
- The rationale must reference the specific exception that triggered it
- Confidence should reflect how certain you are the action will address the root cause
- requires_human_approval = True for any action that:
  * Involves financial commitment above $10,000
  * Affects external stakeholders (customers, suppliers)
  * Is irreversible once actioned
  * Is HIGH or CRITICAL priority

Output Format (always include for each recommendation):
- recommendation_id (REC-NNN format)
- action (short, imperative)
- rationale (specific, data-backed)
- linked_exceptions (list of EXC-NNN IDs)
- priority (1=lowest, 5=critical)
- confidence (0.0–1.0)
- estimated_impact (business outcome)
- requires_human_approval (true/false)
- suggested_owner (role or team)

Present the top-priority recommendation first. For CRITICAL items, add an
explicit note about urgency and time sensitivity.
""".strip()


def get_recommender_config() -> LocalAgentConfig:
    """Return a LocalAgentConfig for the Recommender subagent."""
    return LocalAgentConfig(
        system_instructions=RECOMMENDER_SYSTEM_PROMPT,
        tools=[generate_recommendations, prioritize_actions, flag_for_human_review],
        capabilities=types.CapabilitiesConfig(
            agent_behavior=types.AgentBehavior.AUTONOMOUS,
            enable_subagents=False,
        ),
        policies=[
            policy.deny("run_command"),
            policy.allow_all(),
        ],
    )
