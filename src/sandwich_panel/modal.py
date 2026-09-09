"""Milestone 5: first-order free-vibration screening for the sandwich beam strip.

SCOPE
-----
A uniform, simply supported sandwich beam strip vibrating in ONE transverse
bending plane, carrying only its own distributed mass. Deliberately excluded:
discrete equipment masses, damping, root hinge or bus compliance, torsion, plate
modes, local face/core modes, forced response, and any stress-stiffening. This is
a screening model, not a modal analysis.

BENDING-ONLY REFERENCE (Euler-Bernoulli, simply supported)
-----------------------------------------------------------
::

    k_n   = n pi / L
    omega_n = k_n^2 sqrt(EI / mu)
    f_n     = omega_n / (2 pi)

so for the first mode ``f_1 = (pi / (2 L^2)) sqrt(EI / mu)``.

SHEAR-FLEXIBILITY CORRECTION
----------------------------
The static model already carries bending AND core-shear compliance, so the modal
layer must not pretend the strip is pure Euler-Bernoulli. For a sinusoidal mode
of wavenumber ``k_n`` on a simply supported strip, neglecting rotary inertia::

    omega_n^2 = EI k_n^4 / [ mu (1 + EI k_n^2 / (kappa G_eff A_s)) ]

with ``A_s = b t_c`` and the Milestone 1 convention ``kappa = 1.0``.

**Why this form is the right one, not just a plausible one.** Under a static
sinusoidal load ``q0 sin(k x)`` on the same strip::

    w_bending = q0 / (EI k^4)
    w_shear   = q0 / (kappa G_eff A_s k^2)
    w_shear / w_bending = EI k^2 / (kappa G_eff A_s)

which is *exactly* the correction term. The formula is therefore
``omega^2 = (1 / total compliance) / mu`` - the same bending-plus-shear
compliance the static model already uses, expressed modally. It is consistent
with the Milestone 1 mechanics rather than an unrelated import.

Dimensional audit: ``EI k^4`` is kg/(m s^2), so ``EI k^4 / mu`` is 1/s^2;
``EI k^2`` is N and ``G_eff A_s`` is N, so the correction term is dimensionless.

Limiting behaviour (all verified by test):

* ``G_eff -> infinity``  ->  the Euler-Bernoulli result
* ``G_eff -> 0``         ->  frequency -> 0
* ``EI -> 0``            ->  frequency -> 0
* ``mu`` increasing      ->  frequency decreasing as ``1/sqrt(mu)``
* ``G_eff`` increasing   ->  frequency increasing, monotonically, toward the
  bending-only limit from below

Rotary inertia is neglected, so the shear penalty is a first-order estimate that
degrades at high mode numbers; only the first mode is used as a design screen.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .directions import CoreShearDirection
from .validation import require_positive_finite

__all__ = [
    "DEFAULT_MODAL_KAPPA",
    "distributed_mass",
    "bending_only_frequency",
    "shear_corrected_frequency",
    "modal_frequency",
    "ModalFrequencyResult",
    "FrequencyRequirement",
    "FrequencyAssessment",
]

#: Same convention as the Milestone 1 static shear deflection: G_eff is already
#: an effective sandwich-core shear modulus, so no extra shape factor is applied.
DEFAULT_MODAL_KAPPA = 1.0


def _require_mode_number(value: int, name: str = "mode_number") -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an int, got {value!r}")
    if value < 1:
        raise ValueError(f"{name} must be >= 1, got {value!r}")
    return value


def distributed_mass(areal_mass: float, width: float) -> float:
    """Beam-strip mass per unit length ``mu = m_A * b`` [kg/m].

    Bare faces plus core only, exactly as in the Milestone 1 mass model: no solar
    cells, adhesive, harness, hinges or mechanisms are included.
    """
    m_a = require_positive_finite(areal_mass, "areal_mass")
    b = require_positive_finite(width, "width")
    return m_a * b


def bending_only_frequency(
    flexural_rigidity: float,
    distributed_mass_: float,
    span: float,
    mode_number: int = 1,
) -> float:
    """Euler-Bernoulli simply supported natural frequency ``f_n`` [Hz]."""
    ei = require_positive_finite(flexural_rigidity, "flexural_rigidity")
    mu = require_positive_finite(distributed_mass_, "distributed_mass")
    length = require_positive_finite(span, "span")
    n = _require_mode_number(mode_number)
    k = n * math.pi / length
    return k**2 * math.sqrt(ei / mu) / (2.0 * math.pi)


def shear_corrected_frequency(
    flexural_rigidity: float,
    distributed_mass_: float,
    span: float,
    core_shear_modulus: float,
    core_shear_area: float,
    mode_number: int = 1,
    shear_correction_factor: float = DEFAULT_MODAL_KAPPA,
) -> float:
    """First-order shear-corrected natural frequency ``f_n`` [Hz].

    See the module docstring for the derivation and the limiting cases.
    """
    ei = require_positive_finite(flexural_rigidity, "flexural_rigidity")
    mu = require_positive_finite(distributed_mass_, "distributed_mass")
    length = require_positive_finite(span, "span")
    g = require_positive_finite(core_shear_modulus, "core_shear_modulus")
    a_s = require_positive_finite(core_shear_area, "core_shear_area")
    n = _require_mode_number(mode_number)
    kappa = require_positive_finite(shear_correction_factor, "shear_correction_factor")

    k = n * math.pi / length
    shear_flexibility = ei * k**2 / (kappa * g * a_s)
    omega_squared = ei * k**4 / (mu * (1.0 + shear_flexibility))
    return math.sqrt(omega_squared) / (2.0 * math.pi)


@dataclass(frozen=True)
class ModalFrequencyResult:
    """One mode of the sandwich strip, bending-only and shear-corrected."""

    mode_number: int
    direction: CoreShearDirection | None
    flexural_rigidity: float  # EI [N m^2]
    distributed_mass: float  # mu [kg/m]
    shear_area: float  # A_s = b t_c [m^2]
    core_shear_modulus: float  # G_eff [Pa]
    shear_correction_factor: float  # kappa [-]
    span: float  # L [m]
    bending_only_frequency: float  # [Hz]
    shear_corrected_frequency: float  # [Hz]

    @property
    def shear_frequency_penalty_hz(self) -> float:
        """How much frequency the core shear flexibility costs [Hz], >= 0."""
        return self.bending_only_frequency - self.shear_corrected_frequency

    @property
    def shear_frequency_penalty_fraction(self) -> float:
        """The same penalty as a fraction of the bending-only frequency [-]."""
        return self.shear_frequency_penalty_hz / self.bending_only_frequency

    @property
    def shear_flexibility_ratio(self) -> float:
        """``EI k_n^2 / (kappa G_eff A_s)`` [-] - the dimensionless correction term."""
        k = self.mode_number * math.pi / self.span
        return (
            self.flexural_rigidity
            * k**2
            / (self.shear_correction_factor * self.core_shear_modulus * self.shear_area)
        )

    @property
    def angular_frequency(self) -> float:
        """Shear-corrected ``omega_n`` [rad/s]."""
        return 2.0 * math.pi * self.shear_corrected_frequency


def modal_frequency(
    flexural_rigidity: float,
    distributed_mass_: float,
    span: float,
    core_shear_modulus: float,
    core_shear_area: float,
    mode_number: int = 1,
    shear_correction_factor: float = DEFAULT_MODAL_KAPPA,
    direction: CoreShearDirection | None = None,
) -> ModalFrequencyResult:
    """Evaluate one mode, reporting both the reference and the corrected frequency."""
    return ModalFrequencyResult(
        mode_number=_require_mode_number(mode_number),
        direction=direction,
        flexural_rigidity=require_positive_finite(flexural_rigidity, "flexural_rigidity"),
        distributed_mass=require_positive_finite(distributed_mass_, "distributed_mass"),
        shear_area=require_positive_finite(core_shear_area, "core_shear_area"),
        core_shear_modulus=require_positive_finite(core_shear_modulus, "core_shear_modulus"),
        shear_correction_factor=require_positive_finite(
            shear_correction_factor, "shear_correction_factor"
        ),
        span=require_positive_finite(span, "span"),
        bending_only_frequency=bending_only_frequency(
            flexural_rigidity, distributed_mass_, span, mode_number
        ),
        shear_corrected_frequency=shear_corrected_frequency(
            flexural_rigidity,
            distributed_mass_,
            span,
            core_shear_modulus,
            core_shear_area,
            mode_number,
            shear_correction_factor,
        ),
    )


# -- requirement -----------------------------------------------------------


@dataclass(frozen=True)
class FrequencyAssessment:
    """Outcome of screening one frequency against a minimum-frequency requirement."""

    frequency: float  # [Hz]
    required_frequency: float  # [Hz]
    mode_number: int
    margin_hz: float  # actual - required [Hz]; positive is good
    normalised_margin: float  # actual / required - 1 [-]; positive is good
    feasible: bool  # actual >= required

    def __str__(self) -> str:  # pragma: no cover - presentation only
        return "PASS" if self.feasible else "FAIL"


@dataclass(frozen=True)
class FrequencyRequirement:
    """An ILLUSTRATIVE minimum fundamental-frequency requirement.

    This is a preliminary stiffness screen expressed in the frequency domain. It
    is **not** a launch-provider requirement, not a coupled-loads result, not a
    qualification threshold and not a certification criterion.

    Margin convention, used consistently:

    * ``margin_hz = actual - required`` [Hz], positive means acceptable
    * ``normalised_margin = actual / required - 1`` [-]
    * the check is ``actual >= required``, so exactly meeting it PASSES
    """

    minimum_frequency_hz: float
    mode_number: int = 1
    label: str = "illustrative minimum fundamental-frequency requirement"

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "minimum_frequency_hz",
            require_positive_finite(self.minimum_frequency_hz, "minimum_frequency_hz"),
        )
        object.__setattr__(self, "mode_number", _require_mode_number(self.mode_number))

    def assess(self, frequency: float) -> FrequencyAssessment:
        """Screen a frequency against this requirement."""
        actual = require_positive_finite(frequency, "frequency")
        required = self.minimum_frequency_hz
        return FrequencyAssessment(
            frequency=actual,
            required_frequency=required,
            mode_number=self.mode_number,
            margin_hz=actual - required,
            normalised_margin=actual / required - 1.0,
            feasible=actual >= required,
        )
