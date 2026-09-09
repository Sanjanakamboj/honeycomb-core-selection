"""A-H: distributed mass and the bending-only (Euler-Bernoulli) reference frequency."""

from __future__ import annotations

import math

import pytest

from sandwich_panel import (
    CoreMaterial,
    FaceMaterial,
    SandwichGeometry,
    SandwichPanel,
    bending_only_frequency,
    distributed_mass,
    mass_properties,
)

from .conftest import M5_F1_BENDING, M5_MU

EI = 2913.4933333333
SPAN = 1.5


# -- A. distributed mass hand calculation ----------------------------------


def test_distributed_mass_hand_calc(m2_geometry, m2_face, core):
    # m_A = 2*2700*0.0004 + 48*0.020 = 2.16 + 0.96 = 3.12 kg/m^2 (M1 `core` fixture)
    m = mass_properties(m2_geometry, m2_face, core)
    assert m.total_areal_mass == pytest.approx(3.12, rel=1e-12)
    assert distributed_mass(m.total_areal_mass, m2_geometry.width) == pytest.approx(
        3.12 * 0.5, rel=1e-12
    )
    assert distributed_mass(2.96, 0.5) == pytest.approx(M5_MU, rel=1e-15)


def test_distributed_mass_is_areal_mass_times_width():
    assert distributed_mass(3.0, 0.4) == pytest.approx(1.2, rel=1e-15)


# -- B. width scaling -------------------------------------------------------


def test_distributed_mass_scales_linearly_with_width():
    base = distributed_mass(2.96, 0.5)
    assert distributed_mass(2.96, 1.0) == pytest.approx(2 * base, rel=1e-15)
    assert distributed_mass(2.96, 0.25) == pytest.approx(base / 2, rel=1e-15)


# -- C. density scaling -----------------------------------------------------


def test_distributed_mass_scales_with_core_density(m2_geometry, m2_face):
    light = CoreMaterial(name="light", density=30.0, shear_modulus=20e6)
    heavy = CoreMaterial(name="heavy", density=60.0, shear_modulus=20e6)
    ml = mass_properties(m2_geometry, m2_face, light).total_areal_mass
    mh = mass_properties(m2_geometry, m2_face, heavy).total_areal_mass
    # Core term doubles; the face term (2.16) does not.
    assert ml == pytest.approx(2.16 + 30 * 0.020, rel=1e-12)
    assert mh == pytest.approx(2.16 + 60 * 0.020, rel=1e-12)
    assert distributed_mass(mh, 0.5) - distributed_mass(ml, 0.5) == pytest.approx(
        0.5 * 30 * 0.020, rel=1e-12
    )


def test_distributed_mass_carries_no_hidden_terms(m2_geometry, m2_face, core):
    # Bare faces + core only: no cells, adhesive, harness or mechanisms.
    panel = SandwichPanel(geometry=m2_geometry, face=m2_face, core=core)
    m = panel.mass()
    assert m.total_areal_mass == pytest.approx(
        2 * m2_face.density * m2_geometry.face_thickness
        + core.density * m2_geometry.core_thickness,
        rel=1e-15,
    )
    assert distributed_mass(m.total_areal_mass, m2_geometry.width) == pytest.approx(
        m.total_mass / m2_geometry.span, rel=1e-12
    )


@pytest.mark.parametrize("bad", [0.0, -1.0, math.nan, math.inf, -math.inf])
def test_distributed_mass_validates_inputs(bad):
    with pytest.raises(ValueError):
        distributed_mass(bad, 0.5)
    with pytest.raises(ValueError):
        distributed_mass(2.96, bad)


# -- D. bending-only f1 hand calculation ------------------------------------


def test_bending_only_first_mode_hand_calc():
    # f1 = (pi / (2 L^2)) sqrt(EI/mu)
    expected = (math.pi / (2 * SPAN**2)) * math.sqrt(EI / M5_MU)
    assert bending_only_frequency(EI, M5_MU, SPAN, 1) == pytest.approx(expected, rel=1e-12)
    assert bending_only_frequency(EI, M5_MU, SPAN, 1) == pytest.approx(M5_F1_BENDING, rel=1e-9)
    assert bending_only_frequency(EI, M5_MU, SPAN, 1) == pytest.approx(30.975, rel=1e-4)


