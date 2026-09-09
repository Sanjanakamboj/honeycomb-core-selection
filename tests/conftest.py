"""Shared reference case for the Milestone 1 verification tests.

The reference case below is deliberately simple so that every expected value in
the test suite can be written as INDEPENDENT arithmetic (literal formulas or
hand-computed constants) rather than by calling the package under test.
"""

from __future__ import annotations

import pytest

from sandwich_panel import CoreMaterial, FaceMaterial, SandwichGeometry, SandwichPanel

# Reference case (SI). Illustrative values, not datasheet values.
B = 0.40  # width            [m]
T_F = 0.0005  # face thickness   [m]
T_C = 0.015  # core thickness   [m]
L = 1.20  # span             [m]
E_F = 70.0e9  # face modulus     [Pa]
RHO_F = 2700.0  # face density     [kg/m^3]
RHO_C = 48.0  # core density     [kg/m^3]
G_C = 50.0e6  # core shear mod   [Pa]
P = 100.0  # point load       [N]


@pytest.fixture
def geometry() -> SandwichGeometry:
    return SandwichGeometry(width=B, face_thickness=T_F, core_thickness=T_C, span=L)


@pytest.fixture
def face() -> FaceMaterial:
    return FaceMaterial(name="illustrative face", youngs_modulus=E_F, density=RHO_F)


@pytest.fixture
def core() -> CoreMaterial:
    return CoreMaterial(name="illustrative core", density=RHO_C, shear_modulus=G_C)


@pytest.fixture
def panel(geometry, face, core) -> SandwichPanel:
    return SandwichPanel(geometry=geometry, face=face, core=core)
