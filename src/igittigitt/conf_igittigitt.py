"""Runtime configuration for the igittigitt gitignore parser."""

from __future__ import annotations

from pydantic import BaseModel


class ConfIgittIgitt(BaseModel):
    """Runtime options for :class:`igittigitt.IgnoreParser`.

    Attributes:
        add_default_patterns: Whether to also load git's default ignore
            patterns from the user home directory (see the README section
            "Default Patterns").

    Example:
        >>> ConfIgittIgitt().add_default_patterns
        True
        >>> ConfIgittIgitt(add_default_patterns=False).add_default_patterns
        False
    """

    add_default_patterns: bool = True


conf_igittigitt = ConfIgittIgitt()
