"""Command Line Interface for DynamicMCP."""

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from dynamicmcp.orchestrator.pipeline import DynamicMCPPipeline
from dynamicmcp.models.tool import ToolLifecycleState
from dynamicmcp.config import settings

console = Console()


@click.group()
@click.version_option(version="0.1.0", prog_name="dynamicmcp")
def main():
    """DynamicMCP: Self-assembling Model Context Protocol (MCP) server factory."""
    pass


@main.command()
@click.argument("input_source")
@click.option("--name", "-n", default=None, help="Explicit name for the synthesized tool.")
@click.option("--offline", is_flag=True, default=False, help="Run without calling external LLM APIs.")
def ingest(input_source: str, name: Optional[str], offline: bool):
    """Ingest a curl command, OpenAPI file, or CLI help text and synthesize an MCP tool."""
    # Check if input is a local file or remote URL
    p = Path(input_source)
    if p.exists() and p.is_file():
        content = p.read_text(encoding="utf-8")
        console.print(f"[bold green]Reading input from file:[/bold green] {input_source}")
    elif (input_source.startswith("http://") or input_source.startswith("https://")) and not input_source.strip().startswith("curl"):
        console.print(f"[bold green]Detected remote API spec URL:[/bold green] {input_source}")
        content = input_source
    else:
        content = input_source

    async def _run():
        pipeline = DynamicMCPPipeline(offline_mode=offline or settings.offline_mode)
        with console.status("[bold blue]Executing DynamicMCP pipeline (Ingest -> Synthesize -> Verify -> Sandbox -> Register)...[/bold blue]"):
            result = await pipeline.create_tool_from_spec(content, suggested_name=name)
        return result

    result = asyncio.run(_run())

    if result.success:
        console.print(
            Panel(
                f"[bold green]Tool Assembled Successfully![/bold green]\n\n"
                f"• [bold]Tool ID:[/bold] {result.tool_id}\n"
                f"• [bold]Tool Name:[/bold] {result.tool_name}\n"
                f"• [bold]State:[/bold] [green]{result.state.value}[/green]\n"
                f"• [bold]Registered MCP Tools:[/bold] {', '.join(result.registered_tools)}\n"
                f"• [bold]Code Path:[/bold] {result.code_path}\n"
                f"• [bold]Policy Path:[/bold] {result.policy_path}\n"
                f"• [bold]Pipeline Duration:[/bold] {result.duration_ms}ms",
                title="DynamicMCP Pipeline Success",
                border_style="green",
            )
        )
    else:
        console.print(
            Panel(
                f"[bold red]Tool Assembly Failed[/bold red]\n\n"
                f"• [bold]State:[/bold] [red]{result.state.value}[/red]\n"
                f"• [bold]Error:[/bold] {result.error_message}\n"
                f"• [bold]Duration:[/bold] {result.duration_ms}ms",
                title="DynamicMCP Error",
                border_style="red",
            )
        )
        sys.exit(1)


@main.command(name="list")
@click.option("--state", "-s", default=None, help="Filter tools by lifecycle state.")
def list_tools(state: Optional[str]):
    """List all managed tools and their lifecycle states."""
    pipeline = DynamicMCPPipeline()
    filter_state = ToolLifecycleState(state) if state else None
    tools = pipeline.store.list_tools(state=filter_state)

    if not tools:
        console.print("[yellow]No tools found in the DynamicMCP store.[/yellow]")
        return

    table = Table(title="DynamicMCP Managed Tools", border_style="blue")
    table.add_column("Tool ID", style="cyan")
    table.add_column("Name", style="bold")
    table.add_column("State", style="magenta")
    table.add_column("Domain", style="green")
    table.add_column("Source", style="yellow")
    table.add_column("Updated At", style="dim")

    for t in tools:
        state_color = "green" if t.state == ToolLifecycleState.REGISTERED else "red" if t.state == ToolLifecycleState.QUARANTINED else "yellow"
        table.add_row(
            t.id,
            t.name,
            f"[{state_color}]{t.state.value}[/{state_color}]",
            t.target_domain or "-",
            t.source_type,
            t.updated_at[:19],
        )

    console.print(table)


@main.command()
@click.argument("tool_name")
@click.option("--args", "-a", default="{}", help="JSON string of tool arguments.")
def run(tool_name: str, args: str):
    """Execute a registered dynamic tool directly."""
    try:
        arguments = json.loads(args)
    except Exception as e:
        console.print(f"[bold red]Invalid JSON for --args:[/bold red] {e}")
        sys.exit(1)

    async def _execute():
        pipeline = DynamicMCPPipeline()
        with console.status(f"[bold blue]Executing '{tool_name}'...[/bold blue]"):
            return await pipeline.execute_tool(tool_name, arguments)

    try:
        result = asyncio.run(_execute())
        if hasattr(result, "model_dump"):
            display_val = result.model_dump()
        else:
            display_val = result
        console.print(Panel(json.dumps(display_val, indent=2, default=str), title=f"Result for {tool_name}", border_style="cyan"))
    except Exception as e:
        console.print(f"[bold red]Execution error:[/bold red] {e}")
        sys.exit(1)


@main.command()
@click.option("--host", default="127.0.0.1", help="Host interface to bind FastMCP.")
@click.option("--port", default=8000, type=int, help="Port to serve FastMCP SSE.")
def serve(host: str, port: int):
    """Start FastMCP server for Hermes Agent connection."""
    pipeline = DynamicMCPPipeline()
    console.print(f"[bold green]Starting FastMCP Dynamic server on {host}:{port}...[/bold green]")
    pipeline.registry.server.run(transport="sse", host=host, port=port)


if __name__ == "__main__":
    main()
