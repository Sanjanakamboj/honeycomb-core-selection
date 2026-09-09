"""Honeycomb core shear directions.

Honeycomb is strongly orthotropic in transverse shear. Datasheets quote two
distinct through-thickness shear moduli:

* **L** - the ribbon / longitudinal direction, along which the foil ribbons run
  and are doubled where cells are bonded. This is the STIFFER shear direction.
* **W** - the transverse / expansion direction, across the ribbons. This is the
  SOFTER shear direction, typically roughly one half to one third of ``G_L``.

The beam-strip model needs a single scalar transverse shear modulus, so the
panel's orientation relative to the core ribbon direction must be stated
explicitly. This module makes that choice explicit and validated.

The two directions are never silently averaged: an L/W average has no physical
meaning for a strip loaded in one direction, and hiding it would mask exactly
the sensitivity Milestone 2 exists to expose.
"""

from __future__ import annotations

from enum import Enum

__all__ = ["CoreShearDirection"]


class CoreShearDirection(Enum):
    """Which honeycomb shear direction the beam strip is aligned with."""

    L = "L"  # ribbon / longitudinal direction (stiffer in transverse shear)
    W = "W"  # transverse / expansion direction (softer in transverse shear)

    @classmethod
    def parse(cls, value: "CoreShearDirection | str") -> "CoreShearDirection":
        """Coerce ``value`` to a :class:`CoreShearDirection`.

        Accepts the enum itself or the strings ``"L"``/``"W"`` (case-insensitive,
        surrounding whitespace ignored). Anything else - including ``None``, an
        averaged/combined label such as ``"LW"``, or a numeric value - raises
        ``ValueError`` or ``TypeError`` with a clear message.
        """
        if isinstance(value, cls):
            return value
        if not isinstance(value, str):
            raise TypeError(
                f"core shear direction must be a CoreShearDirection or 'L'/'W', "
                f"got {value!r}"
            )
        key = value.strip().upper()
        if key not in ("L", "W"):
            raise ValueError(
                f"core shear direction must be 'L' (ribbon) or 'W' (transverse), "
                f"got {value!r}; L and W are never averaged"
            )
        return cls(key)

    @property
    def description(self) -> str:
        return {
            CoreShearDirection.L: "ribbon / longitudinal (stiffer)",
            CoreShearDirection.W: "transverse / expansion (softer)",
        }[self]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.value
