"""Milestone 3: combined stiffness + strength screening and preliminary load capacity.

This layer sits on top of the Milestone 2 trade (:mod:`sandwich_panel.trade`) and
adds first-order strength screening. It is purely additive: nothing in Milestones
1-2 changes meaning.

Two things are kept deliberately separate:

* the **stiffness** screen, whose margin is a length [m]
* the **strength** screens, whose margins are dimensionless [-]

These are never combined into a single number. Overall feasibility is the logical
AND of the two, and the governing constraint is reported by name.

Load capacities exploit the linearity of the current model: for fixed geometry and
material, face stress, core shear stress and total deflection are all exactly
proportional to the central point load ``P``. Each capacity is therefore an exact
scaling of the reference response, and the core-shear capacity additionally has a
closed form.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from .core_database import CANDIDATE_CORES
from .directions import CoreShearDirection
from .geometry import SandwichGeometry
from .materials import OrthotropicCoreMaterial
from .requirements import DeflectionAssessment, DeflectionRequirement
from .strength import (
    LimitingConstraint,
    OrthotropicCoreStrength,
    StrengthAssessment,
    StrengthBasis,
    core_shear_margin,
    face_stress_margin,
)
from .strength_database import CANDIDATE_CORE_STRENGTHS
from .trade import CoreCandidateResult, StudyBasis, evaluate_candidate

__all__ = [
    "PreliminaryLoadCapacity",
    "CandidateDesignAssessment",
    "LoadSensitivityRow",
    "CoreDepthCapacityRow",
    "assess_strength",
    "preliminary_load_capacity",
    "assess_candidate_design",
    "build_design_table",
    "pareto_front_by_capacity",
    "is_dominated_by_capacity",
    "load_sensitivity_sweep",
    "core_depth_capacity_sweep",
]


def _strength_for(
    name: str, strengths: Sequence[OrthotropicCoreStrength]
) -> OrthotropicCoreStrength:
    for s in strengths:
        if s.name == name:
            return s
    raise KeyError(f"no strength record for candidate core {name!r}")


# -- strength screen -------------------------------------------------------


def assess_strength(
    result: CoreCandidateResult,
    strength_basis: StrengthBasis,
    core_strength: OrthotropicCoreStrength,
    load: float | None = None,
) -> StrengthAssessment:
    """Screen one candidate/direction response against face and core allowables.

    The governing mode is the one with the smaller dimensionless margin. It is
    computed from the margins, never assumed.

    ``load`` is recorded for traceability only; it does not enter the margins,
    which are read off the already-computed demands in ``result``.
    """
    if not isinstance(strength_basis, StrengthBasis):
        raise TypeError("strength_basis must be a StrengthBasis")
    if not isinstance(core_strength, OrthotropicCoreStrength):
        raise TypeError("core_strength must be an OrthotropicCoreStrength")

    face_allowable = strength_basis.face_allowable_stress
    face_ms = face_stress_margin(result.max_face_stress, face_allowable)

    core_allowable = core_strength.shear_strength(result.direction)
    core_ms = core_shear_margin(result.avg_core_shear_stress, core_allowable)

    if face_ms <= core_ms:
        governing_mode = LimitingConstraint.FACE_YIELD
        governing_margin = face_ms
    else:
        governing_mode = LimitingConstraint.CORE_SHEAR
        governing_margin = core_ms

    return StrengthAssessment(
        candidate=result.core_name,
        direction=result.direction,
        load=load,
        face_stress=result.max_face_stress,
        face_allowable=face_allowable,
        face_margin=face_ms,
        face_pass=face_ms >= 0.0,
        core_shear_stress=result.avg_core_shear_stress,
        core_shear_allowable=core_allowable,
        core_shear_margin=core_ms,
        core_shear_pass=core_ms >= 0.0,
        governing_mode=governing_mode,
        governing_margin=governing_margin,
        strength_feasible=(face_ms >= 0.0) and (core_ms >= 0.0),
    )


# -- preliminary load capacity --------------------------------------------


@dataclass(frozen=True)
class PreliminaryLoadCapacity:
    """Preliminary central-point-load limits for one candidate/direction.

    Every value is a **preliminary central-point-load limit** for the current
    simplified beam-strip model. None of them is an ultimate load, a limit load,
    a design load or a certification allowable.
    """

    candidate: str
    direction: CoreShearDirection
    reference_load: float  # P at which the reference response was evaluated [N]
    face_limit: float  # P at which the face yield margin reaches zero [N]
    core_shear_limit: float  # P at which the core shear margin reaches zero [N]
    deflection_limit: float  # P at which the deflection limit is reached [N]
    strength_limit: float  # min(face, core shear) [N] - strength only
    strength_governing_mode: LimitingConstraint
    preliminary_limit: float  # min(face, core shear, deflection) [N]
    governing_constraint: LimitingConstraint
    areal_mass: float  # [kg/m^2]

    @property
    def capacity_to_areal_mass(self) -> float:
        """Preliminary load-capacity-to-areal-mass indicator [N / (kg/m^2)] = [N m^2/kg].

        A coarse screening diagnostic only. It is NOT a universal optimisation
        metric: it folds a stiffness limit and two strength limits into one number
        and ignores every deferred failure mode.
        """
        return self.preliminary_limit / self.areal_mass


def preliminary_load_capacity(
    basis: StudyBasis,
    result: CoreCandidateResult,
    strength_basis: StrengthBasis,
    core_strength: OrthotropicCoreStrength,
    requirement: DeflectionRequirement,
) -> PreliminaryLoadCapacity:
    """Compute the three modelled load limits and the governing one.

    Face limit (linear scaling of the reference response)::

        P_face = P_ref * sigma_allowable / sigma_face(P_ref)

    Core shear limit (exact closed form, since tau = (P/2) / (b t_c))::

        P_core = 2 b t_c tau_allowable

    Deflection limit (linear scaling, since delta is proportional to P)::

        P_deflection = P_ref * delta_allowable / delta_total(P_ref)

    The preliminary limit is the smallest of the three, and the governing
    constraint is reported by name.
    """
    if not isinstance(requirement, DeflectionRequirement):
        raise TypeError("requirement must be a DeflectionRequirement")

    p_ref = basis.load
    face_allowable = strength_basis.face_allowable_stress
    core_allowable = core_strength.shear_strength(result.direction)

    face_limit = p_ref * face_allowable / result.max_face_stress
    core_limit = 2.0 * basis.geometry.width * basis.geometry.core_thickness * core_allowable
    deflection_limit = (
        p_ref * requirement.maximum_total_deflection / result.total_deflection
    )

    if face_limit <= core_limit:
        strength_limit = face_limit
        strength_mode = LimitingConstraint.FACE_YIELD
    else:
        strength_limit = core_limit
        strength_mode = LimitingConstraint.CORE_SHEAR

    if deflection_limit <= strength_limit:
        preliminary = deflection_limit
        governing = LimitingConstraint.DEFLECTION
    else:
        preliminary = strength_limit
        governing = strength_mode

    return PreliminaryLoadCapacity(
        candidate=result.core_name,
        direction=result.direction,
        reference_load=p_ref,
        face_limit=face_limit,
        core_shear_limit=core_limit,
        deflection_limit=deflection_limit,
        strength_limit=strength_limit,
        strength_governing_mode=strength_mode,
        preliminary_limit=preliminary,
        governing_constraint=governing,
        areal_mass=result.areal_mass,
    )


# -- combined assessment ---------------------------------------------------


@dataclass(frozen=True)
class CandidateDesignAssessment:
    """Milestone 2 stiffness screen + Milestone 3 strength screen, kept separate.

    ``deflection`` carries a margin in metres; ``strength`` carries dimensionless
    margins. They are never numerically combined - only ANDed.
    """

    result: CoreCandidateResult
    deflection: DeflectionAssessment
    strength: StrengthAssessment
    capacity: PreliminaryLoadCapacity

    @property
    def deflection_feasible(self) -> bool:
        return self.deflection.feasible

    @property
    def strength_feasible(self) -> bool:
        return self.strength.strength_feasible

    @property
    def overall_feasible(self) -> bool:
        return self.deflection_feasible and self.strength_feasible

    @property
    def label(self) -> str:
        return self.result.label


def assess_candidate_design(
    basis: StudyBasis,
    core: OrthotropicCoreMaterial,
    core_strength: OrthotropicCoreStrength,
    direction: CoreShearDirection | str,
    strength_basis: StrengthBasis,
    requirement: DeflectionRequirement,
) -> CandidateDesignAssessment:
    """Full preliminary design screen of one candidate in one direction."""
    if core_strength.name != core.name:
        raise ValueError(
            f"strength record {core_strength.name!r} does not match core {core.name!r}"
        )
    result = evaluate_candidate(basis, core, direction)
    return CandidateDesignAssessment(
        result=result,
        deflection=requirement.assess(result.total_deflection),
        strength=assess_strength(result, strength_basis, core_strength, load=basis.load),
        capacity=preliminary_load_capacity(
            basis, result, strength_basis, core_strength, requirement
        ),
    )


def build_design_table(
    basis: StudyBasis,
    strength_basis: StrengthBasis,
    requirement: DeflectionRequirement,
    cores: Iterable[OrthotropicCoreMaterial] = CANDIDATE_CORES,
    strengths: Iterable[OrthotropicCoreStrength] = CANDIDATE_CORE_STRENGTHS,
    directions: Iterable[CoreShearDirection | str] = (CoreShearDirection.L, CoreShearDirection.W),
) -> list[CandidateDesignAssessment]:
    """Build the combined mass / deflection / strength / capacity table.

    Rows come back in direction-major, database order. This function ranks
    nothing and selects nothing.
    """
    core_list = list(cores)
    strength_list = list(strengths)
    direction_list = [CoreShearDirection.parse(d) for d in directions]
    if not core_list:
        raise ValueError("cores must not be empty")
    if not direction_list:
        raise ValueError("directions must not be empty")
    return [
        assess_candidate_design(
            basis, core, _strength_for(core.name, strength_list), direction,
            strength_basis, requirement,
        )
        for direction in direction_list
        for core in core_list
    ]


# -- dominance on (mass down, capacity up) --------------------------------


def is_dominated_by_capacity(
    candidate: CandidateDesignAssessment, others: Iterable[CandidateDesignAssessment]
) -> bool:
    """Is ``candidate`` dominated on (lower areal mass, higher preliminary capacity)?

    A screening aid on two axes only. Not optimisation, not a selection: a
    candidate dominated here may still win once crushing, wrinkling, indentation,
    inserts and manufacturing constraints enter.
    """
    for other in others:
        if other is candidate:
            continue
        no_worse = (
            other.result.areal_mass <= candidate.result.areal_mass
            and other.capacity.preliminary_limit >= candidate.capacity.preliminary_limit
        )
        strictly_better = (
            other.result.areal_mass < candidate.result.areal_mass
            or other.capacity.preliminary_limit > candidate.capacity.preliminary_limit
        )
        if no_worse and strictly_better:
            return True
    return False


def pareto_front_by_capacity(
    assessments: Iterable[CandidateDesignAssessment],
) -> list[CandidateDesignAssessment]:
    """Non-dominated on (areal mass down, preliminary capacity up), in input order."""
    items = list(assessments)
    return [a for a in items if not is_dominated_by_capacity(a, items)]


# -- sensitivity sweeps ----------------------------------------------------


def _rebased(basis: StudyBasis, *, load: float | None = None, core_thickness: float | None = None):
    return StudyBasis(
        geometry=SandwichGeometry(
            width=basis.geometry.width,
            face_thickness=basis.geometry.face_thickness,
            core_thickness=(
                basis.geometry.core_thickness if core_thickness is None else core_thickness
            ),
            span=basis.geometry.span,
        ),
        face=basis.face,
        load=basis.load if load is None else load,
        shear_correction_factor=basis.shear_correction_factor,
    )


@dataclass(frozen=True)
class LoadSensitivityRow:
    """One load level, evaluated for one candidate in one direction."""

    load: float  # P [N]
    direction: CoreShearDirection
    total_deflection: float  # [m]
    deflection_feasible: bool
    face_stress: float  # [Pa]
    face_margin: float  # [-]
    core_shear_stress: float  # [Pa]
    core_shear_margin: float  # [-]
    strength_feasible: bool
    overall_feasible: bool
    governing_constraint: LimitingConstraint


def load_sensitivity_sweep(
    basis: StudyBasis,
    core: OrthotropicCoreMaterial,
    core_strength: OrthotropicCoreStrength,
    loads: Iterable[float],
    strength_basis: StrengthBasis,
    requirement: DeflectionRequirement,
    directions: Iterable[CoreShearDirection | str] = (CoreShearDirection.L, CoreShearDirection.W),
) -> list[LoadSensitivityRow]:
    """Evaluate one candidate over a range of central point loads.

    Every demand quantity scales exactly linearly with ``P`` in this model, so the
    sweep shows where each constraint is crossed rather than revealing any new
    physics.
    """
    load_list = list(loads)
    direction_list = [CoreShearDirection.parse(d) for d in directions]
    if not load_list:
        raise ValueError("loads must not be empty")
    if not direction_list:
        raise ValueError("directions must not be empty")

    rows: list[LoadSensitivityRow] = []
    for direction in direction_list:
        for load in load_list:
            a = assess_candidate_design(
                _rebased(basis, load=load), core, core_strength, direction,
                strength_basis, requirement,
            )
            rows.append(
                LoadSensitivityRow(
                    load=load,
                    direction=direction,
                    total_deflection=a.result.total_deflection,
                    deflection_feasible=a.deflection_feasible,
                    face_stress=a.strength.face_stress,
                    face_margin=a.strength.face_margin,
                    core_shear_stress=a.strength.core_shear_stress,
                    core_shear_margin=a.strength.core_shear_margin,
                    strength_feasible=a.strength_feasible,
                    overall_feasible=a.overall_feasible,
                    governing_constraint=a.capacity.governing_constraint,
                )
            )
    return rows


@dataclass(frozen=True)
class CoreDepthCapacityRow:
    """One core-depth point, with capacities in both shear directions."""

    core_thickness: float  # t_c [m]
    areal_mass: float  # [kg/m^2]
    flexural_rigidity: float  # EI [N m^2]
    face_limit: float  # [N], direction-independent
    deflection_limit_L: float  # [N]
    deflection_limit_W: float  # [N]
    core_shear_limit_L: float  # [N]
    core_shear_limit_W: float  # [N]
    preliminary_limit_L: float  # [N]
    preliminary_limit_W: float  # [N]
    governing_constraint_L: LimitingConstraint
    governing_constraint_W: LimitingConstraint


def core_depth_capacity_sweep(
    basis: StudyBasis,
    core: OrthotropicCoreMaterial,
    core_strength: OrthotropicCoreStrength,
    core_thicknesses: Iterable[float],
    strength_basis: StrengthBasis,
    requirement: DeflectionRequirement,
) -> list[CoreDepthCapacityRow]:
    """Vary core depth for one candidate and report capacity in both directions.

    Increasing core depth raises ``EI`` steeply, lowers the face stress for a given
    load, and increases the core shear area - all of which raise capacity - while
    adding core mass linearly. Core depth is NOT optimised here.
    """
    values = list(core_thicknesses)
    if not values:
        raise ValueError("core_thicknesses must not be empty")

    rows: list[CoreDepthCapacityRow] = []
    for t_c in values:
        local = _rebased(basis, core_thickness=t_c)
        a_l = assess_candidate_design(
            local, core, core_strength, CoreShearDirection.L, strength_basis, requirement
        )
        a_w = assess_candidate_design(
            local, core, core_strength, CoreShearDirection.W, strength_basis, requirement
        )
        rows.append(
            CoreDepthCapacityRow(
                core_thickness=t_c,
                areal_mass=a_l.result.areal_mass,
                flexural_rigidity=a_l.result.flexural_rigidity,
                face_limit=a_l.capacity.face_limit,
                deflection_limit_L=a_l.capacity.deflection_limit,
                deflection_limit_W=a_w.capacity.deflection_limit,
                core_shear_limit_L=a_l.capacity.core_shear_limit,
                core_shear_limit_W=a_w.capacity.core_shear_limit,
                preliminary_limit_L=a_l.capacity.preliminary_limit,
                preliminary_limit_W=a_w.capacity.preliminary_limit,
                governing_constraint_L=a_l.capacity.governing_constraint,
                governing_constraint_W=a_w.capacity.governing_constraint,
            )
        )
    return rows
