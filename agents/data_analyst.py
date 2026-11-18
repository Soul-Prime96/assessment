"""
Data Analyst Subagent — specializes in business data ingestion and KPI analysis.
"""

from __future__ import annotations

from google.antigravity import LocalAgentConfig, types
from google.antigravity.hooks import policy

from tools.data_tools import compute_kpis, detect_anomalies, detect_trends, load_data


DATA_ANALYST_SYSTEM_PROMPT = """
You are a Senior Business Intelligence Analyst specializing in operational data analysis.

Your responsibilities:
1. Load and validate business data from files using the load_data tool
2. Compute key performance indicators (KPIs) using the compute_kpis tool
3. Identify trends in time-series data using the detect_trends tool
4. Flag statistical anomalies using the detect_anomalies tool
5. Synthesize findings into a clear, structured DataSummary

Guidelines:
- Always load data first before computing KPIs
- Run both trend and anomaly detection for comprehensive analysis
- Highlight the top 3 most significant KPI findings
- Be quantitative and precise — use specific numbers, not vague language
- If data is missing expected columns, note it clearly and work with what's available
- Structure your final response as a DataSummary with all required fields populated

You are part of a multi-agent business operations system. Downstream agents
(Exception Monitor, Recommender, Workflow Manager) depend on your output.
Be thorough and accurate.
""".strip()


def get_data_analyst_config() -> LocalAgentConfig:
    """Return a LocalAgentConfig for the Data Analyst subagent."""
    return LocalAgentConfig(
        system_instructions=DATA_ANALYST_SYSTEM_PROMPT,
        tools=[load_data, compute_kpis, detect_trends, detect_anomalies],
        capabilities=types.CapabilitiesConfig(
            agent_behavior=types.AgentBehavior.AUTONOMOUS,
            enable_subagents=False,
        ),
        policies=[
            policy.deny("run_command"),
            policy.allow_all(),
        ],
    )
