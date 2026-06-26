"""Module entry point for ``python -m igittigitt``."""

from __future__ import annotations

from .adapters.cli.main import main
from .composition import build_production

if __name__ == "__main__":
    raise SystemExit(main(services_factory=build_production))
