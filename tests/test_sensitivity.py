"""K, V, W, X, Y - sensitivity sweeps and core-shear behaviour."""

from __future__ import annotations

import pytest

from sandwich_panel import core_depth_sweep, core_shear_modulus_sweep, face_thickness_sweep

from .conftest import P

CORE_DEPTHS = [0.005, 0.010, 0.015, 0.020, 0.025]
FACE_THICKNESSES = [0.0002, 0.0003, 0.0004, 0.0005, 0.0006]
SHEAR_MODULI = [10.0e6, 20.0e6, 40.0e6, 80.0e6, 160.0e6]


def test_core_depth_sweep_shape_and_baseline(panel):
    rows = core_depth_sweep(panel, CORE_DEPTHS, P)
    assert len(rows) == len(CORE_DEPTHS)
    assert rows[0].flexural_rigidity_ratio == pytest.approx(1.0, rel=1e-15)
    assert rows[0].areal_mass_ratio == pytest.approx(1.0, rel=1e-15)


def test_core_depth_increases_stiffness_far_faster_than_mass(panel):
    # K. The central Milestone 1 result.
    rows = core_depth_sweep(panel, CORE_DEPTHS, P)
    assert all(b.flexural_rigidity > a.flexural_rigidity for a, b in zip(rows, rows[1:]))
    assert all(b.areal_mass > a.areal_mass for a, b in zip(rows, rows[1:]))
    assert all(b.total_deflection < a.total_deflection for a, b in zip(rows, rows[1:]))
    last = rows[-1]
    assert last.flexural_rigidity_ratio > 10.0 * last.areal_mass_ratio


def test_core_depth_total_thickness_hand_calc(panel):
    rows = core_depth_sweep(panel, [0.020], P)
    # h = 2 * 0.0005 + 0.020 = 0.021 m
    assert rows[0].total_thickness == pytest.approx(0.021, abs=1e-15)


def test_core_depth_sweep_rejects_empty_input(panel):
    with pytest.raises(ValueError):
        core_depth_sweep(panel, [], P)


def test_face_thickness_sweep_trends(panel):
    rows = face_thickness_sweep(panel, FACE_THICKNESSES, P)
    assert len(rows) == len(FACE_THICKNESSES)
    assert all(b.flexural_rigidity > a.flexural_rigidity for a, b in zip(rows, rows[1:]))
    assert all(b.areal_mass > a.areal_mass for a, b in zip(rows, rows[1:]))
    assert all(b.max_face_stress < a.max_face_stress for a, b in zip(rows, rows[1:]))
    assert all(b.total_deflection < a.total_deflection for a, b in zip(rows, rows[1:]))


def test_face_thickness_sweep_areal_mass_hand_calc(panel):
    rows = face_thickness_sweep(panel, [0.0006], P)
    # m_A = 2 * 2700 * 0.0006 + 48 * 0.015 = 3.24 + 0.72 = 3.96 kg/m^2
    assert rows[0].areal_mass == pytest.approx(3.96, rel=1e-12)


def test_face_thickness_sweep_rejects_empty_input(panel):
    with pytest.raises(ValueError):
        face_thickness_sweep(panel, [], P)


def test_bending_deflection_is_invariant_with_core_shear_modulus(panel):
    # V.
    rows = core_shear_modulus_sweep(panel, SHEAR_MODULI, P)
    reference = rows[0].bending_deflection
    for row in rows:
        assert row.bending_deflection == reference  # bit-for-bit, not merely close


def test_shear_deflection_scales_as_inverse_core_shear_modulus(panel):
    # W.
    rows = core_shear_modulus_sweep(panel, SHEAR_MODULI, P)
    for a, b in zip(rows, rows[1:]):
        factor = b.core_shear_modulus / a.core_shear_modulus
        assert b.shear_deflection == pytest.approx(a.shear_deflection / factor, rel=1e-12)


def test_total_deflection_decreases_with_increasing_core_shear_modulus(panel):
    # X.
    rows = core_shear_modulus_sweep(panel, SHEAR_MODULI, P)
    assert all(b.total_deflection < a.total_deflection for a, b in zip(rows, rows[1:]))


def test_shear_fraction_bounded_and_decreasing(panel):
    # Y.
    rows = core_shear_modulus_sweep(panel, SHEAR_MODULI, P)
    for row in rows:
        assert 0.0 < row.shear_deflection_fraction < 1.0
    assert all(
        b.shear_deflection_fraction < a.shear_deflection_fraction for a, b in zip(rows, rows[1:])
    )


def test_a_very_soft_core_makes_the_panel_shear_dominated(panel):
    # A bending-stiff sandwich can still be core-shear-critical.
    soft = panel.with_core_shear_modulus(2.0e5).central_point_load(P)
    assert soft.shear_deflection_fraction > 0.5
    stiff = panel.with_core_shear_modulus(2.0e9).central_point_load(P)
    assert stiff.shear_deflection_fraction < 0.01


def test_core_shear_sweep_rejects_empty_input(panel):
    with pytest.raises(ValueError):
        core_shear_modulus_sweep(panel, [], P)


def test_with_core_shear_modulus_preserves_density_and_geometry(panel):
    variant = panel.with_core_shear_modulus(1.0e8)
    assert variant.core.density == panel.core.density
    assert variant.geometry == panel.geometry
    assert variant.core.shear_modulus == 1.0e8
    assert panel.core.shear_modulus != 1.0e8  # original untouched
