"""Beam-strip load response: simply supported strip, central transverse point load.

Formulation (simply supported span ``L``, central point load ``P``)::

    M_max   = P L / 4                       at midspan
    V_max   = P / 2                         at the supports
    delta_b = P L^3 / (48 EI)                bending (Euler-Bernoulli) midspan
    delta_s = P L / (4 kappa G_c A_s)        core transverse shear, A_s = b t_c
    delta   = delta_b + delta_s

Stress-reporting convention
---------------------------
``sigma_face,max = M_max (h/2) / I_faces_total``

i.e. the extreme-fibre beam-theory normal stress at the OUTER face surface,
using the faces-only second moment. This is a beam-theory estimate, not a
detailed laminate or local stress.

``tau_core = V_max / (b t_c)`` is an AVERAGE effective core shear stress over the
core depth. It is a first-order screening quantity, not a honeycomb cell-wall
stress.

Shear-correction factor
-----------------------
``kappa`` is exposed explicitly and defaults to ``1.0``, because ``G_c`` is
already an *effective sandwich-core* transverse shear modulus and the shear is
taken as carried uniformly by the core over ``A_s = b t_c``. The factor is never
applied silently.
"""

from __future__ import annotations

from dataclasses import dataclass

from .validation import require_positive_finite

__all__ = ["CentralPointLoadResult", "central_point_load_response", "DEFAULT_KAPPA"]

DEFAULT_KAPPA = 1.0


@dataclass(frozen=True)
class CentralPointLoadResult:
    """Response of a simply supported sandwich strip under a central point load."""

    load: float  # P [N]
    span: float  # L [m]
    shear_correction_factor: float  # kappa [-]
    max_bending_moment: float  # M_max [N m]
    max_shear_force: float  # V_max [N]
    bending_deflection: float  # delta_b [m]
    shear_deflection: float  # delta_s [m]
    total_deflection: float  # delta [m]
    max_face_stress: float  # sigma_face,max [Pa]
    avg_core_shear_stress: float  # tau_core [Pa]

    @property
    def shear_deflection_fraction(self) -> float:
        """``delta_s / delta_total`` in [0, 1].

        A sandwich can be very bending-stiff yet core-shear-dominated; this
        diagnostic makes that visible.
        """
        return self.shear_deflection / self.total_deflection


def central_point_load_response(
    load: float,
    span: float,
    flexural_rigidity: float,
    second_moment_for_stress: float,
    outer_fibre_distance: float,
    core_shear_modulus: float,
    core_shear_area: float,
    shear_correction_factor: float = DEFAULT_KAPPA,
) -> CentralPointLoadResult:
    """Evaluate the central-point-load response of a simply supported strip.

    All arguments are SI and must be strictly positive and finite.
    """
    p = require_positive_finite(load, "load")
    length = require_positive_finite(span, "span")
    ei = require_positive_finite(flexural_rigidity, "flexural_rigidity")
    i_stress = require_positive_finite(second_moment_for_stress, "second_moment_for_stress")
    c = require_positive_finite(outer_fibre_distance, "outer_fibre_distance")
    g_c = require_positive_finite(core_shear_modulus, "core_shear_modulus")
    a_s = require_positive_finite(core_shear_area, "core_shear_area")
    kappa = require_positive_finite(shear_correction_factor, "shear_correction_factor")

    m_max = p * length / 4.0
    v_max = p / 2.0
    delta_b = p * length**3 / (48.0 * ei)
    delta_s = p * length / (4.0 * kappa * g_c * a_s)

    return CentralPointLoadResult(
        load=p,
        span=length,
        shear_correction_factor=kappa,
        max_bending_moment=m_max,
        max_shear_force=v_max,
        bending_deflection=delta_b,
        shear_deflection=delta_s,
        total_deflection=delta_b + delta_s,
        max_face_stress=m_max * c / i_stress,
        avg_core_shear_stress=v_max / a_s,
    )
