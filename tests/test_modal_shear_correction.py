"""I-S: the shear-flexibility correction, its limits, directionality and determinism."""

from __future__ import annotations

import math

import pytest

from sandwich_panel import (
    CANDIDATE_CORES,
    CoreShearDirection,
    assess_core_modal,
    bending_only_frequency,
    modal_frequency,
    shear_corrected_frequency,
)

from .conftest import M5_F1_BENDING, M5_F1_L, M5_F1_W, M5_MU, M5_SHEAR_AREA

EI = 2913.4933333333
SPAN = 1.5
G_L = 50.0e6
G_W = 20.0e6


# -- I. dimensional / hand-calculation check --------------------------------


def test_shear_corrected_hand_calc():
    """Independent arithmetic, written out rather than calling the helper twice.

    k     = pi / 1.5
    ratio = EI k^2 / (kappa G A_s)
    omega^2 = EI k^4 / (mu (1 + ratio))
    """
    k = math.pi / SPAN
    ratio = EI * k**2 / (1.0 * G_L * M5_SHEAR_AREA)
    omega = math.sqrt(EI * k**4 / (M5_MU * (1.0 + ratio)))
    expected = omega / (2.0 * math.pi)
    assert shear_corrected_frequency(EI, M5_MU, SPAN, G_L, M5_SHEAR_AREA) == pytest.approx(
        expected, rel=1e-12
    )
    assert ratio == pytest.approx(0.0255600237, rel=1e-8)
    assert expected == pytest.approx(M5_F1_L, rel=1e-9)


def test_correction_term_equals_the_static_shear_to_bending_compliance_ratio():
    """The correction term is not an arbitrary import.

    For a static sinusoidal load q0 sin(kx):
        w_bending = q0 / (EI k^4)
        w_shear   = q0 / (kappa G A_s k^2)
    so w_shear / w_bending = EI k^2 / (kappa G A_s) - exactly the correction term.
    """
    k = math.pi / SPAN
    q0 = 123.0
    w_bending = q0 / (EI * k**4)
    w_shear = q0 / (1.0 * G_L * M5_SHEAR_AREA * k**2)
    r = modal_frequency(EI, M5_MU, SPAN, G_L, M5_SHEAR_AREA)
    assert r.shear_flexibility_ratio == pytest.approx(w_shear / w_bending, rel=1e-12)


def test_result_reports_consistent_penalty_fields():
    r = modal_frequency(EI, M5_MU, SPAN, G_L, M5_SHEAR_AREA)
    assert r.bending_only_frequency == pytest.approx(M5_F1_BENDING, rel=1e-9)
    assert r.shear_corrected_frequency == pytest.approx(M5_F1_L, rel=1e-9)
    assert r.shear_frequency_penalty_hz == pytest.approx(
        r.bending_only_frequency - r.shear_corrected_frequency, rel=1e-15
    )
    assert r.shear_frequency_penalty_fraction == pytest.approx(
        r.shear_frequency_penalty_hz / r.bending_only_frequency, rel=1e-15
    )
    assert r.angular_frequency == pytest.approx(
        2 * math.pi * r.shear_corrected_frequency, rel=1e-15
    )


def test_corrected_frequency_equals_bending_over_sqrt_one_plus_ratio():
    r = modal_frequency(EI, M5_MU, SPAN, G_L, M5_SHEAR_AREA)
    assert r.shear_corrected_frequency == pytest.approx(
        r.bending_only_frequency / math.sqrt(1.0 + r.shear_flexibility_ratio), rel=1e-12
    )


# -- J. corrected <= bending-only -------------------------------------------


def test_corrected_frequency_never_exceeds_the_bending_only_frequency():
    for g in (1.0e5, 1.0e6, 1.0e7, 5.0e7, 1.0e9, 1.0e12):
        r = modal_frequency(EI, M5_MU, SPAN, g, M5_SHEAR_AREA)
        assert r.shear_corrected_frequency <= r.bending_only_frequency
        assert r.shear_frequency_penalty_hz >= 0.0
        assert 0.0 <= r.shear_frequency_penalty_fraction < 1.0


# -- K / M. G raises frequency, lower G lowers it ---------------------------


def test_frequency_rises_monotonically_with_shear_modulus():
    values = [
        shear_corrected_frequency(EI, M5_MU, SPAN, g, M5_SHEAR_AREA)
        for g in (5e6, 10e6, 20e6, 40e6, 80e6, 160e6, 500e6)
    ]
    assert all(b > a for a, b in zip(values, values[1:]))


