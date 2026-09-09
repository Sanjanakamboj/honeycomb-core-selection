"""O-U, Z, AA - central point load response, verified by independent hand calculation."""

from __future__ import annotations

import math

import pytest

from sandwich_panel import central_point_load_response

from .conftest import P

# Independent hand arithmetic for the reference case
# (b = 0.40, t_f = 0.5 mm, t_c = 15 mm, L = 1.2 m, E_f = 70 GPa, G_c = 50 MPa, P = 100 N):
#
#   h        = 0.016 m,          z_f = 0.00775 m
#   I_total  = 2.4033333333e-8 m^4
#   EI       = 1682.3333333 N m^2
#   A_s      = 0.4 * 0.015 = 0.006 m^2
#
#   M_max    = 100 * 1.2 / 4                       = 30 N m
#   V_max    = 100 / 2                             = 50 N
#   delta_b  = 100 * 1.2^3 / (48 * 1682.3333333)   = 2.1398851e-3 m
#   delta_s  = 100 * 1.2 / (4 * 1 * 50e6 * 0.006)  = 1.0e-4 m
#   sigma_f  = 30 * 0.008 / 2.4033333333e-8        = 9.9861304e6 Pa
#   tau_c    = 50 / 0.006                          = 8333.3333 Pa
EI = 70.0e9 * 2 * (0.40 * 0.0005**3 / 12 + (0.40 * 0.0005) * 0.00775**2)
DELTA_B = 100.0 * 1.2**3 / (48.0 * EI)
DELTA_S = 100.0 * 1.2 / (4.0 * 1.0 * 50.0e6 * 0.006)


def test_max_bending_moment_hand_calc(panel):
    # O. M_max = P L / 4 = 100 * 1.2 / 4 = 30 N m
    assert panel.central_point_load(P).max_bending_moment == pytest.approx(30.0, rel=1e-12)


def test_max_shear_force_hand_calc(panel):
    # P. V_max = P / 2 = 50 N
    assert panel.central_point_load(P).max_shear_force == pytest.approx(50.0, rel=1e-12)


def test_bending_deflection_hand_calc(panel):
    # Q.
    res = panel.central_point_load(P)
    assert res.bending_deflection == pytest.approx(DELTA_B, rel=1e-12)
    assert res.bending_deflection == pytest.approx(2.1398851e-3, rel=1e-6)


def test_shear_deflection_hand_calc(panel):
    # R. delta_s = P L / (4 kappa G_c b t_c) = 120 / 1.2e6 = 1.0e-4 m
    res = panel.central_point_load(P)
    assert res.shear_deflection == pytest.approx(DELTA_S, rel=1e-12)
    assert res.shear_deflection == pytest.approx(1.0e-4, rel=1e-12)


def test_total_deflection_identity(panel):
    # S.
    res = panel.central_point_load(P)
    assert res.total_deflection == pytest.approx(
        res.bending_deflection + res.shear_deflection, rel=1e-15
    )
    assert res.total_deflection == pytest.approx(DELTA_B + DELTA_S, rel=1e-12)


def test_max_face_stress_hand_calc(panel):
    # T. sigma = M_max (h/2) / I_faces_total
    res = panel.central_point_load(P)
    expected = 30.0 * 0.008 / (2 * (0.40 * 0.0005**3 / 12 + (0.40 * 0.0005) * 0.00775**2))
    assert res.max_face_stress == pytest.approx(expected, rel=1e-12)
    assert res.max_face_stress == pytest.approx(9.9861304e6, rel=1e-6)


def test_avg_core_shear_stress_hand_calc(panel):
    # U. tau = V / (b t_c) = 50 / 0.006
    res = panel.central_point_load(P)
    assert res.avg_core_shear_stress == pytest.approx(50.0 / 0.006, rel=1e-12)
    assert res.avg_core_shear_stress == pytest.approx(8333.333333, rel=1e-9)


def test_response_scales_linearly_with_load(panel):
    one = panel.central_point_load(P)
    two = panel.central_point_load(2 * P)
    assert two.max_bending_moment == pytest.approx(2 * one.max_bending_moment, rel=1e-12)
    assert two.max_shear_force == pytest.approx(2 * one.max_shear_force, rel=1e-12)
    assert two.total_deflection == pytest.approx(2 * one.total_deflection, rel=1e-12)
    assert two.max_face_stress == pytest.approx(2 * one.max_face_stress, rel=1e-12)
    assert two.avg_core_shear_stress == pytest.approx(2 * one.avg_core_shear_stress, rel=1e-12)


def test_shear_deflection_fraction_bounded(panel):
    # Y.
    res = panel.central_point_load(P)
    assert 0.0 < res.shear_deflection_fraction < 1.0
    assert res.shear_deflection_fraction == pytest.approx(
        res.shear_deflection / res.total_deflection, rel=1e-15
    )


@pytest.mark.parametrize("bad", [0.0, -100.0, math.nan, math.inf, -math.inf])
def test_invalid_load_rejected(panel, bad):
    # Z.
    with pytest.raises(ValueError):
        panel.central_point_load(bad)


@pytest.mark.parametrize("bad", [0.0, -1.0, math.nan, math.inf])
def test_invalid_kappa_rejected(panel, bad):
    # AA.
    with pytest.raises(ValueError):
        panel.central_point_load(P, shear_correction_factor=bad)


def test_kappa_defaults_to_one_and_is_reported(panel):
    res = panel.central_point_load(P)
    assert res.shear_correction_factor == 1.0


def test_kappa_scales_shear_deflection_only(panel):
    base = panel.central_point_load(P)
    halved = panel.central_point_load(P, shear_correction_factor=0.5)
    assert halved.bending_deflection == pytest.approx(base.bending_deflection, rel=1e-15)
    assert halved.shear_deflection == pytest.approx(2 * base.shear_deflection, rel=1e-12)


@pytest.mark.parametrize(
    "field",
    [
        "load",
        "span",
        "flexural_rigidity",
        "second_moment_for_stress",
        "outer_fibre_distance",
        "core_shear_modulus",
        "core_shear_area",
        "shear_correction_factor",
    ],
)
def test_low_level_response_validates_every_input(field):
    kwargs = dict(
        load=100.0,
        span=1.2,
        flexural_rigidity=1682.3333333,
        second_moment_for_stress=2.4033333333e-8,
        outer_fibre_distance=0.008,
        core_shear_modulus=50.0e6,
        core_shear_area=0.006,
        shear_correction_factor=1.0,
    )
    kwargs[field] = -1.0
    with pytest.raises(ValueError):
        central_point_load_response(**kwargs)


def test_deflection_result_is_immutable(panel):
    res = panel.central_point_load(P)
    with pytest.raises(Exception):
        res.load = 1.0  # type: ignore[misc]
