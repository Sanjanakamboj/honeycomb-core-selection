"""Milestone 4: combined global + local preliminary sandwich screen.

Additive over Milestone 3: nothing in :mod:`sandwich_panel.design_screen` changes
meaning, and this module composes it rather than replacing it.

THREE MARGIN FAMILIES ARE KEPT APART
------------------------------------
* the **deflection** margin is a LENGTH [m]
* the **global strength** margins (face yield, average core shear) are [-]
* the **local failure** margins (wrinkling, core compression) are [-]

They are combined only by logical AND. No numerical minimum is ever taken across
a dimensional and a dimensionless quantity.

TWO LOAD CASES ARE KEPT APART
-----------------------------
* the **global** central point load ``P``, whose capacity now also accounts for
  face wrinkling;
* the **local** patch force ``F_local`` on a prescribed footprint, whose capacity
  is core crushing.

There is no defined physical relationship between ``P`` and ``F_local`` in this
model, so their capacities are never summed, minimised together, or divided into
one another.

Wrinkling appears in both places on purpose: its *demand* is the global
beam-theory face stress, so its load limit belongs with the global capacity, while
the mode itself is a local face instability, so its *margin* sits with the local
modes.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from enum import Enum

from .core_database import CANDIDATE_CORES
from .design_screen import CandidateDesignAssessment, assess_candidate_design
from .directions import CoreShearDirection
from .geometry import SandwichGeometry
from .local_failure import (
    CoreCompressionProperties,
    LocalFailureAssessment,
    LocalFailureMode,
    LocalPatchLoad,
    SandwichConstraint,
    WrinklingModel,
    core_compression_margin,
    core_crush_force_limit,
    wrinkling_margin,
    wrinkling_screening_stress,
)
from .local_failure_database import CANDIDATE_CORE_COMPRESSION
from .materials import OrthotropicCoreMaterial
from .requirements import DeflectionRequirement
from .strength import OrthotropicCoreStrength, StrengthBasis
from .strength_database import CANDIDATE_CORE_STRENGTHS
from .trade import CoreCandidateResult, StudyBasis

__all__ = [
    "LocalScreenBasis",
    "RetentionStatus",
    "GlobalSandwichCapacity",
    "SandwichDesignAssessment",
    "LocalPatchSweepRow",
    "CoreDepthWrinklingRow",
    "assess_local_failure",
    "global_sandwich_capacity",
    "assess_sandwich_design",
    "build_sandwich_table",
    "local_patch_force_sweep",
    "local_patch_size_sweep",
    "core_depth_wrinkling_sweep",
]


@dataclass(frozen=True)
class LocalScreenBasis:
    """The local-screen inputs applied to a study: wrinkling convention + patch."""

    wrinkling_model: WrinklingModel
    patch_load: LocalPatchLoad

    def __post_init__(self) -> None:
        if not isinstance(self.wrinkling_model, WrinklingModel):
            raise TypeError("wrinkling_model must be a WrinklingModel")
        if not isinstance(self.patch_load, LocalPatchLoad):
            raise TypeError("patch_load must be a LocalPatchLoad")

    def with_patch(self, patch_load: LocalPatchLoad) -> "LocalScreenBasis":
        return LocalScreenBasis(wrinkling_model=self.wrinkling_model, patch_load=patch_load)


class RetentionStatus(str, Enum):
    """Milestone 4 candidate retention outcome. NOT a selection."""

    RETAINED = "retained"
    REJECTED_GLOBAL = "rejected_global"
    REJECTED_LOCAL = "rejected_local"

    def __str__(self) -> str:
        return self.value


# -- local failure screen --------------------------------------------------


def assess_local_failure(
    result: CoreCandidateResult,
    face_modulus: float,
    core_compression: CoreCompressionProperties,
    local_basis: LocalScreenBasis,
) -> LocalFailureAssessment:
    """Screen wrinkling and local core crushing for one candidate/direction.

    The wrinkling demand is the EXISTING global beam-theory face stress; no
    separate face stress field is invented. The core compression demand is the
    uniform patch pressure, which is direction-independent.
    """
    if not isinstance(core_compression, CoreCompressionProperties):
        raise TypeError("core_compression must be a CoreCompressionProperties")
    if not isinstance(local_basis, LocalScreenBasis):
        raise TypeError("local_basis must be a LocalScreenBasis")
    if core_compression.name != result.core_name:
        raise ValueError(
            f"compression record {core_compression.name!r} does not match candidate "
            f"{result.core_name!r}"
        )

    sigma_wr = wrinkling_screening_stress(
        local_basis.wrinkling_model,
        face_modulus,
        core_compression.compression_modulus,
        result.effective_shear_modulus,
    )
    wr_ms = wrinkling_margin(result.max_face_stress, sigma_wr)

    patch = local_basis.patch_load
    pressure = patch.pressure
    cc_allow = core_compression.compression_strength
    cc_ms = core_compression_margin(pressure, cc_allow)

    if wr_ms <= cc_ms:
        governing_mode = LocalFailureMode.WRINKLING
        governing_margin = wr_ms
    else:
        governing_mode = LocalFailureMode.CORE_COMPRESSION
        governing_margin = cc_ms

    return LocalFailureAssessment(
        candidate=result.core_name,
        direction=result.direction,
        face_stress=result.max_face_stress,
        wrinkling_screening_stress=sigma_wr,
        wrinkling_margin=wr_ms,
        wrinkling_pass=wr_ms >= 0.0,
        local_patch_force=patch.force,
        patch_area=patch.patch_area,
        local_core_compression_stress=pressure,
        core_compression_allowable=cc_allow,
        core_compression_margin=cc_ms,
        core_compression_pass=cc_ms >= 0.0,
        core_crush_force_limit=core_crush_force_limit(cc_allow, patch.patch_area),
        governing_local_mode=governing_mode,
        governing_local_margin=governing_margin,
        local_failure_feasible=(wr_ms >= 0.0) and (cc_ms >= 0.0),
    )


# -- global capacity, now including wrinkling ------------------------------


@dataclass(frozen=True)
class GlobalSandwichCapacity:
    """Global central-point-load capacity including face wrinkling.

    Every value is a **preliminary central-point-load limit** for a simplified
    beam-strip model: not an ultimate load, not a limit load, not a design load
    and not a certification allowable.

    The local patch crush capacity is deliberately NOT folded in here - it is a
    different load case.
    """

    candidate: str
    direction: CoreShearDirection
    deflection_limit: float  # [N]
    face_limit: float  # [N]
    core_shear_limit: float  # [N]
    wrinkling_limit: float  # [N]
    sandwich_limit: float  # min of the four [N]
    governing_constraint: SandwichConstraint
    areal_mass: float  # [kg/m^2]

    @property
    def capacity_to_areal_mass(self) -> float:
        """``P_sandwich / m_A`` [N m^2/kg] - a screening diagnostic, not a metric."""
        return self.sandwich_limit / self.areal_mass


def global_sandwich_capacity(
    design: CandidateDesignAssessment,
    local: LocalFailureAssessment,
    reference_load: float,
) -> GlobalSandwichCapacity:
    """Extend the Milestone 3 capacity with the wrinkling load limit.

    ``P_wrinkling = P_ref * sigma_wr,screen / sigma_face(P_ref)``, exact because
    the face stress is linear in the load.
    """
    m3 = design.capacity
    p_wr = reference_load * local.wrinkling_screening_stress / local.face_stress

    limits = {
        SandwichConstraint.DEFLECTION: m3.deflection_limit,
        SandwichConstraint.FACE_YIELD: m3.face_limit,
        SandwichConstraint.CORE_SHEAR: m3.core_shear_limit,
        SandwichConstraint.WRINKLING: p_wr,
    }
    # Deterministic tie-breaking: declaration order of SandwichConstraint.
    governing = min(limits, key=lambda k: (limits[k], list(SandwichConstraint).index(k)))

    return GlobalSandwichCapacity(
        candidate=design.result.core_name,
        direction=design.result.direction,
        deflection_limit=m3.deflection_limit,
        face_limit=m3.face_limit,
        core_shear_limit=m3.core_shear_limit,
        wrinkling_limit=p_wr,
        sandwich_limit=limits[governing],
        governing_constraint=governing,
        areal_mass=m3.areal_mass,
    )


# -- combined assessment ---------------------------------------------------


@dataclass(frozen=True)
class SandwichDesignAssessment:
    """Deflection + global strength + local failure, kept dimensionally separate."""

    design: CandidateDesignAssessment
    local: LocalFailureAssessment
    capacity: GlobalSandwichCapacity

    @property
    def result(self) -> CoreCandidateResult:
        return self.design.result

    @property
    def label(self) -> str:
        return self.design.label

    @property
    def deflection_feasible(self) -> bool:
        return self.design.deflection_feasible

    @property
    def global_strength_feasible(self) -> bool:
        """Milestone 3 face-yield AND average core-shear screens."""
        return self.design.strength_feasible

    @property
    def local_failure_feasible(self) -> bool:
        """Milestone 4 wrinkling AND local core compression screens."""
        return self.local.local_failure_feasible

    @property
    def overall_feasible(self) -> bool:
        return (
            self.deflection_feasible
            and self.global_strength_feasible
            and self.local_failure_feasible
        )

    @property
    def retention(self) -> RetentionStatus:
        """Retained, or rejected by the global or the local screen. NOT a selection."""
        if self.overall_feasible:
            return RetentionStatus.RETAINED
        if not (self.deflection_feasible and self.global_strength_feasible):
            return RetentionStatus.REJECTED_GLOBAL
        return RetentionStatus.REJECTED_LOCAL

    @property
    def retention_reason(self) -> str:
        failures = []
        if not self.deflection_feasible:
            failures.append("deflection")
        if not self.design.strength.face_pass:
            failures.append("face_yield")
        if not self.design.strength.core_shear_pass:
            failures.append("core_shear")
        if not self.local.wrinkling_pass:
            failures.append("wrinkling")
        if not self.local.core_compression_pass:
            failures.append("core_compression")
        if not failures:
            return "passes every modelled screen"
        return "fails: " + ", ".join(failures)


def assess_sandwich_design(
    basis: StudyBasis,
    core: OrthotropicCoreMaterial,
    core_strength: OrthotropicCoreStrength,
    core_compression: CoreCompressionProperties,
    direction: CoreShearDirection | str,
    strength_basis: StrengthBasis,
    requirement: DeflectionRequirement,
    local_basis: LocalScreenBasis,
) -> SandwichDesignAssessment:
    """Full preliminary screen of one candidate in one direction."""
    design = assess_candidate_design(
        basis, core, core_strength, direction, strength_basis, requirement
    )
    local = assess_local_failure(
        design.result, basis.face.youngs_modulus, core_compression, local_basis
    )
    return SandwichDesignAssessment(
        design=design,
        local=local,
        capacity=global_sandwich_capacity(design, local, basis.load),
    )


def _record_for(name: str, records: Sequence):
    for r in records:
        if r.name == name:
            return r
    raise KeyError(f"no record for candidate core {name!r}")


def build_sandwich_table(
    basis: StudyBasis,
    strength_basis: StrengthBasis,
    requirement: DeflectionRequirement,
    local_basis: LocalScreenBasis,
    cores: Iterable[OrthotropicCoreMaterial] = CANDIDATE_CORES,
    strengths: Iterable[OrthotropicCoreStrength] = CANDIDATE_CORE_STRENGTHS,
    compressions: Iterable[CoreCompressionProperties] = CANDIDATE_CORE_COMPRESSION,
    directions: Iterable[CoreShearDirection | str] = (CoreShearDirection.L, CoreShearDirection.W),
) -> list[SandwichDesignAssessment]:
    """Build the combined Milestone 4 screen, direction-major in database order.

    Ranks nothing and selects nothing.
    """
    core_list = list(cores)
    strength_list = list(strengths)
    compression_list = list(compressions)
    direction_list = [CoreShearDirection.parse(d) for d in directions]
    if not core_list:
        raise ValueError("cores must not be empty")
    if not direction_list:
        raise ValueError("directions must not be empty")
    return [
        assess_sandwich_design(
            basis,
            core,
            _record_for(core.name, strength_list),
            _record_for(core.name, compression_list),
            direction,
            strength_basis,
            requirement,
            local_basis,
        )
        for direction in direction_list
        for core in core_list
    ]


# -- local patch sweeps ----------------------------------------------------


@dataclass(frozen=True)
class LocalPatchSweepRow:
    """One local patch point. Direction-independent: crushing does not use G."""

    candidate: str
    force: float  # [N]
    patch_side: float | None  # [m] for a square patch, else None
    patch_area: float  # [m^2]
    pressure: float  # [Pa]
    compression_allowable: float  # [Pa]
    compression_margin: float  # [-]
    compression_pass: bool
    crush_force_limit: float  # [N]


def _patch_row(core_compression: CoreCompressionProperties, patch: LocalPatchLoad, side):
    allowable = core_compression.compression_strength
    ms = core_compression_margin(patch.pressure, allowable)
    return LocalPatchSweepRow(
        candidate=core_compression.name,
        force=patch.force,
        patch_side=side,
        patch_area=patch.patch_area,
        pressure=patch.pressure,
        compression_allowable=allowable,
        compression_margin=ms,
        compression_pass=ms >= 0.0,
        crush_force_limit=core_crush_force_limit(allowable, patch.patch_area),
    )


def local_patch_force_sweep(
    core_compression: CoreCompressionProperties,
    patch: LocalPatchLoad,
    forces: Iterable[float],
) -> list[LocalPatchSweepRow]:
    """Vary the local patch force at a FIXED footprint. Pressure is linear in force."""
    values = list(forces)
    if not values:
        raise ValueError("forces must not be empty")
    side = patch.patch_width if patch.patch_width == patch.patch_length else None
    return [_patch_row(core_compression, patch.with_force(f), side) for f in values]


def local_patch_size_sweep(
    core_compression: CoreCompressionProperties,
    patch: LocalPatchLoad,
    sides: Iterable[float],
) -> list[LocalPatchSweepRow]:
    """Vary a SQUARE patch side at fixed force. Pressure goes as 1/side^2."""
    values = list(sides)
    if not values:
        raise ValueError("sides must not be empty")
    return [_patch_row(core_compression, patch.with_square_side(s), s) for s in values]


# -- core depth vs wrinkling ------------------------------------------------


@dataclass(frozen=True)
class CoreDepthWrinklingRow:
    """One core-depth point with the wrinkling screen, in one direction."""

    core_thickness: float  # [m]
    direction: CoreShearDirection
    flexural_rigidity: float  # [N m^2]
    areal_mass: float  # [kg/m^2]
    face_stress: float  # at the study load [Pa]
    wrinkling_screening_stress: float  # [Pa]
    wrinkling_margin: float  # [-]
    wrinkling_limit: float  # [N]
    sandwich_limit: float  # [N]
    governing_constraint: SandwichConstraint


def core_depth_wrinkling_sweep(
    basis: StudyBasis,
    core: OrthotropicCoreMaterial,
    core_strength: OrthotropicCoreStrength,
    core_compression: CoreCompressionProperties,
    core_thicknesses: Iterable[float],
    strength_basis: StrengthBasis,
    requirement: DeflectionRequirement,
    local_basis: LocalScreenBasis,
    directions: Iterable[CoreShearDirection | str] = (CoreShearDirection.L, CoreShearDirection.W),
) -> list[CoreDepthWrinklingRow]:
    """Vary core depth and watch the wrinkling screen.

    With this screening convention ``sigma_wr`` depends only on material moduli, so
    it does NOT change with core depth - but the face stress demand falls steeply
    with depth, so the wrinkling MARGIN still improves. The test suite checks the
    actual model rather than assuming either behaviour.
    """
    values = list(core_thicknesses)
    direction_list = [CoreShearDirection.parse(d) for d in directions]
    if not values:
        raise ValueError("core_thicknesses must not be empty")
    if not direction_list:
        raise ValueError("directions must not be empty")

    rows: list[CoreDepthWrinklingRow] = []
    for direction in direction_list:
        for t_c in values:
            local_study = StudyBasis(
                geometry=SandwichGeometry(
                    width=basis.geometry.width,
                    face_thickness=basis.geometry.face_thickness,
                    core_thickness=t_c,
                    span=basis.geometry.span,
                ),
                face=basis.face,
                load=basis.load,
                shear_correction_factor=basis.shear_correction_factor,
            )
            a = assess_sandwich_design(
                local_study, core, core_strength, core_compression, direction,
                strength_basis, requirement, local_basis,
            )
            rows.append(
                CoreDepthWrinklingRow(
                    core_thickness=t_c,
                    direction=a.result.direction,
                    flexural_rigidity=a.result.flexural_rigidity,
                    areal_mass=a.result.areal_mass,
                    face_stress=a.local.face_stress,
                    wrinkling_screening_stress=a.local.wrinkling_screening_stress,
                    wrinkling_margin=a.local.wrinkling_margin,
                    wrinkling_limit=a.capacity.wrinkling_limit,
                    sandwich_limit=a.capacity.sandwich_limit,
                    governing_constraint=a.capacity.governing_constraint,
                )
            )
    return rows