def test_lower_shear_modulus_lowers_the_frequency():
    high = shear_corrected_frequency(EI, M5_MU, SPAN, 100e6, M5_SHEAR_AREA)
    low = shear_corrected_frequency(EI, M5_MU, SPAN, 1e6, M5_SHEAR_AREA)
    assert low < high


# -- L. high-G limit --------------------------------------------------------


def test_high_shear_modulus_approaches_the_bending_only_limit():
    reference = bending_only_frequency(EI, M5_MU, SPAN, 1)
    for g, tol in ((1e9, 1e-3), (1e12, 1e-6), (1e15, 1e-9)):
        assert shear_corrected_frequency(EI, M5_MU, SPAN, g, M5_SHEAR_AREA) == pytest.approx(
            reference, rel=tol
        )
    # ...and always from BELOW.
    assert shear_corrected_frequency(EI, M5_MU, SPAN, 1e15, M5_SHEAR_AREA) <= reference


def test_vanishing_shear_modulus_drives_the_frequency_to_zero():
    values = [shear_corrected_frequency(EI, M5_MU, SPAN, g, M5_SHEAR_AREA) for g in (1e5, 1e3, 1e1)]
    assert all(b < a for a, b in zip(values, values[1:]))
    assert values[-1] < 0.1 * values[0]
    assert values[-1] > 0.0


def test_vanishing_EI_drives_the_frequency_to_zero():
    values = [shear_corrected_frequency(ei, M5_MU, SPAN, G_L, M5_SHEAR_AREA)
              for ei in (EI, EI * 1e-4, EI * 1e-8)]
    assert all(b < a for a, b in zip(values, values[1:]))
    assert values[-1] > 0.0


# -- P. mass affects both frequencies consistently --------------------------


def test_increasing_mass_lowers_both_frequencies_by_the_same_factor():
    a = modal_frequency(EI, M5_MU, SPAN, G_L, M5_SHEAR_AREA)
    b = modal_frequency(EI, 4 * M5_MU, SPAN, G_L, M5_SHEAR_AREA)
    assert b.bending_only_frequency == pytest.approx(a.bending_only_frequency / 2, rel=1e-12)
    assert b.shear_corrected_frequency == pytest.approx(a.shear_corrected_frequency / 2, rel=1e-12)
    # mu does not enter the correction term at all
    assert b.shear_flexibility_ratio == pytest.approx(a.shear_flexibility_ratio, rel=1e-15)
    assert b.shear_frequency_penalty_fraction == pytest.approx(
        a.shear_frequency_penalty_fraction, rel=1e-12
    )


# -- N / O. directional behaviour -------------------------------------------


def test_L_frequency_is_at_least_W_frequency(basis, ortho_core, frequency_requirement):
    al = assess_core_modal(basis, ortho_core, "L", frequency_requirement)
    aw = assess_core_modal(basis, ortho_core, "W", frequency_requirement)
    assert al.frequency > aw.frequency
    assert al.frequency == pytest.approx(M5_F1_L, rel=1e-9)
    assert aw.frequency == pytest.approx(M5_F1_W, rel=1e-9)


def test_bending_only_frequency_is_identical_between_L_and_W(basis, ortho_core, frequency_requirement):
    # O. EI and mass do not depend on shear direction, so ONLY the correction differs.
    al = assess_core_modal(basis, ortho_core, "L", frequency_requirement)
    aw = assess_core_modal(basis, ortho_core, "W", frequency_requirement)
    assert al.bending_only_frequency == aw.bending_only_frequency  # bit-for-bit
    assert al.distributed_mass == aw.distributed_mass
    assert al.modal.flexural_rigidity == aw.modal.flexural_rigidity
    assert al.effective_shear_modulus != aw.effective_shear_modulus


def test_directional_ordering_holds_for_every_candidate(basis, frequency_requirement):
    for core in CANDIDATE_CORES:
        al = assess_core_modal(basis, core, "L", frequency_requirement)
        aw = assess_core_modal(basis, core, "W", frequency_requirement)
        assert core.shear_modulus_L > core.shear_modulus_W
        assert al.frequency > aw.frequency
        assert al.bending_only_frequency == aw.bending_only_frequency


