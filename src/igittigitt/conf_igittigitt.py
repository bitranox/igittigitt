"""Runtime configuration for the igittigitt gitignore parser."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ConfIgittIgitt(BaseModel):
    """Runtime options for :class:`igittigitt.IgnoreParser`.

    Attributes:
        add_default_patterns: Whether ``parse_rule_files`` also loads git's user-level
            ignore file when its caller does not say; read each time it runs, so a change
            here applies to later calls.

    Example:
        >>> ConfIgittIgitt().add_default_patterns
        True
        >>> ConfIgittIgitt(add_default_patterns=False).add_default_patterns
        False
    """

    # Callers change this object at runtime, so each assignment is checked as it is made.
    model_config = ConfigDict(validate_assignment=True, strict=True)

    add_default_patterns: bool = True


conf_igittigitt = ConfIgittIgitt()
