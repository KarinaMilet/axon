from __future__ import annotations

import logging
import tomllib
from pathlib import Path

import typer

app = typer.Typer(
    name="axon",
    help="Axon — your personal research assistant.",
    add_completion=False,
)


def _load_config(config_path: str) -> dict:
    path = Path(config_path)
    if not path.exists():
        typer.echo(f"Error: config file not found: {path}", err=True)
        raise typer.Exit(1)
    with open(path, "rb") as f:
        return tomllib.load(f)


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


@app.command()
def fetch(
    config: str = typer.Option("config.toml", "--config", "-c", help="Path to config file"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logging"),
) -> None:
    """Fetch and filter papers only (no LLM calls). Reusable data acquisition step."""
    _setup_logging(verbose)
    from axon.orchestrator import Orchestrator

    orch = Orchestrator(_load_config(config))
    orch.run("fetch")


@app.command()
def daily(
    config: str = typer.Option("config.toml", "--config", "-c", help="Path to config file"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logging"),
) -> None:
    """Run full daily pipeline: fetch -> analyze -> digest -> deliver."""
    _setup_logging(verbose)
    from axon.orchestrator import Orchestrator

    orch = Orchestrator(_load_config(config))
    orch.run("daily")


@app.command()
def crawler(
    config: str = typer.Option("config.toml", "--config", "-c", help="Path to config file"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logging"),
) -> None:
    """Alias for 'daily'. Run full daily pipeline."""
    daily(config=config, verbose=verbose)


@app.command()
def serve(
    config: str = typer.Option("config.toml", "--config", "-c", help="Path to config file"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logging"),
) -> None:
    """Start the scheduler daemon. Runs the daily pipeline on the cron schedule."""
    _setup_logging(verbose)
    from axon.orchestrator import Orchestrator
    from axon.scheduler import start_scheduler

    cfg = _load_config(config)
    orch = Orchestrator(cfg)
    start_scheduler(cfg, lambda: orch.run("daily"))


if __name__ == "__main__":
    app()
