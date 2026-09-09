"""Milestone 5: integrated screening and the illustrative preliminary core selection.

Additive over Milestone 4. Nothing in the earlier layers changes meaning; this
module composes them and adds the modal screen.

FOUR MARGIN FAMILIES, NEVER BLENDED
-----------------------------------
* deflection margin - a LENGTH [m]
* global strength margins (face yield, average core shear) - dimensionless
* local failure margins (wrinkling, core compression) - dimensionless
* frequency margin - a FREQUENCY [Hz]

``overall_feasible`` is the logical AND of the four booleans. No numerical
minimum, sum or average is ever taken across them.

For a defensible *cross-mode* comparison the module instead reports dimensionless
**utilisations** (demand / capacity, so ``<= 1`` passes) for each screen. Those
are comparable by construction. The local patch utilisation is kept identified
separately, because it belongs to an independent load case with no defined
relationship to the global central load.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from .core_database import CANDIDATE_CORES
from .directions import CoreShearDirection
from .geometry import SandwichGeometry
from .local_failure import CoreCompressionProperties
from .local_failure_database import CANDIDATE_CORE_COMPRESSION
from .materials import OrthotropicCoreMaterial
from .modal import (
    DEFAULT_MODAL_KAPPA,
    FrequencyAssessment,
    FrequencyRequirement,
    ModalFrequencyResult,
    distributed_mass,
    modal_frequency,
)
from .requirements import DeflectionRequirement
from .sandwich_screen import (
    LocalScreenBasis,
    SandwichDesignAssessment,
    assess_sandwich_design,
)
from .strength import OrthotropicCoreStrength, StrengthBasis
from .strength_database import CANDIDATE_CORE_STRENGTHS
from .trade import StudyBasis

__all__ = [
    "PreliminaryScreens",
    "CoreModalAssessment",
    "ScreenUtilisation",
    "IntegratedDesignAssessment",
    "PreliminaryCoreSelection",
    "CoreDepthModalRow",
    "ModalSweepRow",
    "RequirementSweepRow",
    "DeflectionLimitSweepRow",
    "assess_core_modal",
    "assess_integrated_design",
    "build_integrated_table",
    "select_preliminary_core",
    "core_depth_modal_sweep",
    "modal_density_sweep",
    "modal_shear_modulus_sweep",
    "modal_face_thickness_sweep",
    "frequency_requirement_sweep",
    "deflection_limit_sweep",
]


@dataclass(frozen=True)
class PreliminaryScreens:
    """The four preliminary screen definitions applied to a study."""

    deflection: DeflectionRequirement
    strength: StrengthBasis
    local: LocalScreenBasis
    frequency: FrequencyRequirement

    def __post_init__(self) -> None:
        for name, expected in (
            ("deflection", DeflectionRequirement),
            ("strength", StrengthBasis),
            ("local", LocalScreenBasis),
            ("frequency", FrequencyRequirement),
        ):
            if not isinstance(getattr(self, name), expected):
                raise TypeError(f"{name} must be a {expected.__name__}")

    def with_frequency(self, requirement: FrequencyRequirement) -> "PreliminaryScreens":
        return PreliminaryScreens(
            deflection=self.deflection, strength=self.strength,
            local=self.local, frequency=requirement,
        )

    def with_deflection(self, requirement: DeflectionRequirement) -> "PreliminaryScreens":
        return PreliminaryScreens(
            deflection=requirement, strength=self.strength,
            local=self.local, frequency=self.frequency,
        )


# -- modal assessment of one candidate ------------------------------------


@dataclass(frozen=True)
class CoreModalAssessment:
    """First-mode modal screen for one candidate in one shear direction."""

    candidate: str
    direction: CoreShearDirection
    core_density: float  # rho_c [kg/m^3]
    effective_shear_modulus: float  # G_eff [Pa]
    areal_mass: float  # m_A [kg/m^2]
    distributed_mass: float  # mu [kg/m]
    modal: ModalFrequencyResult
    assessment: FrequencyAssessment

    @property
    def bending_only_frequency(self) -> float:
        return self.modal.bending_only_frequency

    @property
    def frequency(self) -> float:
        """The shear-corrected first-mode frequency - the primary screening value."""
        return self.modal.shear_corrected_frequency

    @property
    def margin_hz(self) -> float:
        return self.assessment.margin_hz

    @property
    def normalised_margin(self) -> float:
        return self.assessment.normalised_margin

    @property
    def modal_feasible(self) -> bool:
        return self.assessment.feasible

    @property
    def frequency_to_areal_mass(self) -> float:
        """First-order frequency-to-areal-mass indicator ``f_1 / m_A`` [Hz m^2/kg].

        A coarse screening diagnostic, NOT an optimisation objective. It may rank
        candidates quite differently from the Milestone 2 ``G/rho`` indicator or
        the Milestone 3 load-capacity indicator, which is exactly why it is
        reported rather than assumed.
        """
        return self.frequency / self.areal_mass

    @property
    def label(self) -> str:
        return f"{self.candidate} [{self.direction.value}]"


def assess_core_modal(
    basis: StudyBasis,
    core: OrthotropicCoreMaterial,
    direction: CoreShearDirection | str,
    requirement: FrequencyRequirement,
    mode_number: int | None = None,
    shear_correction_factor: float = DEFAULT_MODAL_KAPPA,
) -> CoreModalAssessment:
    """Screen one candidate/direction against a minimum-frequency requirement.

    ``EI`` and the areal mass come straight from the Milestone 1-2 mechanics; only
    ``G_eff`` differs between the L and W configurations.
    """
    from .trade import evaluate_candidate

    chosen = CoreShearDirection.parse(direction)
    result = evaluate_candidate(basis, core, chosen)
    mu = distributed_mass(result.areal_mass, basis.geometry.width)
    n = requirement.mode_number if mode_number is None else mode_number

    modal = modal_frequency(
        flexural_rigidity=result.flexural_rigidity,
        distributed_mass_=mu,
        span=basis.geometry.span,
        core_shear_modulus=result.effective_shear_modulus,
        core_shear_area=basis.geometry.core_shear_area,
        mode_number=n,
        shear_correction_factor=shear_correction_factor,
        direction=chosen,
    )
    return CoreModalAssessment(
        candidate=core.name,
        direction=chosen,
        core_density=core.density,
        effective_shear_modulus=result.effective_shear_modulus,
        areal_mass=result.areal_mass,
        distributed_mass=mu,
        modal=modal,
        assessment=requirement.assess(modal.shear_corrected_frequency),
    )


# -- cross-mode utilisation ------------------------------------------------


@dataclass(frozen=True)
class ScreenUtilisation:
    """Dimensionless demand/capacity ratios; ``<= 1`` passes.

    Because the raw margins carry four different units, utilisations are the only
    defensible way to say which screen is *closest*. The local patch utilisation is
    reported separately and is NOT part of the global comparison: it belongs to an
    independent load case.
    """

    deflection: float  # delta / delta_allowable
    face_yield: float  # sigma_face / sigma_allowable
    core_shear: float  # tau / tau_allowable
    wrinkling: float  # sigma_face / sigma_wr,screen
    frequency: float  # f_required / f_actual
    core_compression_local_patch: float  # p_patch / sigma_c,allow  (separate case)

    @property
    def global_screens(self) -> dict[str, float]:
        """The five screens driven by the global central-load / modal case."""
        return {
            "deflection": self.deflection,
            "face_yield": self.face_yield,
            "core_shear": self.core_shear,
            "wrinkling": self.wrinkling,
            "frequency": self.frequency,
        }

    @property
    def closest_global_screen(self) -> str:
        """Name of the highest-utilisation global screen (deterministic ties)."""
        screens = self.global_screens
        order = list(screens)
        return max(order, key=lambda k: (screens[k], -order.index(k)))

    @property
    def closest_global_utilisation(self) -> float:
        return self.global_screens[self.closest_global_screen]


def _utilisation(
    sandwich: SandwichDesignAssessment,
    modal: CoreModalAssessment,
    screens: PreliminaryScreens,
) -> ScreenUtilisation:
    strength = sandwich.design.strength
    local = sandwich.local
    return ScreenUtilisation(
        deflection=sandwich.result.total_deflection / screens.deflection.maximum_total_deflection,
        face_yield=strength.face_stress / strength.face_allowable,
        core_shear=strength.core_shear_stress / strength.core_shear_allowable,
        wrinkling=local.face_stress / local.wrinkling_screening_stress,
        frequency=screens.frequency.minimum_frequency_hz / modal.frequency,
        core_compression_local_patch=(
            local.local_core_compression_stress / local.core_compression_allowable
        ),
    )


# -- integrated assessment -------------------------------------------------


@dataclass(frozen=True)
class IntegratedDesignAssessment:
    """All four preliminary screens for one candidate/direction configuration."""

    sandwich: SandwichDesignAssessment
    modal: CoreModalAssessment
    utilisation: ScreenUtilisation

    @property
    def result(self):
        return self.sandwich.result

    @property
    def label(self) -> str:
        return self.sandwich.label

    @property
    def areal_mass(self) -> float:
        return self.sandwich.result.areal_mass

    @property
    def total_panel_mass(self) -> float:
        return self.sandwich.result.total_mass

    @property
    def deflection_feasible(self) -> bool:
        return self.sandwich.deflection_feasible

    @property
    def global_strength_feasible(self) -> bool:
        return self.sandwich.global_strength_feasible

    @property
    def local_failure_feasible(self) -> bool:
        return self.sandwich.local_failure_feasible

    @property
    def modal_feasible(self) -> bool:
        return self.modal.modal_feasible

    @property
    def static_feasible(self) -> bool:
        """The Milestone 2-4 screens only, without the modal one."""
        return (
            self.deflection_feasible
            and self.global_strength_feasible
            and self.local_failure_feasible
        )

    @property
    def overall_feasible(self) -> bool:
        return self.static_feasible and self.modal_feasible

    @property
    def failing_screens(self) -> tuple[str, ...]:
        failures = []
        if not self.deflection_feasible:
            failures.append("deflection")
        if not self.sandwich.design.strength.face_pass:
            failures.append("face_yield")
        if not self.sandwich.design.strength.core_shear_pass:
            failures.append("core_shear")
        if not self.sandwich.local.wrinkling_pass:
            failures.append("wrinkling")
        if not self.sandwich.local.core_compression_pass:
            failures.append("core_compression")
        if not self.modal_feasible:
            failures.append("frequency")
        return tuple(failures)


def assess_integrated_design(
    basis: StudyBasis,
    core: OrthotropicCoreMaterial,
    core_strength: OrthotropicCoreStrength,
    core_compression: CoreCompressionProperties,
    direction: CoreShearDirection | str,
    screens: PreliminaryScreens,
) -> IntegratedDesignAssessment:
    """Run all four preliminary screens on one candidate/direction configuration."""
    if not isinstance(screens, PreliminaryScreens):
        raise TypeError("screens must be a PreliminaryScreens")
    sandwich = assess_sandwich_design(
        basis, core, core_strength, core_compression, direction,
        screens.strength, screens.deflection, screens.local,
    )
    modal = assess_core_modal(basis, core, direction, screens.frequency)
    return IntegratedDesignAssessment(
        sandwich=sandwich,
        modal=modal,
        utilisation=_utilisation(sandwich, modal, screens),
    )


def _record_for(name: str, records: Sequence):
    for r in records:
        if r.name == name:
            return r
    raise KeyError(f"no record for candidate core {name!r}")


def build_integrated_table(
    basis: StudyBasis,
    screens: PreliminaryScreens,
    cores: Iterable[OrthotropicCoreMaterial] = CANDIDATE_CORES,
    strengths: Iterable[OrthotropicCoreStrength] = CANDIDATE_CORE_STRENGTHS,
    compressions: Iterable[CoreCompressionProperties] = CANDIDATE_CORE_COMPRESSION,
    directions: Iterable[CoreShearDirection | str] = (CoreShearDirection.L, CoreShearDirection.W),
) -> list[IntegratedDesignAssessment]:
    """Every candidate/direction configuration, direction-major in database order."""
    core_list = list(cores)
    strength_list = list(strengths)
    compression_list = list(compressions)
    direction_list = [CoreShearDirection.parse(d) for d in directions]
    if not core_list:
        raise ValueError("cores must not be empty")
    if not direction_list:
        raise ValueError("directions must not be empty")
    return [
        assess_integrated_design(
            basis, core, _record_for(core.name, strength_list),
            _record_for(core.name, compression_list), direction, screens,
        )
        for direction in direction_list
        for core in core_list
    ]


# -- preliminary selection -------------------------------------------------


@dataclass(frozen=True)
class PreliminaryCoreSelection:
    """An ILLUSTRATIVE PRELIMINARY CORE SELECTION.

    This is **not** a qualified core, a flight-selected material, a certified
    design, a manufacturer recommendation or an optimised solution. Every material
    property behind it is illustrative, and both the deflection limit and the
    frequency requirement are illustrative screening thresholds.

    ``direction`` means the beam strip is aligned with that effective core shear
    direction. It is a one-dimensional orientation choice, not a 2-D panel layup
    optimisation.
    """

    candidate: str
    direction: CoreShearDirection
    core_density: float  # [kg/m^3]
    areal_mass: float  # [kg/m^2]
    total_panel_mass: float  # [kg]
    first_mode_frequency: float  # [Hz]
    frequency_margin_hz: float  # [Hz]
    total_deflection: float  # [m]
    deflection_feasible: bool
    global_strength_feasible: bool
    local_failure_feasible: bool
    modal_feasible: bool
    closest_global_screen: str
    closest_global_utilisation: float
    local_patch_utilisation: float
    feasible_configuration_count: int
    selection_basis: str

    @property
    def label(self) -> str:
        return f"{self.candidate} [{self.direction.value}]"


#: The selection policy, stated once and applied deterministically.
SELECTION_BASIS = (
    "minimum areal mass among configurations passing all preliminary screens "
    "(deflection, global strength, local failure, modal); ties broken by larger "
    "frequency margin, then by candidate database order, then by L before W"
)


def select_preliminary_core(
    assessments: Iterable[IntegratedDesignAssessment],
) -> PreliminaryCoreSelection | None:
    """Apply the explicit selection policy. Returns ``None`` if nothing is feasible.

    The policy is deterministic and stated in :data:`SELECTION_BASIS`; there is no
    hidden judgement anywhere in it.
    """
    items = list(assessments)
    order = {id(a): i for i, a in enumerate(items)}
    feasible = [a for a in items if a.overall_feasible]
    if not feasible:
        return None

    chosen = min(
        feasible,
        key=lambda a: (a.areal_mass, -a.modal.margin_hz, order[id(a)]),
    )
    return PreliminaryCoreSelection(
        candidate=chosen.result.core_name,
        direction=chosen.result.direction,
        core_density=chosen.result.core_density,
        areal_mass=chosen.areal_mass,
        total_panel_mass=chosen.total_panel_mass,
        first_mode_frequency=chosen.modal.frequency,
        frequency_margin_hz=chosen.modal.margin_hz,
        total_deflection=chosen.result.total_deflection,
        deflection_feasible=chosen.deflection_feasible,
        global_strength_feasible=chosen.global_strength_feasible,
        local_failure_feasible=chosen.local_failure_feasible,
        modal_feasible=chosen.modal_feasible,
        closest_global_screen=chosen.utilisation.closest_global_screen,
        closest_global_utilisation=chosen.utilisation.closest_global_utilisation,
        local_patch_utilisation=chosen.utilisation.core_compression_local_patch,
        feasible_configuration_count=len(feasible),
        selection_basis=SELECTION_BASIS,
    )


# -- sweeps ----------------------------------------------------------------


def _rebased(basis: StudyBasis, **changes) -> StudyBasis:
    geometry = SandwichGeometry(
        width=changes.get("width", basis.geometry.width),
        face_thickness=changes.get("face_thickness", basis.geometry.face_thickness),
        core_thickness=changes.get("core_thickness", basis.geometry.core_thickness),
        span=changes.get("span", basis.geometry.span),
    )
    return StudyBasis(
        geometry=geometry,
        face=basis.face,
        load=changes.get("load", basis.load),
        shear_correction_factor=basis.shear_correction_factor,
    )


def _synthetic_core(name: str, density: float, shear_modulus: float) -> OrthotropicCoreMaterial:
    return OrthotropicCoreMaterial(
        name=name, density=density,
        shear_modulus_L=shear_modulus, shear_modulus_W=shear_modulus,
        family="synthetic sweep point",
        source_note="Synthetic sensitivity-sweep input; not a candidate material.",
    )


@dataclass(frozen=True)
class CoreDepthModalRow:
    core_thickness: float  # [m]
    direction: CoreShearDirection
    flexural_rigidity: float  # [N m^2]
    areal_mass: float  # [kg/m^2]
    distributed_mass: float  # [kg/m]
    shear_area: float  # [m^2]
    core_shear_modulus: float  # [Pa]
    shear_flexibility_ratio: float  # [-]
    bending_only_frequency: float  # [Hz]
    frequency: float  # [Hz]
    margin_hz: float  # [Hz]
    modal_feasible: bool


def core_depth_modal_sweep(
    basis: StudyBasis,
    core: OrthotropicCoreMaterial,
    core_thicknesses: Iterable[float],
    requirement: FrequencyRequirement,
    directions: Iterable[CoreShearDirection | str] = (CoreShearDirection.L, CoreShearDirection.W),
) -> list[CoreDepthModalRow]:
    """Vary core depth and watch the fundamental frequency in both directions."""
    values = list(core_thicknesses)
    direction_list = [CoreShearDirection.parse(d) for d in directions]
    if not values:
        raise ValueError("core_thicknesses must not be empty")
    if not direction_list:
        raise ValueError("directions must not be empty")

    rows: list[CoreDepthModalRow] = []
    for direction in direction_list:
        for t_c in values:
            local = _rebased(basis, core_thickness=t_c)
            a = assess_core_modal(local, core, direction, requirement)
            rows.append(
                CoreDepthModalRow(
                    core_thickness=t_c,
                    direction=a.direction,
                    flexural_rigidity=a.modal.flexural_rigidity,
                    areal_mass=a.areal_mass,
                    distributed_mass=a.distributed_mass,
                    shear_area=a.modal.shear_area,
                    core_shear_modulus=a.effective_shear_modulus,
                    shear_flexibility_ratio=a.modal.shear_flexibility_ratio,
                    bending_only_frequency=a.bending_only_frequency,
                    frequency=a.frequency,
                    margin_hz=a.margin_hz,
                    modal_feasible=a.modal_feasible,
                )
            )
    return rows


@dataclass(frozen=True)
class ModalSweepRow:
    """One generic modal sweep point."""

    swept_value: float
    core_density: float
    core_shear_modulus: float
    face_thickness: float
    flexural_rigidity: float
    areal_mass: float
    distributed_mass: float
    bending_only_frequency: float
    frequency: float
    modal_feasible: bool


def _modal_row(swept, basis, core, requirement) -> ModalSweepRow:
    a = assess_core_modal(basis, core, CoreShearDirection.L, requirement)
    return ModalSweepRow(
        swept_value=swept,
        core_density=core.density,
        core_shear_modulus=a.effective_shear_modulus,
        face_thickness=basis.geometry.face_thickness,
        flexural_rigidity=a.modal.flexural_rigidity,
        areal_mass=a.areal_mass,
        distributed_mass=a.distributed_mass,
        bending_only_frequency=a.bending_only_frequency,
        frequency=a.frequency,
        modal_feasible=a.modal_feasible,
    )


def modal_density_sweep(
    basis: StudyBasis,
    densities: Iterable[float],
    shear_modulus: float,
    requirement: FrequencyRequirement,
) -> list[ModalSweepRow]:
    """Vary core density at FIXED shear modulus, geometry and EI."""
    values = list(densities)
    if not values:
        raise ValueError("densities must not be empty")
    return [
        _modal_row(rho, basis, _synthetic_core(f"rho={rho:g}", rho, shear_modulus), requirement)
        for rho in values
    ]


def modal_shear_modulus_sweep(
    basis: StudyBasis,
    shear_moduli: Iterable[float],
    density: float,
    requirement: FrequencyRequirement,
) -> list[ModalSweepRow]:
    """Vary the core shear modulus at FIXED density and geometry."""
    values = list(shear_moduli)
    if not values:
        raise ValueError("shear_moduli must not be empty")
    return [
        _modal_row(g, basis, _synthetic_core(f"G={g:g}", density, g), requirement)
        for g in values
    ]


def modal_face_thickness_sweep(
    basis: StudyBasis,
    face_thicknesses: Iterable[float],
    core: OrthotropicCoreMaterial,
    requirement: FrequencyRequirement,
) -> list[ModalSweepRow]:
    """Vary face thickness: EI and face mass both rise, so the trend is computed."""
    values = list(face_thicknesses)
    if not values:
        raise ValueError("face_thicknesses must not be empty")
    return [
        _modal_row(t_f, _rebased(basis, face_thickness=t_f), core, requirement)
        for t_f in values
    ]


@dataclass(frozen=True)
class RequirementSweepRow:
    required_frequency_hz: float
    feasible_count: int
    total_count: int
    lightest_feasible_label: str | None
    lightest_feasible_areal_mass: float | None


def frequency_requirement_sweep(
    basis: StudyBasis,
    screens: PreliminaryScreens,
    required_frequencies: Iterable[float],
) -> list[RequirementSweepRow]:
    """How the feasible set responds to the illustrative frequency threshold."""
    values = list(required_frequencies)
    if not values:
        raise ValueError("required_frequencies must not be empty")

    rows: list[RequirementSweepRow] = []
    for f_req in values:
        variant = screens.with_frequency(
            FrequencyRequirement(
                minimum_frequency_hz=f_req,
                mode_number=screens.frequency.mode_number,
                label=screens.frequency.label,
            )
        )
        table = build_integrated_table(basis, variant)
        selection = select_preliminary_core(table)
        feasible = [a for a in table if a.overall_feasible]
        rows.append(
            RequirementSweepRow(
                required_frequency_hz=f_req,
                feasible_count=len(feasible),
                total_count=len(table),
                lightest_feasible_label=None if selection is None else selection.label,
                lightest_feasible_areal_mass=None if selection is None else selection.areal_mass,
            )
        )
    return rows


@dataclass(frozen=True)
class DeflectionLimitSweepRow:
    span_divisor: float
    allowable_deflection: float  # [m]
    static_feasible_count: int
    overall_feasible_count: int
    total_count: int
    selected_label: str | None


def deflection_limit_sweep(
    basis: StudyBasis,
    screens: PreliminaryScreens,
    span_divisors: Iterable[float],
) -> list[DeflectionLimitSweepRow]:
    """How the feasible set and the selection respond to the placeholder L/N limit.

    The canonical Milestone 2 limit is NOT redefined; this varies a local copy.
    """
    values = list(span_divisors)
    if not values:
        raise ValueError("span_divisors must not be empty")

    rows: list[DeflectionLimitSweepRow] = []
    for divisor in values:
        allowable = basis.geometry.span / divisor
        variant = screens.with_deflection(
            DeflectionRequirement(
                maximum_total_deflection=allowable,
                label=f"illustrative deflection limit = span/{divisor:g}",
            )
        )
        table = build_integrated_table(basis, variant)
        selection = select_preliminary_core(table)
        rows.append(
            DeflectionLimitSweepRow(
                span_divisor=divisor,
                allowable_deflection=allowable,
                static_feasible_count=sum(1 for a in table if a.static_feasible),
                overall_feasible_count=sum(1 for a in table if a.overall_feasible),
                total_count=len(table),
                selected_label=None if selection is None else selection.label,
            )
        )
    return rows
