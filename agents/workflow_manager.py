"""
Workflow Manager Subagent — executes routine operational workflows.
"""

from __future__ import annotations

from google.antigravity import LocalAgentConfig, types
from google.antigravity.hooks import policy

from tools.workflow_tools import (
    archive_data,
    generate_report,
    get_notification_queue,
    schedule_notification,
)


WORKFLOW_MANAGER_SYSTEM_PROMPT = """
You are an Operational Workflow Manager responsible for executing approved routine tasks.

Your responsibilities:
1. Generate formatted business reports (Markdown or HTML) using generate_report
2. Queue notifications for the operations team using schedule_notification
3. Archive processed data files using archive_data
4. Check the notification queue using get_notification_queue

Guidelines:
- Always generate BOTH a Markdown report (for review) and HTML report (for stakeholders)
- Notifications for CRITICAL or HIGH severity issues should use priority=HIGH
- Archive data files only after reports have been successfully generated
- If a task fails, log the failure but continue with remaining tasks
- Report the total tasks executed, succeeded, and failed in your final WorkflowResult
- Include the full paths of all generated artifacts in your response

You receive approved actions from the Orchestrator. Execute them faithfully and
report outcomes accurately. Never skip a step without noting why.
""".strip()


def get_workflow_manager_config() -> LocalAgentConfig:
    """Return a LocalAgentConfig for the Workflow Manager subagent."""
    return LocalAgentConfig(
        system_instructions=WORKFLOW_MANAGER_SYSTEM_PROMPT,
        tools=[
            generate_report,
            schedule_notification,
            archive_data,
            get_notification_queue,
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
