"""Console script entry point with production wiring.

This module provides the entry point for console scripts (pip-installed commands).
It wires production services from the composition layer before invoking the CLI.

System Role:
    Sits at package level (outside adapters) to properly wire composition into
    the adapters layer without violating clean architecture layer constraints.
"""

from __future__ import annotations

from .adapters.cli.main import main as cli_main
from .composition import build_production


def main() -> int:
    """Console script entry point with production services wired.

    Returns:
        Exit code from CLI execution.
    """
    return cli_main(services_factory=build_production)


__all__ = ["main"]
