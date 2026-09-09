"""F-P: local patch load, pressure scaling, compression margin and crush limit."""

from __future__ import annotations

import math

import pytest

from sandwich_panel import (
    CoreCompressionProperties,
    LocalPatchLoad,
    assess_local_failure,
    core_compression_margin,
    core_crush_force_limit,
    evaluate_candidate,
    local_patch_force_sweep,
    local_patch_size_sweep,
)


# -- F. patch validation ---------------------------------------------------


@pytest.mark.parametrize("field", ["force", "patch_width", "patch_length"])
@pytest.mark.parametrize("bad", [0.0, -1.0, math.nan, math.inf, -math.inf])
def test_patch_rejects_non_positive_or_non_finite(field, bad):
    kwargs = {"force": 100.0, "patch_width": 0.025, "patch_length": 0.025}
    kwargs[field] = bad
    with pytest.raises(ValueError):
        LocalPatchLoad(**kwargs)


def test_patch_is_immutable(patch_load):
    with pytest.raises(Exception):
        patch_load.force = 1.0  # type: ignore[misc]


def test_square_constructor_matches_explicit_dimensions():
    a = LocalPatchLoad.square(force=100.0, side=0.025)
    b = LocalPatchLoad(force=100.0, patch_width=0.025, patch_length=0.025)
    assert a == b


def test_rectangular_patch_is_supported():
    p = LocalPatchLoad(force=100.0, patch_width=0.020, patch_length=0.040)
    assert p.patch_area == pytest.approx(8.0e-4, rel=1e-15)
    assert p.pressure == pytest.approx(100.0 / 8.0e-4, rel=1e-15)


# -- G. area hand calculation ----------------------------------------------


def test_patch_area_hand_calc(patch_load):
    # 0.025 * 0.025 = 6.25e-4 m^2 = 625 mm^2
    assert patch_load.patch_area == pytest.approx(6.25e-4, rel=1e-15)


# -- H. pressure hand calculation ------------------------------------------


def test_patch_pressure_hand_calc(patch_load):
    # 100 / 6.25e-4 = 1.6e5 Pa = 160 kPa
    assert patch_load.pressure == pytest.approx(1.6e5, rel=1e-15)
    assert patch_load.pressure == pytest.approx(100.0 / 0.025**2, rel=1e-15)


# -- I. pressure scales with force -----------------------------------------


def test_pressure_is_linear_in_force(patch_load):
    for factor in (0.5, 2.0, 10.0):
        scaled = patch_load.with_force(factor * patch_load.force)
        assert scaled.pressure == pytest.approx(factor * patch_load.pressure, rel=1e-12)
        assert scaled.patch_area == patch_load.patch_area


# -- J. pressure scales inversely with area --------------------------------


def test_pressure_is_inverse_in_area():
    small = LocalPatchLoad(force=100.0, patch_width=0.02, patch_length=0.02)
    big = LocalPatchLoad(force=100.0, patch_width=0.02, patch_length=0.08)  # 4x the area
    assert big.patch_area == pytest.approx(4 * small.patch_area, rel=1e-15)
    assert big.pressure == pytest.approx(small.pressure / 4.0, rel=1e-12)


# -- K. square patch: inverse-square in side length ------------------------


def test_pressure_goes_as_inverse_side_squared(patch_load):
    for factor in (0.5, 2.0, 4.0):
        scaled = patch_load.with_square_side(factor * 0.025)
        assert scaled.pressure == pytest.approx(patch_load.pressure / factor**2, rel=1e-12)