def test_directional_penalty_is_not_a_simple_shear_ratio(basis, frequency_requirement):
    """Unlike the static shear deflection, no clean ratio identity is expected."""
    core = CANDIDATE_CORES[0]
    al = assess_core_modal(basis, core, "L", frequency_requirement)
    aw = assess_core_modal(basis, core, "W", frequency_requirement)
    shear_ratio = core.shear_modulus_L / core.shear_modulus_W
    assert al.frequency / aw.frequency != pytest.approx(shear_ratio, rel=1e-3)
    assert 1.0 < al.frequency / aw.frequency < shear_ratio


# -- Q / R. positive, sorted multi-mode frequencies -------------------------


def test_all_frequencies_are_positive(basis, frequency_requirement):
    for core in CANDIDATE_CORES:
        for direction in ("L", "W"):
            for n in (1, 2, 3):
                a = assess_core_modal(basis, core, direction, frequency_requirement, mode_number=n)
                assert a.frequency > 0.0
                assert a.bending_only_frequency > 0.0


def test_multi_mode_frequencies_are_sorted_increasing(basis, ortho_core, frequency_requirement):
    values = [
        assess_core_modal(basis, ortho_core, "L", frequency_requirement, mode_number=n).frequency
        for n in (1, 2, 3, 4)
    ]
    assert all(b > a for a, b in zip(values, values[1:]))


def test_shear_penalty_grows_with_mode_number(basis, ortho_core, frequency_requirement):
    # The correction term goes as k^2, hence as n^2, so higher modes are penalised more.
    penalties = [
        assess_core_modal(
            basis, ortho_core, "L", frequency_requirement, mode_number=n
        ).modal.shear_frequency_penalty_fraction
        for n in (1, 2, 3, 4)
    ]
    assert all(b > a for a, b in zip(penalties, penalties[1:]))


def test_shear_corrected_modes_fall_short_of_exact_n_squared(basis, ortho_core, frequency_requirement):
    first = assess_core_modal(basis, ortho_core, "L", frequency_requirement, mode_number=1)
    third = assess_core_modal(basis, ortho_core, "L", frequency_requirement, mode_number=3)
    # Bending-only would give exactly 9x; the shear correction makes it less.
    assert third.bending_only_frequency == pytest.approx(
        9 * first.bending_only_frequency, rel=1e-12
    )
    assert third.frequency < 9 * first.frequency


# -- S. determinism ---------------------------------------------------------


def test_modal_evaluation_is_deterministic(basis, ortho_core, frequency_requirement):
    from dataclasses import asdict

    first = asdict(assess_core_modal(basis, ortho_core, "L", frequency_requirement).modal)
    for _ in range(5):
        assert asdict(assess_core_modal(basis, ortho_core, "L", frequency_requirement).modal) == first


# -- validation --------------------------------------------------------------


@pytest.mark.parametrize("bad", [0.0, -1.0, math.nan, math.inf])
def test_shear_corrected_validates_every_input(bad):
    kwargs = dict(
        flexural_rigidity=EI, distributed_mass_=M5_MU, span=SPAN,
        core_shear_modulus=G_L, core_shear_area=M5_SHEAR_AREA,
        mode_number=1, shear_correction_factor=1.0,
    )
    for field in (
        "flexural_rigidity", "distributed_mass_", "span",
        "core_shear_modulus", "core_shear_area", "shear_correction_factor",
    ):
        bad_kwargs = dict(kwargs)
        bad_kwargs[field] = bad
        with pytest.raises(ValueError):
            shear_corrected_frequency(**bad_kwargs)


def test_kappa_is_exposed_and_defaults_to_one():
    r = modal_frequency(EI, M5_MU, SPAN, G_L, M5_SHEAR_AREA)
    assert r.shear_correction_factor == 1.0
    halved = shear_corrected_frequency(
        EI, M5_MU, SPAN, G_L, M5_SHEAR_AREA, shear_correction_factor=0.5
    )
    assert halved < r.shear_corrected_frequency  # softer shear layer -> lower frequency


def test_direction_is_recorded_on_the_result():
    r = modal_frequency(
        EI, M5_MU, SPAN, G_L, M5_SHEAR_AREA, direction=CoreShearDirection.W
    )
    assert r.direction is CoreShearDirection.W
    assert modal_frequency(EI, M5_MU, SPAN, G_L, M5_SHEAR_AREA).direction is None
