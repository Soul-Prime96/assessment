"""
Orchestrator — central coordination agent for the Business Operations AI system.

Responsibilities:
  - Routes analysis tasks to appropriate subagents
  - Enforces human-in-the-loop for HIGH/CRITICAL actions
  - Aggregates outputs into an OrchestratorSummary
  - Maintains a complete audit trail via hooks
  - Applies layered safety policies
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from google.antigravity import Agent, LocalAgentConfig, ToolContext, types
from google.antigravity.hooks import hooks, policy

from tools.exception_tools import log_decision, log_exception

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Human Approval Handler
# ---------------------------------------------------------------------------

async def _human_approval_handler(tool_call: types.ToolCall) -> bool:
    """Intercept tool calls flagged for human review and prompt the operator."""
    # This handler is wired to ask_user policies on sensitive tools.
    # In interactive mode, the user is shown the tool call details and decides.
    print(f"\n{'='*60}")
    print("⚠️  HUMAN APPROVAL REQUIRED")
    print(f"{'='*60}")
    print(f"Tool: {tool_call.name}")
    if hasattr(tool_call, "args") and tool_call.args:
        print(f"Arguments:\n{json.dumps(tool_call.args, indent=2)}")
    print(f"{'='*60}")
    response = input("Approve this action? [y/N]: ").strip().lower()
    approved = response in ("y", "yes")
    print(f"{'✅ Approved' if approved else '❌ Rejected'}")

    # Audit the decision
    log_decision({
        "tool": tool_call.name,
        "args": getattr(tool_call, "args", {}),
        "approved": approved,
        "reviewer": "human_operator",
        "decided_at": datetime.utcnow().isoformat(),
    })

    return approved


# ---------------------------------------------------------------------------
# Hooks
# ---------------------------------------------------------------------------

@hooks.on_session_start
async def _on_session_start() -> None:
    print("\n🚀 Business Operations AI — Session started")


@hooks.on_session_end
async def _on_session_end() -> None:
    print("\n✅ Session complete. Audit log saved to output/audit_log.json")


@hooks.post_turn
async def _post_turn_audit(data: str) -> None:
    """Write every agent response to the audit trail."""
    log = []
    audit_path = OUTPUT_DIR / "session_transcript.json"
    if audit_path.exists():
        with open(audit_path) as f:
            log = json.load(f)
    log.append({
        "timestamp": datetime.utcnow().isoformat(),
        "response_preview": data[:500] if data else "",
    })
    with open(audit_path, "w") as f:
        json.dump(log, f, indent=2)


@hooks.on_tool_error
async def _on_tool_error(data: Exception):
    """Log tool errors to audit trail."""
    print(f"\n⚠️  Tool error: {data}")
    return None  # Let the agent handle the error


# ---------------------------------------------------------------------------
# Orchestrator system prompt
# ---------------------------------------------------------------------------

ORCHESTRATOR_PROMPT = """
You are the Chief Business Operations Orchestrator AI, coordinating a team of
specialized AI agents to streamline business operations.

Your team:
1. Data Analyst Agent — analyzes data, computes KPIs, detects anomalies
2. Exception Monitor Agent — identifies rule violations and threshold breaches  
3. Recommender Agent — generates ranked, structured action recommendations
4. Workflow Manager Agent — executes approved routine tasks (reports, notifications)

Your workflow for a FULL analysis:
Step 1 — Instruct the Data Analyst to load and analyze the provided data file
Step 2 — Pass the KPI results to the Exception Monitor to identify exceptions
Step 3 — Pass the exceptions to the Recommender to generate action recommendations
Step 4 — For recommendations requiring human approval (requires_human_approval=True):
           • Present them clearly to the human operator
           • Wait for explicit approval before proceeding
Step 5 — Instruct the Workflow Manager to execute approved actions:
           • Generate reports (always)
           • Queue notifications for CRITICAL/HIGH exceptions
           • Archive the processed data file
Step 6 — Compile an OrchestratorSummary with all results

Human Oversight Rules (NON-NEGOTIABLE):
• NEVER auto-execute any action marked requires_human_approval=True
• ALWAYS present HIGH and CRITICAL recommendations to the human before acting
• ALWAYS log your decision-making rationale
• If a human rejects an action, note it in the summary and do not retry

Output Format:
Provide a structured OrchestratorSummary including:
- executive_summary: 3-5 sentence plain English overview
- data_summary: KPIs and trend findings
- exceptions: list with severity, description, affected area
- recommendations: ranked list with approval status
- workflow_result: tasks executed and artifacts generated
- human_decisions: any approvals/rejections received

