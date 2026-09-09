"""Small shared validation helpers.

All quantities in this package are SI units.
"""

from __future__ import annotations

import math

__all__ = ["require_positive_finite", "require_finite", "require_non_empty_name"]


def require_finite(value: float, name: str) -> float:
    """Return ``value`` as a float, rejecting NaN/inf and non-numeric input."""
    try:
        v = float(value)
    except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
        raise TypeError(f"{name} must be a real number, got {value!r}") from exc
    if not math.isfinite(v):
        raise ValueError(f"{name} must be finite, got {v!r}")
    return v


def require_positive_finite(value: float, name: str) -> float:
    """Return ``value`` as a strictly positive, finite float."""
    v = require_finite(value, name)
    if v <= 0.0:
        raise ValueError(f"{name} must be > 0, got {v!r}")
    return v


def require_non_empty_name(value: str, name: str = "name") -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string, got {value!r}")
    return value
