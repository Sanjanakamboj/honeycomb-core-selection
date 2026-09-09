"""L, M, N - areal mass and mass decomposition."""

from __future__ import annotations

import pytest

from sandwich_panel import CoreMaterial, FaceMaterial, SandwichPanel, mass_properties


def test_areal_mass_hand_calc(panel):
    # L. m_A = 2 * 2700 * 0.0005 + 48 * 0.015 = 2.70 + 0.72 = 3.42 kg/m^2
    m = panel.mass()
    assert m.total_areal_mass == pytest.approx(3.42, rel=1e-12)
    assert panel.areal_mass == pytest.approx(3.42, rel=1e-12)


def test_mass_decomposition_hand_calc(panel):
    # M.
    m = panel.mass()
    assert m.face_areal_mass == pytest.approx(2.70, rel=1e-12)
    assert m.core_areal_mass == pytest.approx(0.72, rel=1e-12)
    assert m.face_areal_mass + m.core_areal_mass == pytest.approx(m.total_areal_mass, rel=1e-15)
    assert m.face_mass_fraction + m.core_mass_fraction == pytest.approx(1.0, rel=1e-15)
    assert m.face_mass_fraction == pytest.approx(2.70 / 3.42, rel=1e-12)


def test_total_strip_mass_hand_calc(panel):
    # plan area = 0.4 * 1.2 = 0.48 m^2 ; m = 3.42 * 0.48 = 1.6416 kg
    m = panel.mass()
    assert m.plan_area == pytest.approx(0.48, rel=1e-12)
    assert m.total_mass == pytest.approx(1.6416, rel=1e-12)
    assert m.face_mass + m.core_mass == pytest.approx(m.total_mass, rel=1e-15)


def test_face_mass_scales_linearly_with_face_thickness(panel):
    base = panel.mass().face_areal_mass
    doubled = panel.with_geometry(face_thickness=2 * panel.geometry.face_thickness)
    assert doubled.mass().face_areal_mass == pytest.approx(2 * base, rel=1e-12)
    # ...and the core contribution is untouched
    assert doubled.mass().core_areal_mass == pytest.approx(panel.mass().core_areal_mass, rel=1e-15)


def test_core_mass_scales_linearly_with_core_thickness(panel):
    base = panel.mass().core_areal_mass
    tripled = panel.with_geometry(core_thickness=3 * panel.geometry.core_thickness)
    assert tripled.mass().core_areal_mass == pytest.approx(3 * base, rel=1e-12)
    assert tripled.mass().face_areal_mass == pytest.approx(panel.mass().face_areal_mass, rel=1e-15)


def test_areal_mass_scales_exactly_with_densities(geometry, face, core):
    # N.
    base = mass_properties(geometry, face, core)
    dense_face = FaceMaterial(
        name="x2", youngs_modulus=face.youngs_modulus, density=2 * face.density
    )
    dense_core = CoreMaterial(name="x5", density=5 * core.density, shear_modulus=core.shear_modulus)
    scaled = mass_properties(geometry, dense_face, dense_core)
    assert scaled.face_areal_mass == pytest.approx(2 * base.face_areal_mass, rel=1e-12)
    assert scaled.core_areal_mass == pytest.approx(5 * base.core_areal_mass, rel=1e-12)


def test_areal_mass_is_independent_of_width_and_span(panel):
    assert panel.with_geometry(width=7 * panel.geometry.width).areal_mass == pytest.approx(
        panel.areal_mass, rel=1e-15
    )
    assert panel.with_geometry(span=7 * panel.geometry.span).areal_mass == pytest.approx(
        panel.areal_mass, rel=1e-15
    )


def test_total_mass_scales_with_plan_area(panel):
    bigger = panel.with_geometry(width=2 * panel.geometry.width, span=3 * panel.geometry.span)
    assert bigger.mass().total_mass == pytest.approx(6 * panel.mass().total_mass, rel=1e-12)


def test_core_depth_is_cheap_relative_to_stiffness(panel):
    # The core-depth leverage in mass terms: the light core adds little mass.
    deep = panel.with_geometry(core_thickness=0.025)
    mass_ratio = deep.areal_mass / panel.areal_mass
    ei_ratio = deep.flexural_rigidity / panel.flexural_rigidity
    assert mass_ratio < 1.2
    assert ei_ratio > 2.0
    assert isinstance(deep, SandwichPanel)
