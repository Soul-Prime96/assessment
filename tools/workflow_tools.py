"""
Workflow Tools — report generation, notifications, archiving.

These tools execute routine operational tasks approved by the orchestrator.
All outputs are written to the output/ directory and logged.
"""

from __future__ import annotations

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

OUTPUT_DIR = Path(__file__).parent.parent / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

NOTIFICATION_QUEUE_FILE = OUTPUT_DIR / "notification_queue.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_queue() -> list[dict]:
    if NOTIFICATION_QUEUE_FILE.exists():
        with open(NOTIFICATION_QUEUE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return []


def _save_queue(queue: list[dict]) -> None:
    with open(NOTIFICATION_QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(queue, f, indent=2)


def _safe_filename(name: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in name)


# ---------------------------------------------------------------------------
# Public tools
# ---------------------------------------------------------------------------

def generate_report(
    summary: dict[str, Any],
    format: str = "markdown",
    report_name: str = "business_report",
) -> dict[str, Any]:
    """Generate a formatted business report from a data/KPI summary dict.

    Args:
        summary: Aggregated data to include in the report (from compute_kpis or OrchestratorSummary).
        format: Output format — 'markdown' or 'html'.
        report_name: Base filename for the report (without extension).

    Returns:
        A dict with status and the path to the generated report file.
    """
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    safe_name = _safe_filename(report_name)
    ext = "md" if format == "markdown" else "html"
    out_path = OUTPUT_DIR / f"{safe_name}_{ts}.{ext}"

    try:
        lines: list[str] = []

        if format == "markdown":
            lines.append(f"# Business Operations Report\n")
            lines.append(f"**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
            lines.append("---\n")

            # KPIs section
            kpis = summary.get("kpis", summary)
            if isinstance(kpis, dict):
                lines.append("## Key Performance Indicators\n")
                lines.append("| Metric | Value | Unit |")
                lines.append("|--------|-------|------|")
                for key, val in kpis.items():
                    if isinstance(val, dict) and "value" in val:
                        unit = val.get("unit", "")
                        lines.append(f"| {key.replace('_', ' ').title()} | {val['value']} | {unit} |")
                lines.append("")

            # Exceptions section
            exceptions = summary.get("exceptions", [])
            if exceptions:
                lines.append("## Active Exceptions\n")
                lines.append("| ID | Rule | Severity | Description |")
                lines.append("|----|------|----------|-------------|")
                for exc in exceptions:
                    lines.append(
                        f"| {exc.get('exception_id', '')} "
                        f"| {exc.get('rule_name', '')} "
                        f"| {exc.get('severity', '')} "
                        f"| {exc.get('description', '')} |"
                    )
                lines.append("")

            # Recommendations section
            recs = summary.get("recommendations", [])
            if recs:
                lines.append("## Action Recommendations\n")
                for rec in recs:
                    approval_flag = " ⚠️ Requires Human Approval" if rec.get("requires_human_approval") else ""
                    lines.append(
                        f"### [{rec.get('priority', '')}] {rec.get('action', '')}{approval_flag}\n"
                        f"- **Rationale:** {rec.get('rationale', '')}\n"
                        f"- **Confidence:** {rec.get('confidence', 0):.0%}\n"
                        f"- **Impact:** {rec.get('estimated_impact', 'N/A')}\n"
                        f"- **Owner:** {rec.get('suggested_owner', 'N/A')}\n"
                    )

        else:  # HTML
            kpis = summary.get("kpis", summary)
            kpi_rows = ""
            if isinstance(kpis, dict):
                for key, val in kpis.items():
                    if isinstance(val, dict) and "value" in val:
                        unit = val.get("unit", "")
                        kpi_rows += (
                            f"<tr><td>{key.replace('_',' ').title()}</td>"
                            f"<td><strong>{val['value']} {unit}</strong></td></tr>"
                        )

            lines.append(f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Business Operations Report</title>
<style>
  body {{ font-family: 'Segoe UI', sans-serif; max-width: 900px; margin: 40px auto; color: #1a1a2e; }}
  h1 {{ color: #16213e; border-bottom: 3px solid #0f3460; padding-bottom: 10px; }}
  h2 {{ color: #0f3460; margin-top: 30px; }}
  table {{ border-collapse: collapse; width: 100%; margin: 16px 0; }}
  th {{ background: #0f3460; color: white; padding: 10px 14px; text-align: left; }}
  td {{ padding: 9px 14px; border-bottom: 1px solid #e0e0e0; }}
  tr:hover {{ background: #f0f4ff; }}
  .badge-critical {{ background:#e53935; color:white; padding:3px 8px; border-radius:4px; }}
  .badge-high {{ background:#fb8c00; color:white; padding:3px 8px; border-radius:4px; }}
  .badge-medium {{ background:#fdd835; color:#333; padding:3px 8px; border-radius:4px; }}
  .badge-low {{ background:#43a047; color:white; padding:3px 8px; border-radius:4px; }}
  .meta {{ color: #888; font-size: 0.9em; margin-bottom: 24px; }}
</style>
</head>
<body>
<h1>📊 Business Operations Report</h1>
<p class="meta">Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
<h2>Key Performance Indicators</h2>
<table>
<tr><th>Metric</th><th>Value</th></tr>
{kpi_rows}
</table>
</body>
</html>""")

        content = "\n".join(lines)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(content)

        return {
            "status": "COMPLETED",
            "output_path": str(out_path),
            "format": format,
            "size_bytes": out_path.stat().st_size,
        }

    except Exception as exc:
        return {"status": "FAILED", "error": str(exc)}


def schedule_notification(
    message: str,
    priority: str = "MEDIUM",
    recipient: str = "operations_team",
    channel: str = "log",
) -> dict[str, Any]:
    """Queue a notification for the operations team.

    In this implementation, notifications are written to a persistent JSON queue file.
    In production, plug in email/Slack/Teams delivery here.

    Args:
        message: Notification body text.
        priority: Urgency level — LOW, MEDIUM, HIGH, or CRITICAL.
        recipient: Target role or team name.
        channel: Delivery channel — 'log' (default), 'email', 'slack'.

    Returns:
        A dict confirming the queued notification with its ID.
    """
    try:
        queue = _load_queue()
        notification_id = f"NOTIF-{len(queue) + 1:04d}"
        entry = {
            "id": notification_id,
            "message": message,
            "priority": priority.upper(),
            "recipient": recipient,
            "channel": channel,
            "queued_at": datetime.utcnow().isoformat(),
            "status": "QUEUED",
        }
        queue.append(entry)
        _save_queue(queue)
        return {
            "status": "QUEUED",
            "notification_id": notification_id,
            "queue_depth": len(queue),
        }
    except Exception as exc:
        return {"status": "FAILED", "error": str(exc)}


def archive_data(filepath: str, archive_label: str = "") -> dict[str, Any]:
    """Archive a processed data file with a timestamp suffix.

    Args:
        filepath: Path to the source data file to archive.
        archive_label: Optional label to append to the archive filename.

    Returns:
        A dict with the destination path of the archived file.
    """
    src = Path(filepath)
    if not src.exists():
        return {"status": "FAILED", "error": f"Source file not found: {filepath}"}

    archive_dir = OUTPUT_DIR / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    label_part = f"_{_safe_filename(archive_label)}" if archive_label else ""
    dest_name = f"{src.stem}{label_part}_{ts}{src.suffix}"
    dest = archive_dir / dest_name

    try:
        shutil.copy2(src, dest)
        return {
            "status": "COMPLETED",
            "source": str(src),
            "destination": str(dest),
            "size_bytes": dest.stat().st_size,
        }
    except Exception as exc:
        return {"status": "FAILED", "error": str(exc)}


def get_notification_queue() -> dict[str, Any]:
    """Return all queued notifications.

    Returns:
        A dict containing the list of pending notifications and queue stats.
    """
    queue = _load_queue()
    pending = [n for n in queue if n.get("status") == "QUEUED"]
    return {
        "total": len(queue),
        "pending": len(pending),
        "notifications": queue,
    }