def test_patch_size_sweep_inverse_square_scaling(core_compression, patch_load):
    sides = [0.010, 0.015, 0.020, 0.025, 0.040, 0.050]
    rows = local_patch_size_sweep(core_compression, patch_load, sides)
    assert len(rows) == len(sides)
    for row, side in zip(rows, sides):
        assert row.patch_side == side
        assert row.patch_area == pytest.approx(side**2, rel=1e-15)
        assert row.pressure == pytest.approx(100.0 / side**2, rel=1e-12)
    # 10 mm -> 1.0 MPa ; 50 mm -> 40 kPa
    assert rows[0].pressure == pytest.approx(1.0e6, rel=1e-12)
    assert rows[-1].pressure == pytest.approx(4.0e4, rel=1e-12)
    assert all(b.pressure < a.pressure for a, b in zip(rows, rows[1:]))
    assert all(b.compression_margin > a.compression_margin for a, b in zip(rows, rows[1:]))


# -- L. compression margin hand calculation --------------------------------


def test_compression_margin_hand_calc(core_compression, patch_load):
    # MS = 2.0e6 / 1.6e5 - 1 = 11.5
    ms = core_compression_margin(patch_load.pressure, core_compression.compression_strength)
    assert ms == pytest.approx(11.5, rel=1e-12)


def test_compression_margin_through_the_assessment(
    basis, ortho_core, core_compression, local_basis
):
    r = evaluate_candidate(basis, ortho_core, "L")
    a = assess_local_failure(r, basis.face.youngs_modulus, core_compression, local_basis)
    assert a.local_core_compression_stress == pytest.approx(1.6e5, rel=1e-15)
    assert a.core_compression_allowable == 2.0e6
    assert a.core_compression_margin == pytest.approx(11.5, rel=1e-12)
    assert a.core_compression_pass is True
    assert a.patch_area == pytest.approx(6.25e-4, rel=1e-15)
    assert a.local_patch_force == 100.0


def test_compression_margin_is_direction_independent(
    basis, ortho_core, core_compression, local_basis
):
    # Crushing does not involve the L/W shear moduli.
    al = assess_local_failure(
        evaluate_candidate(basis, ortho_core, "L"),
        basis.face.youngs_modulus, core_compression, local_basis,
    )
    aw = assess_local_failure(
        evaluate_candidate(basis, ortho_core, "W"),
        basis.face.youngs_modulus, core_compression, local_basis,
    )
    assert al.core_compression_margin == aw.core_compression_margin
    assert al.local_core_compression_stress == aw.local_core_compression_stress
    assert al.core_crush_force_limit == aw.core_crush_force_limit


@pytest.mark.parametrize("bad", [0.0, -1.0, math.nan, math.inf])
def test_compression_margin_validates_inputs(bad):
    with pytest.raises(ValueError):
        core_compression_margin(bad, 2.0e6)
    with pytest.raises(ValueError):
        core_compression_margin(1.6e5, bad)


# -- M. exact-boundary PASS -------------------------------------------------


def test_compression_exact_boundary_passes(basis, ortho_core, local_basis):
    boundary = CoreCompressionProperties(
        name="TEST-CORE",
        compression_strength=local_basis.patch_load.pressure,
        compression_modulus=500.0e6,
    )
    a = assess_local_failure(
        evaluate_candidate(basis, ortho_core, "L"),
        basis.face.youngs_modulus, boundary, local_basis,
    )
    assert a.core_compression_margin == pytest.approx(0.0, abs=1e-15)
    assert a.core_compression_pass is True


# -- N. fail case -----------------------------------------------------------


def test_compression_fail_case(basis, ortho_core, local_basis):
    weak = CoreCompressionProperties(
        name="TEST-CORE",
        compression_strength=0.5 * local_basis.patch_load.pressure,
        compression_modulus=500.0e6,
    )
    a = assess_local_failure(
        evaluate_candidate(basis, ortho_core, "L"),
        basis.face.youngs_modulus, weak, local_basis,
    )
    assert a.core_compression_margin == pytest.approx(-0.5, rel=1e-12)
    assert a.core_compression_pass is False
    assert a.local_failure_feasible is False


# -- O. crush-force limit hand calculation ---------------------------------


