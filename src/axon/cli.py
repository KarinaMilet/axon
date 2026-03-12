from __future__ import annotations

import logging
import tomllib
from pathlib import Path

import typer

app = typer.Typer(
    name="axon",
    help="ArXiv AI Agent research digest bot.",
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
def run(
    config: str = typer.Option("config.toml", "--config", "-c", help="Path to config file"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logging"),
) -> None:
    """Run the full pipeline once (fetch → filter → analyze → digest → deliver)."""
    _setup_logging(verbose)
    cfg = _load_config(config)

    from axon.pipeline import run_pipeline

    run_pipeline(cfg)


@app.command()
def serve(
    config: str = typer.Option("config.toml", "--config", "-c", help="Path to config file"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logging"),
) -> None:
    """Start the scheduler daemon. Runs the pipeline on the cron schedule defined in config."""
    _setup_logging(verbose)
    cfg = _load_config(config)

    from axon.pipeline import run_pipeline
    from axon.scheduler import start_scheduler

    start_scheduler(cfg, lambda: run_pipeline(cfg))


@app.command(name="fetch-only")
def fetch_only(
    config: str = typer.Option("config.toml", "--config", "-c", help="Path to config file"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logging"),
) -> None:
    """Fetch and filter papers only (no LLM calls). Useful for debugging."""
    _setup_logging(verbose)
    cfg = _load_config(config)

    from axon.pipeline import fetch_only_pipeline

    fetch_only_pipeline(cfg)


if __name__ == "__main__":
    app()
