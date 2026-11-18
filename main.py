"""
main.py — CLI entry point for the Business Operations AI Agent System.

Usage:
    python main.py                        # Interactive menu
    python main.py --mode full            # Full analysis on default data
    python main.py --mode analyze --file data/sample_sales.csv
    python main.py --mode monitor --no-interactive  # Autonomous (no prompts)

Modes:
    full       — Complete pipeline: analyze → monitor → recommend → workflow
    analyze    — Data analysis and KPI computation only
    monitor    — Data analysis + exception detection
    recommend  — Data → exceptions → recommendations (no workflow execution)
    workflow   — Execute workflows only (assumes prior analysis)
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Fix Unicode output on Windows (PowerShell defaults to cp1252)
if sys.platform == "win32" and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# Rich console (graceful degradation if not installed)
# ---------------------------------------------------------------------------
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich import print as rprint
    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    Console = None

# ---------------------------------------------------------------------------
# Load .env if present
# ---------------------------------------------------------------------------
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_DATA_FILE = str(Path(__file__).parent / "data" / "sample_sales.csv")
VALID_MODES = ("full", "analyze", "monitor", "recommend", "workflow")

# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def _banner():
    if HAS_RICH:
        console = Console()
        console.print(Panel.fit(
            "[bold cyan]🤖 Business Operations AI Agent[/bold cyan]\n"
            "[dim]Powered by Google Antigravity SDK + Gemini[/dim]",
            border_style="cyan",
        ))
    else:
        print("=" * 60)
        print("   Business Operations AI Agent")
        print("   Powered by Google Antigravity SDK + Gemini")
        print("=" * 60)


def _check_api_key() -> bool:
    key = os.getenv("GEMINI_API_KEY", "")
    if not key or key == "your_api_key_here":
        msg = (
            "\n❌  GEMINI_API_KEY is not set.\n"
            "   1. Get a free key at: https://aistudio.google.com/app/api-keys\n"
            "   2. Copy .env.example to .env and add your key\n"
            "   3. Or set the environment variable: set GEMINI_API_KEY=your_key\n"
        )
        print(msg)
        return False
    return True


def _interactive_menu() -> tuple[str, str]:
    """Show interactive mode + file selection menu. Returns (mode, filepath)."""
    if HAS_RICH:
        console = Console()
        table = Table(title="Available Modes", border_style="blue")
        table.add_column("Mode", style="cyan bold")
        table.add_column("Description")
        table.add_row("1. full",      "Complete pipeline: analyze → monitor → recommend → workflow")
        table.add_row("2. analyze",   "Data analysis and KPI computation only")
        table.add_row("3. monitor",   "Data analysis + exception detection")
        table.add_row("4. recommend", "Analysis + exceptions + recommendations (no workflow)")
        table.add_row("5. workflow",  "Execute reporting workflows only")
        console.print(table)
    else:
        print("\nModes:")
        print("  1. full       — Complete pipeline")
        print("  2. analyze    — Data analysis only")
        print("  3. monitor    — Analysis + exception detection")
        print("  4. recommend  — Analysis + exceptions + recommendations")
        print("  5. workflow   — Workflow execution only")

    mode_map = {"1": "full", "2": "analyze", "3": "monitor", "4": "recommend", "5": "workflow"}
    mode_input = input("\nSelect mode (1-5, or type mode name) [default: full]: ").strip()
    mode = mode_map.get(mode_input, mode_input if mode_input in VALID_MODES else "full")

    file_input = input(f"Data file path [default: {DEFAULT_DATA_FILE}]: ").strip()
    filepath = file_input if file_input else DEFAULT_DATA_FILE

    return mode, filepath


def _display_result(result: str):
    """Pretty-print the final orchestrator response."""
    if HAS_RICH:
        console = Console()
        console.print("\n")
        console.print(Panel(
            result,
            title="[bold green]📋 Operations Report[/bold green]",
            border_style="green",
            expand=False,
        ))
    else:
        print("\n" + "=" * 60)
        print("OPERATIONS REPORT")
        print("=" * 60)
        print(result)
        print("=" * 60)


# ---------------------------------------------------------------------------
# Main async entrypoint
# ---------------------------------------------------------------------------

async def _run(mode: str, filepath: str, interactive: bool) -> None:
    """Import and run the orchestrator (deferred import to avoid import errors
    before the API key is validated)."""
    # Validate file exists
    if not Path(filepath).exists():
        print(f"❌  Data file not found: {filepath}")
        sys.exit(1)

    print(f"\n▶ Starting [{mode.upper()}] analysis on: {filepath}")
    print("  (This may take 30–90 seconds as agents collaborate...)\n")

    from orchestrator import run_analysis  # noqa: PLC0415

    result = await run_analysis(
        data_filepath=filepath,
        mode=mode,
        interactive=interactive,
    )
    _display_result(result)

    # Print artifact locations
    output_dir = Path(__file__).parent / "output"
    artifacts = list(output_dir.glob("**/*"))
    if artifacts:
        print(f"\n📁 Generated artifacts in: {output_dir}")
        for art in sorted(artifacts):
            if art.is_file():
                print(f"   • {art.name}  ({art.stat().st_size:,} bytes)")


# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Business Operations AI Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--mode",
        choices=VALID_MODES,
        help="Operation mode (default: interactive menu)",
    )
    parser.add_argument(
        "--file",
        default=None,
        help=f"Path to data file (default: {DEFAULT_DATA_FILE})",
    )
    parser.add_argument(
        "--no-interactive",
        action="store_true",
        help="Disable human approval prompts (fully autonomous)",
    )
    return parser.parse_args()


def main() -> None:
    _banner()

    if not _check_api_key():
        sys.exit(1)

    args = _parse_args()

    if args.mode:
        # Non-interactive CLI mode
        mode = args.mode
        filepath = args.file or DEFAULT_DATA_FILE
        interactive = not args.no_interactive
    else:
        # Interactive menu
        mode, filepath = _interactive_menu()
        interactive = True

    try:
        asyncio.run(_run(mode=mode, filepath=filepath, interactive=interactive))
    except KeyboardInterrupt:
        print("\n\n🛑 Interrupted by user. Goodbye!")
        sys.exit(0)
    except Exception as exc:
        print(f"\n❌ Fatal error: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
