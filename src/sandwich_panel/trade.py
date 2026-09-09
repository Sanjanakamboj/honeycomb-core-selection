"""Milestone 2 candidate-core trade framework.

Every candidate is evaluated on ONE common study basis - the same geometry, the
same face sheets, the same core depth and the same transverse load - so the
comparison is a clean material-property-only comparison. Geometry is never tuned
per candidate in this milestone.

Because the sandwich bending stiffness is face-dominated and the core carries no
normal-stress bending stiffness (Milestone 1 idealisation), ``EI`` and the
bending deflection are IDENTICAL across every candidate. Only two things move:

* areal mass, through the core density term ``rho_c t_c``
* shear deflection, through the selected directional shear modulus ``G_eff``

That invariance is the backbone of the trade and is locked down by tests.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from .directions import CoreShearDirection
from .geometry import SandwichGeometry
from .loads import DEFAULT_KAPPA
from .materials import CoreMaterial, FaceMaterial, OrthotropicCoreMaterial
from .panel import SandwichPanel
from .requirements import DeflectionAssessment, DeflectionRequirement
from .validation import require_positive_finite

__all__ = [
    "StudyBasis",
    "CoreCandidateResult",
    "TradeRow",
    "CoreDepthDirectionalRow",
    "evaluate_candidate",
    "evaluate_candidates",
    "build_trade_table",
    "is_dominated",
    "pareto_front",
    "core_density_sweep",
    "core_shear_modulus_sweep_at_fixed_density",
    "core_depth_directional_sweep",
]


@dataclass(frozen=True)
class StudyBasis:
    """The single common basis every candidate is evaluated against."""

    geometry: SandwichGeometry
    face: FaceMaterial
    load: float  # P [N], transverse central point load
    shear_correction_factor: float = DEFAULT_KAPPA

    def __post_init__(self) -> None:
        if not isinstance(self.geometry, SandwichGeometry):
            raise TypeError("geometry must be a SandwichGeometry")
        if not isinstance(self.face, FaceMaterial):
            raise TypeError("face must be a FaceMaterial")
        object.__setattr__(self, "load", require_positive_finite(self.load, "load"))
        object.__setattr__(
            self,
            "shear_correction_factor",
            require_positive_finite(self.shear_correction_factor, "shear_correction_factor"),
        )

    def panel_with(self, core: CoreMaterial) -> SandwichPanel:
        """Build the Milestone 1 panel for a direction-collapsed core."""
        return SandwichPanel(geometry=self.geometry, face=self.face, core=core)


@dataclass(frozen=True)
class CoreCandidateResult:
    """Sandwich response for one candidate core in one shear direction."""

    core_name: str
    direction: CoreShearDirection
    core_density: float  # rho_c [kg/m^3]
    effective_shear_modulus: float  # G_eff [Pa]
    core_thickness: float  # t_c [m]
    face_areal_mass: float  # [kg/m^2]
    core_areal_mass: float  # [kg/m^2]
    areal_mass: float  # m_A [kg/m^2]
    total_mass: float  # [kg]
    flexural_rigidity: float  # EI [N m^2]
    bending_deflection: float  # [m]
    shear_deflection: float  # [m]
    total_deflection: float  # [m]
    shear_fraction: float  # [-]
    max_face_stress: float  # [Pa], demand only - no allowable applied
    avg_core_shear_stress: float  # [Pa], demand only - no allowable applied
    core_family: str | None = None

    @property
    def specific_shear_stiffness(self) -> float:
        """First-order shear-stiffness-to-density indicator ``G_eff / rho_c`` [m^2/s^2].

        A coarse screening indicator, NOT a universal optimisation index. It says
        nothing about strength, stability, minimum manufacturable density or
        cost, and must never be used alone to rank cores.
        """
        return self.effective_shear_modulus / self.core_density

    @property
    def core_mass_fraction(self) -> float:
        return self.core_areal_mass / self.areal_mass

    @property
    def label(self) -> str:
        return f"{self.core_name} [{self.direction.value}]"


def evaluate_candidate(
    basis: StudyBasis,
    core: OrthotropicCoreMaterial,
    direction: CoreShearDirection | str,
) -> CoreCandidateResult:
    """Evaluate one candidate core in one shear direction on the common basis.

    The orthotropic core is collapsed to a single scalar effective shear modulus
    *before* it reaches the panel, so the Milestone 1 equations stay unchanged and
    orientation-agnostic.
    """
    if not isinstance(core, OrthotropicCoreMaterial):
        raise TypeError(
            f"core must be an OrthotropicCoreMaterial, got {type(core).__name__}"
        )
    chosen = CoreShearDirection.parse(direction)
    panel = basis.panel_with(core.as_effective_core(chosen))
    sec = panel.section()
    mass = panel.mass()
    res = panel.central_point_load(basis.load, basis.shear_correction_factor)

    return CoreCandidateResult(
        core_name=core.name,
        direction=chosen,
        core_density=core.density,
        effective_shear_modulus=core.shear_modulus(chosen),
        core_thickness=basis.geometry.core_thickness,
        face_areal_mass=mass.face_areal_mass,
        core_areal_mass=mass.core_areal_mass,
        areal_mass=mass.total_areal_mass,
        total_mass=mass.total_mass,
        flexural_rigidity=sec.flexural_rigidity,
        bending_deflection=res.bending_deflection,
        shear_deflection=res.shear_deflection,
        total_deflection=res.total_deflection,
        shear_fraction=res.shear_deflection_fraction,
        max_face_stress=res.max_face_stress,
        avg_core_shear_stress=res.avg_core_shear_stress,
        core_family=core.family,
    )


def evaluate_candidates(
    basis: StudyBasis,
    cores: Iterable[OrthotropicCoreMaterial],
    directions: Iterable[CoreShearDirection | str] = (CoreShearDirection.L, CoreShearDirection.W),
) -> list[CoreCandidateResult]:
    """Evaluate every candidate in every requested direction, in input order."""
    core_list = list(cores)
    direction_list = [CoreShearDirection.parse(d) for d in directions]
    if not core_list:
        raise ValueError("cores must not be empty")
    if not direction_list:
        raise ValueError("directions must not be empty")
    return [
        evaluate_candidate(basis, core, direction)
        for direction in direction_list
        for core in core_list
    ]


# -- feasibility screening -------------------------------------------------


@dataclass(frozen=True)
class TradeRow:
    """One trade-table row: a candidate result plus its stiffness screen."""

    result: CoreCandidateResult
    assessment: DeflectionAssessment | None

    @property
    def feasible(self) -> bool | None:
        return None if self.assessment is None else self.assessment.feasible

    @property
    def margin(self) -> float | None:
        return None if self.assessment is None else self.assessment.margin


def build_trade_table(
    basis: StudyBasis,
    cores: Iterable[OrthotropicCoreMaterial],
    directions: Iterable[CoreShearDirection | str] = (CoreShearDirection.L, CoreShearDirection.W),
    requirement: DeflectionRequirement | None = None,
) -> list[TradeRow]:
    """Build the mass-deflection trade table.

    Rows are returned in evaluation order (direction-major, then database order).
    Sorting, if any, belongs to the reporting layer - this function does not rank
    candidates and does not select one.
    """
    results = evaluate_candidates(basis, cores, directions)
    return [
        TradeRow(
            result=r,
            assessment=None if requirement is None else requirement.assess(r.total_deflection),
        )
        for r in results
    ]


# -- preliminary dominance (NOT optimisation, NOT selection) ---------------


def is_dominated(candidate: CoreCandidateResult, others: Iterable[CoreCandidateResult]) -> bool:
    """Is ``candidate`` dominated on (areal mass, total deflection)?

    Lower areal mass is better and lower total deflection is better. ``candidate``
    is dominated if some other result is no worse on both and strictly better on
    at least one.

    This is a preliminary screening aid on two stiffness/mass axes only. It is
    NOT optimisation and it does NOT select a core: a dominated candidate here may
    still win once strength, stability, thermal and manufacturing criteria enter.
    """
    for other in others:
        if other is candidate:
            continue
        no_worse = (
            other.areal_mass <= candidate.areal_mass
            and other.total_deflection <= candidate.total_deflection
        )
        strictly_better = (
            other.areal_mass < candidate.areal_mass
            or other.total_deflection < candidate.total_deflection
        )
        if no_worse and strictly_better:
            return True
    return False


def pareto_front(results: Iterable[CoreCandidateResult]) -> list[CoreCandidateResult]:
    """Non-dominated results on (areal mass, total deflection), in input order."""
    items = list(results)
    return [r for r in items if not is_dominated(r, items)]


# -- sensitivity sweeps through the trade layer ---------------------------


def _synthetic_core(name: str, density: float, shear_modulus: float) -> OrthotropicCoreMaterial:
    """An isotropic-in-shear synthetic core used only for sensitivity sweeps."""
    return OrthotropicCoreMaterial(
        name=name,
        density=density,
        shear_modulus_L=shear_modulus,
        shear_modulus_W=shear_modulus,
        family="synthetic sweep point",
        source_note="Synthetic sensitivity-sweep input; not a candidate material.",
    )


def core_density_sweep(
    basis: StudyBasis,
    densities: Iterable[float],
    shear_modulus: float,
    direction: CoreShearDirection | str = CoreShearDirection.L,
) -> list[CoreCandidateResult]:
    """Vary core density at FIXED shear modulus.

    Mass must move linearly; ``EI`` and every deflection must not move at all.
    """
    values: Sequence[float] = list(densities)
    if not values:
        raise ValueError("densities must not be empty")
    return [
        evaluate_candidate(
            basis, _synthetic_core(f"rho={rho:g}", rho, shear_modulus), direction
        )
        for rho in values
    ]


def core_shear_modulus_sweep_at_fixed_density(
    basis: StudyBasis,
    shear_moduli: Iterable[float],
    density: float,
    direction: CoreShearDirection | str = CoreShearDirection.L,
) -> list[CoreCandidateResult]:
    """Vary the effective core shear modulus at FIXED density.

    Mass, ``EI`` and the bending deflection must not move; the shear deflection
    must scale as ``1/G``.
    """
    values: Sequence[float] = list(shear_moduli)
    if not values:
        raise ValueError("shear_moduli must not be empty")
    return [
        evaluate_candidate(basis, _synthetic_core(f"G={g:g}", density, g), direction)
        for g in values
    ]


@dataclass(frozen=True)
class CoreDepthDirectionalRow:
    """One core-depth sweep point, evaluated in BOTH shear directions."""

    core_thickness: float  # t_c [m]
    total_thickness: float  # h [m]
    flexural_rigidity: float  # EI [N m^2]
    areal_mass: float  # [kg/m^2]
    bending_deflection: float  # [m], direction-independent
    shear_deflection_L: float  # [m]
    shear_deflection_W: float  # [m]
    total_deflection_L: float  # [m]
    total_deflection_W: float  # [m]
    shear_fraction_L: float  # [-]
    shear_fraction_W: float  # [-]


def core_depth_directional_sweep(
    basis: StudyBasis,
    core: OrthotropicCoreMaterial,
    core_thicknesses: Iterable[float],
) -> list[CoreDepthDirectionalRow]:
    """Vary core depth for ONE candidate, reporting both L and W.

    Increasing ``t_c`` acts on three things at once: it raises the face
    separation (so ``EI`` rises steeply), it adds core mass linearly, and it
    increases the core shear area ``A_s = b t_c`` (so the shear deflection falls).
    This sweep exposes all three together. It does NOT optimise ``t_c``.
    """
    values: Sequence[float] = list(core_thicknesses)
    if not values:
        raise ValueError("core_thicknesses must not be empty")

    rows: list[CoreDepthDirectionalRow] = []
    for t_c in values:
        local = StudyBasis(
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
        res_l = evaluate_candidate(local, core, CoreShearDirection.L)
        res_w = evaluate_candidate(local, core, CoreShearDirection.W)
        rows.append(
            CoreDepthDirectionalRow(
                core_thickness=t_c,
                total_thickness=local.geometry.total_thickness,
                flexural_rigidity=res_l.flexural_rigidity,
                areal_mass=res_l.areal_mass,
                bending_deflection=res_l.bending_deflection,
                shear_deflection_L=res_l.shear_deflection,
                shear_deflection_W=res_w.shear_deflection,
                total_deflection_L=res_l.total_deflection,
                total_deflection_W=res_w.total_deflection,
                shear_fraction_L=res_l.shear_fraction,
                shear_fraction_W=res_w.shear_fraction,
            )
        )
    return rows
