"""Milestone 1 sensitivity sweeps.

These answer the key Milestone 1 question: does the model capture the stiffness
and mass leverage of increasing lightweight core depth while keeping the thin
faces structurally active?

Ratios in each sweep are taken against the FIRST row of that sweep.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from .panel import SandwichPanel

__all__ = [
    "CoreDepthRow",
    "FaceThicknessRow",
    "CoreShearRow",
    "core_depth_sweep",
    "face_thickness_sweep",
    "core_shear_modulus_sweep",
]


@dataclass(frozen=True)
class CoreDepthRow:
    core_thickness: float  # [m]
    total_thickness: float  # [m]
    flexural_rigidity: float  # EI [N m^2]
    flexural_rigidity_ratio: float  # EI / EI_baseline [-]
    areal_mass: float  # [kg/m^2]
    areal_mass_ratio: float  # [-]
    total_deflection: float  # [m]


@dataclass(frozen=True)
class FaceThicknessRow:
    face_thickness: float  # [m]
    total_thickness: float  # [m]
    flexural_rigidity: float  # EI [N m^2]
    areal_mass: float  # [kg/m^2]
    max_face_stress: float  # [Pa]
    total_deflection: float  # [m]


@dataclass(frozen=True)
class CoreShearRow:
    core_shear_modulus: float  # G_c [Pa]
    bending_deflection: float  # [m]
    shear_deflection: float  # [m]
    total_deflection: float  # [m]
    shear_deflection_fraction: float  # [-]


def core_depth_sweep(
    panel: SandwichPanel, core_thicknesses: Iterable[float], load: float
) -> list[CoreDepthRow]:
    """Vary core thickness with ``b``, ``t_f``, ``E_f`` and span held fixed."""
    values: Sequence[float] = list(core_thicknesses)
    if not values:
        raise ValueError("core_thicknesses must not be empty")
    baseline = panel.with_geometry(core_thickness=values[0])
    ei_ref = baseline.flexural_rigidity
    m_ref = baseline.areal_mass

    rows: list[CoreDepthRow] = []
    for t_c in values:
        variant = panel.with_geometry(core_thickness=t_c)
        ei = variant.flexural_rigidity
        m_a = variant.areal_mass
        rows.append(
            CoreDepthRow(
                core_thickness=t_c,
                total_thickness=variant.geometry.total_thickness,
                flexural_rigidity=ei,
                flexural_rigidity_ratio=ei / ei_ref,
                areal_mass=m_a,
                areal_mass_ratio=m_a / m_ref,
                total_deflection=variant.central_point_load(load).total_deflection,
            )
        )
    return rows


def face_thickness_sweep(
    panel: SandwichPanel, face_thicknesses: Iterable[float], load: float
) -> list[FaceThicknessRow]:
    """Vary face thickness with the core depth and span held fixed."""
    values: Sequence[float] = list(face_thicknesses)
    if not values:
        raise ValueError("face_thicknesses must not be empty")

    rows: list[FaceThicknessRow] = []
    for t_f in values:
        variant = panel.with_geometry(face_thickness=t_f)
        response = variant.central_point_load(load)
        rows.append(
            FaceThicknessRow(
                face_thickness=t_f,
                total_thickness=variant.geometry.total_thickness,
                flexural_rigidity=variant.flexural_rigidity,
                areal_mass=variant.areal_mass,
                max_face_stress=response.max_face_stress,
                total_deflection=response.total_deflection,
            )
        )
    return rows


def core_shear_modulus_sweep(
    panel: SandwichPanel, shear_moduli: Iterable[float], load: float
) -> list[CoreShearRow]:
    """Vary the effective core shear modulus with geometry held fixed.

    The bending deflection is independent of ``G_c`` and must be identical
    across every row; the test suite asserts that invariance.
    """
    values: Sequence[float] = list(shear_moduli)
    if not values:
        raise ValueError("shear_moduli must not be empty")

    rows: list[CoreShearRow] = []
    for g_c in values:
        response = panel.with_core_shear_modulus(g_c).central_point_load(load)
        rows.append(
            CoreShearRow(
                core_shear_modulus=g_c,
                bending_deflection=response.bending_deflection,
                shear_deflection=response.shear_deflection,
                total_deflection=response.total_deflection,
                shear_deflection_fraction=response.shear_deflection_fraction,
            )
        )
    return rows