def test_crush_force_limit_hand_calc(core_compression, patch_load):
    # F_crush = 2.0e6 * 6.25e-4 = 1250 N
    assert core_crush_force_limit(
        core_compression.compression_strength, patch_load.patch_area
    ) == pytest.approx(1250.0, rel=1e-12)


def test_crush_force_limit_scales_with_area_and_strength(core_compression):
    base = core_crush_force_limit(2.0e6, 6.25e-4)
    assert core_crush_force_limit(4.0e6, 6.25e-4) == pytest.approx(2 * base, rel=1e-12)
    assert core_crush_force_limit(2.0e6, 12.5e-4) == pytest.approx(2 * base, rel=1e-12)


@pytest.mark.parametrize("bad", [0.0, -1.0, math.nan, math.inf])
def test_crush_force_limit_validates_inputs(bad):
    with pytest.raises(ValueError):
        core_crush_force_limit(bad, 6.25e-4)
    with pytest.raises(ValueError):
        core_crush_force_limit(2.0e6, bad)


# -- P. returned limit gives zero margin -----------------------------------


def test_crush_force_limit_gives_zero_margin_at_that_force(core_compression, patch_load):
    limit = core_crush_force_limit(
        core_compression.compression_strength, patch_load.patch_area
    )
    at_limit = patch_load.with_force(limit)
    ms = core_compression_margin(at_limit.pressure, core_compression.compression_strength)
    assert ms == pytest.approx(0.0, abs=1e-12)


def test_just_below_and_above_the_crush_limit(core_compression, patch_load):
    limit = core_crush_force_limit(
        core_compression.compression_strength, patch_load.patch_area
    )
    below = core_compression_margin(
        patch_load.with_force(0.999 * limit).pressure, core_compression.compression_strength
    )
    above = core_compression_margin(
        patch_load.with_force(1.001 * limit).pressure, core_compression.compression_strength
    )
    assert below > 0.0
    assert above < 0.0


# -- force sweep ------------------------------------------------------------


def test_force_sweep_is_linear_and_crosses_the_boundary(core_compression, patch_load):
    forces = [25.0, 50.0, 100.0, 200.0, 500.0, 1000.0, 2000.0]
    rows = local_patch_force_sweep(core_compression, patch_load, forces)
    assert len(rows) == len(forces)
    for row, f in zip(rows, forces):
        assert row.force == f
        assert row.pressure == pytest.approx(f / 6.25e-4, rel=1e-12)
        assert row.patch_area == pytest.approx(6.25e-4, rel=1e-15)
        assert row.crush_force_limit == pytest.approx(1250.0, rel=1e-12)
    assert all(b.pressure > a.pressure for a, b in zip(rows, rows[1:]))
    assert all(b.compression_margin < a.compression_margin for a, b in zip(rows, rows[1:]))
    # Boundary is at F = 1250 N: 1000 N passes, 2000 N fails.
    passes = [r.force for r in rows if r.compression_pass]
    fails = [r.force for r in rows if not r.compression_pass]
    assert max(passes) == 1000.0
    assert min(fails) == 2000.0


def test_sweeps_reject_empty_input(core_compression, patch_load):
    with pytest.raises(ValueError):
        local_patch_force_sweep(core_compression, patch_load, [])
    with pytest.raises(ValueError):
        local_patch_size_sweep(core_compression, patch_load, [])


def test_sweeps_do_not_mutate_the_patch(core_compression, patch_load):
    before = (patch_load.force, patch_load.patch_width, patch_load.patch_length)
    local_patch_force_sweep(core_compression, patch_load, [1.0, 2.0])
    local_patch_size_sweep(core_compression, patch_load, [0.01, 0.02])
    assert (patch_load.force, patch_load.patch_width, patch_load.patch_length) == before


def test_rectangular_patch_reports_no_square_side(core_compression):
    rect = LocalPatchLoad(force=100.0, patch_width=0.02, patch_length=0.04)
    rows = local_patch_force_sweep(core_compression, rect, [100.0])
    assert rows[0].patch_side is None