def test_bending_only_matches_the_omega_form():
    # omega_n = (n pi / L)^2 sqrt(EI/mu) ; f = omega / (2 pi)
    k = math.pi / SPAN
    omega = k**2 * math.sqrt(EI / M5_MU)
    assert bending_only_frequency(EI, M5_MU, SPAN, 1) == pytest.approx(
        omega / (2 * math.pi), rel=1e-15
    )


# -- E. mode-number n^2 identity --------------------------------------------


def test_bending_only_scales_exactly_as_n_squared():
    f1 = bending_only_frequency(EI, M5_MU, SPAN, 1)
    for n in (2, 3, 4, 5):
        assert bending_only_frequency(EI, M5_MU, SPAN, n) == pytest.approx(
            n**2 * f1, rel=1e-12
        )


# -- F. f proportional to sqrt(EI) ------------------------------------------


def test_bending_only_scales_as_sqrt_EI():
    base = bending_only_frequency(EI, M5_MU, SPAN, 1)
    assert bending_only_frequency(4 * EI, M5_MU, SPAN, 1) == pytest.approx(2 * base, rel=1e-12)
    assert bending_only_frequency(EI / 9, M5_MU, SPAN, 1) == pytest.approx(base / 3, rel=1e-12)


# -- G. f proportional to 1/sqrt(mu) ----------------------------------------


def test_bending_only_scales_as_inverse_sqrt_mu():
    base = bending_only_frequency(EI, M5_MU, SPAN, 1)
    assert bending_only_frequency(EI, 4 * M5_MU, SPAN, 1) == pytest.approx(base / 2, rel=1e-12)
    assert bending_only_frequency(EI, M5_MU / 9, SPAN, 1) == pytest.approx(3 * base, rel=1e-12)


# -- H. f proportional to 1/L^2 ---------------------------------------------


def test_bending_only_scales_as_inverse_span_squared():
    base = bending_only_frequency(EI, M5_MU, SPAN, 1)
    assert bending_only_frequency(EI, M5_MU, 2 * SPAN, 1) == pytest.approx(base / 4, rel=1e-12)
    assert bending_only_frequency(EI, M5_MU, SPAN / 2, 1) == pytest.approx(4 * base, rel=1e-12)


# -- validation --------------------------------------------------------------


@pytest.mark.parametrize("bad", [0.0, -1.0, math.nan, math.inf])
def test_bending_only_validates_every_input(bad):
    with pytest.raises(ValueError):
        bending_only_frequency(bad, M5_MU, SPAN, 1)
    with pytest.raises(ValueError):
        bending_only_frequency(EI, bad, SPAN, 1)
    with pytest.raises(ValueError):
        bending_only_frequency(EI, M5_MU, bad, 1)


@pytest.mark.parametrize("bad", [0, -1, -5])
def test_bending_only_rejects_invalid_mode_number(bad):
    with pytest.raises(ValueError):
        bending_only_frequency(EI, M5_MU, SPAN, bad)


@pytest.mark.parametrize("bad", [1.5, "1", None, True])
def test_bending_only_rejects_non_integer_mode_number(bad):
    with pytest.raises(TypeError):
        bending_only_frequency(EI, M5_MU, SPAN, bad)


def test_frequency_is_positive_for_a_real_panel(m2_geometry, m2_face, core):
    panel = SandwichPanel(geometry=m2_geometry, face=m2_face, core=core)
    mu = distributed_mass(panel.areal_mass, m2_geometry.width)
    assert bending_only_frequency(panel.flexural_rigidity, mu, m2_geometry.span, 1) > 0.0
    assert isinstance(m2_face, FaceMaterial)
    assert isinstance(m2_geometry, SandwichGeometry)
