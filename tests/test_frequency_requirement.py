"""T-Z: the illustrative minimum-frequency requirement."""

from __future__ import annotations

import math

import pytest

from sandwich_panel import FrequencyRequirement


# -- T. validation ----------------------------------------------------------


@pytest.mark.parametrize("bad", [0.0, -1.0, -25.0, math.nan, math.inf, -math.inf])
def test_requirement_rejects_bad_frequency(bad):
    with pytest.raises(ValueError):
        FrequencyRequirement(minimum_frequency_hz=bad)


@pytest.mark.parametrize("bad", [0, -1, -3])
def test_requirement_rejects_invalid_mode_number(bad):
    # Z.
    with pytest.raises(ValueError):
        FrequencyRequirement(minimum_frequency_hz=25.0, mode_number=bad)


@pytest.mark.parametrize("bad", [1.5, "1", None, True])
def test_requirement_rejects_non_integer_mode_number(bad):
    with pytest.raises(TypeError):
        FrequencyRequirement(minimum_frequency_hz=25.0, mode_number=bad)


def test_requirement_defaults_to_first_mode():
    assert FrequencyRequirement(minimum_frequency_hz=25.0).mode_number == 1


def test_requirement_is_immutable(frequency_requirement):
    with pytest.raises(Exception):
        frequency_requirement.minimum_frequency_hz = 1.0  # type: ignore[misc]


def test_requirement_label_is_carried_through():
    req = FrequencyRequirement(minimum_frequency_hz=25.0)
    assert "illustrative" in req.label
    assert "minimum fundamental-frequency" in req.label


@pytest.mark.parametrize("bad", [0.0, -1.0, math.nan, math.inf])
def test_requirement_rejects_invalid_assessed_frequency(frequency_requirement, bad):
    with pytest.raises(ValueError):
        frequency_requirement.assess(bad)


# -- U. PASS case -----------------------------------------------------------


def test_requirement_pass_case(frequency_requirement):
    a = frequency_requirement.assess(31.1)
    assert a.feasible is True
    assert a.margin_hz > 0.0
    assert a.normalised_margin > 0.0
    assert a.mode_number == 1
    assert str(a) == "PASS"


# -- V. exact-boundary PASS -------------------------------------------------


def test_requirement_exact_boundary_passes():
    # The convention is `actual >= required`, so equality PASSES.
    limit = 25.0
    a = FrequencyRequirement(minimum_frequency_hz=limit).assess(limit)
    assert a.feasible is True
    assert a.margin_hz == pytest.approx(0.0, abs=1e-15)
    assert a.normalised_margin == pytest.approx(0.0, abs=1e-15)


def test_just_below_the_boundary_fails():
    limit = 25.0
    assert FrequencyRequirement(minimum_frequency_hz=limit).assess(0.999 * limit).feasible is False
    assert FrequencyRequirement(minimum_frequency_hz=limit).assess(1.001 * limit).feasible is True


# -- W. FAIL case -----------------------------------------------------------


def test_requirement_fail_case(frequency_requirement):
    a = frequency_requirement.assess(20.0)
    assert a.feasible is False
    assert a.margin_hz == pytest.approx(-5.0, rel=1e-12)
    assert a.normalised_margin == pytest.approx(20.0 / 25.0 - 1.0, rel=1e-12)
    assert str(a) == "FAIL"


# -- X / Y. margin identities ------------------------------------------------


def test_margin_identity(frequency_requirement):
    for actual in (10.0, 25.0, 27.5, 31.1, 100.0):
        a = frequency_requirement.assess(actual)
        assert a.margin_hz == pytest.approx(actual - 25.0, rel=1e-12, abs=1e-15)
        assert a.frequency == actual
        assert a.required_frequency == 25.0


def test_normalised_margin_identity(frequency_requirement):
    for actual in (10.0, 25.0, 27.5, 31.1, 100.0):
        a = frequency_requirement.assess(actual)
        assert a.normalised_margin == pytest.approx(actual / 25.0 - 1.0, rel=1e-12, abs=1e-15)


def test_margin_and_normalised_margin_agree_on_sign(frequency_requirement):
    for actual in (5.0, 24.999, 25.0, 25.001, 60.0):
        a = frequency_requirement.assess(actual)
        assert (a.margin_hz >= 0.0) == (a.normalised_margin >= 0.0) == a.feasible


def test_assessment_is_immutable(frequency_requirement):
    a = frequency_requirement.assess(30.0)
    with pytest.raises(Exception):
        a.margin_hz = 1.0  # type: ignore[misc]


def test_requirement_can_target_a_higher_mode():
    req = FrequencyRequirement(minimum_frequency_hz=100.0, mode_number=2)
    assert req.mode_number == 2
    assert req.assess(120.0).mode_number == 2
    assert req.assess(120.0).feasible is True
