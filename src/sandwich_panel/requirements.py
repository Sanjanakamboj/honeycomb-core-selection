"""Preliminary stiffness requirement layer (Milestone 2).

The ONLY feasibility check in Milestone 2 is:

    total panel deflection <= illustrative deflection limit

This is a preliminary stiffness screen. It is deliberately not a qualification
limit, not a verification requirement, and not a certification criterion. No
strength allowable of any kind is evaluated here: face stress and core shear
stress are reported as demand diagnostics only, with nothing to compare them
against until a later milestone introduces allowables.
"""

from __future__ import annotations

from dataclasses import dataclass

from .validation import require_positive_finite

__all__ = ["DeflectionRequirement", "DeflectionAssessment"]


@dataclass(frozen=True)
class DeflectionAssessment:
    """Outcome of screening one total deflection against a deflection limit."""

    total_deflection: float  # [m]
    allowable_deflection: float  # [m]
    margin: float  # allowable - actual [m]; positive is good
    normalised_margin: float  # allowable / actual - 1 [-]; positive is good
    feasible: bool  # actual <= allowable

    def __str__(self) -> str:  # pragma: no cover - presentation only
        return "PASS" if self.feasible else "FAIL"


@dataclass(frozen=True)
class DeflectionRequirement:
    """An illustrative preliminary panel deflection limit.

    Parameters
    ----------
    maximum_total_deflection:
        Allowable total (bending + core shear) deflection [m]. Must be > 0 and
        finite.
    label:
        How the limit was chosen, carried through into reports so the number is
        never presented as if it were derived from a real requirement.

    Margin convention (used consistently everywhere):

    * ``margin = allowable - actual`` [m], positive means acceptable
    * ``normalised_margin = allowable / actual - 1`` [-], positive means acceptable
    * the check is ``actual <= allowable``, so exactly meeting the limit PASSES
    """

    maximum_total_deflection: float
    label: str = "illustrative panel deflection limit"

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "maximum_total_deflection",
            require_positive_finite(self.maximum_total_deflection, "maximum_total_deflection"),
        )

    def assess(self, total_deflection: float) -> DeflectionAssessment:
        """Screen a total deflection against this limit."""
        actual = require_positive_finite(total_deflection, "total_deflection")
        allowable = self.maximum_total_deflection
        return DeflectionAssessment(
            total_deflection=actual,
            allowable_deflection=allowable,
            margin=allowable - actual,
            normalised_margin=allowable / actual - 1.0,
            feasible=actual <= allowable,
        )