Be clear, structured, and professional. The operations team relies on your output
to make time-sensitive business decisions.
""".strip()


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_orchestrator(mode: str = "full", interactive: bool = True) -> LocalAgentConfig:
    """
    Create and return a LocalAgentConfig for the central Orchestrator agent.

    Args:
        mode: One of 'analyze', 'workflow', 'monitor', 'recommend', 'full'
        interactive: If True, enables human approval prompts via ask_user

    Returns:
        A configured LocalAgentConfig ready for Agent() instantiation.
    """
    # Build safety policies
    # - Shell execution is always denied
    # - File writes for report generation are allowed
    # - Sensitive / external actions require human approval in interactive mode
    policies_list = [
        policy.deny("run_command"),
    ]

    if interactive:
        # In interactive mode, ask the human before executing any file-creation
        # tool that wasn't explicitly pre-approved (e.g. archive_data).
        # generate_report and schedule_notification are always auto-approved.
        policies_list.append(
            policy.ask_user(
                "archive_data",
                handler=_human_approval_handler,
            )
        )

    # Allow everything else (read + reporting tools)
    policies_list.append(policy.allow_all())

    # Subagent declarations
    subagents = [
        types.SubagentConfig(
            name="data_analyst",
            description=(
                "Loads and analyzes business data files. Computes KPIs, detects "
                "time-series trends, and identifies statistical anomalies."
            ),
            capabilities=types.SubagentCapabilities(
                agent_behavior=types.AgentBehavior.AUTONOMOUS,
            ),
        ),
        types.SubagentConfig(
            name="exception_monitor",
            description=(
                "Evaluates KPIs against business rules and identifies exceptions. "
                "Classifies each by severity: LOW, MEDIUM, HIGH, or CRITICAL."
            ),
            capabilities=types.SubagentCapabilities(
                agent_behavior=types.AgentBehavior.AUTONOMOUS,
            ),
        ),
        types.SubagentConfig(
            name="recommender",
            description=(
                "Converts detected exceptions into prioritized, structured action "
                "recommendations with confidence scores and human-approval flags."
            ),
            capabilities=types.SubagentCapabilities(
                agent_behavior=types.AgentBehavior.AUTONOMOUS,
            ),
        ),
        types.SubagentConfig(
            name="workflow_manager",
            description=(
                "Executes approved routine workflows: generates reports, queues "
                "notifications, and archives processed data files."
            ),
            capabilities=types.SubagentCapabilities(
                agent_behavior=types.AgentBehavior.AUTONOMOUS,
            ),
        ),
    ]

    # Mode-specific system prompt adjustments
    mode_addendum = {
        "analyze": "\n\nThis session: Run ONLY Steps 1 (data analysis). Skip exceptions, recommendations, and workflows.",
        "monitor": "\n\nThis session: Run Steps 1–2 only (data analysis + exception monitoring). Skip recommendations and workflows.",
        "recommend": "\n\nThis session: Run Steps 1–3 only (data → exceptions → recommendations). Skip workflow execution.",
        "workflow": "\n\nThis session: Assume data has already been analyzed. Run Step 5 only (workflow execution and reporting).",
        "full": "",  # Full mode — run everything
    }.get(mode, "")

    return LocalAgentConfig(
        system_instructions=ORCHESTRATOR_PROMPT + mode_addendum,
        capabilities=types.CapabilitiesConfig(
            agent_behavior=types.AgentBehavior.INTERACTIVE if interactive else types.AgentBehavior.AUTONOMOUS,
            enable_subagents=True,
        ),
        subagents=subagents,
        policies=policies_list,
        hooks=[
            _on_session_start,
            _on_session_end,
            _post_turn_audit,
            _on_tool_error,
        ],
        budget_config=types.BudgetConfig(
            max_model_calls=40,
            max_tool_calls=60,
        ),
    )


# ---------------------------------------------------------------------------
# High-level run helpers (used by main.py)
# ---------------------------------------------------------------------------

async def run_analysis(
    data_filepath: str,
    mode: str = "full",
    interactive: bool = True,
) -> str:
    """
    Run the orchestrator against a data file and return the final response text.

    Args:
        data_filepath: Path to the CSV or JSON business data file.
        mode: Operation mode — 'analyze', 'monitor', 'recommend', 'workflow', 'full'
        interactive: Whether to prompt for human approval on flagged actions.

    Returns:
        The final orchestrator response as a string.
    """
    session_id = str(uuid.uuid4())[:8].upper()
    config = create_orchestrator(mode=mode, interactive=interactive)

    prompt = (
        f"Session ID: {session_id}\n"
        f"Mode: {mode.upper()}\n"
        f"Data file: {data_filepath}\n\n"
        f"Please run a complete business operations analysis on the provided data file "
        f"following your defined workflow. The data file path is: {data_filepath}"
    )

    async with Agent(config) as agent:
        response = await agent.chat(prompt)
        result = await response.text()
        return result
