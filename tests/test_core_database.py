"""G-K: candidate core database integrity."""

from __future__ import annotations

import math

import pytest

from sandwich_panel import (
    CANDIDATE_CORES,
    ILLUSTRATIVE_DATA_NOTE,
    OrthotropicCoreMaterial,
    core_names,
    get_core,
)


def test_database_has_a_useful_number_of_candidates():
    assert 4 <= len(CANDIDATE_CORES) <= 6


def test_candidate_names_are_unique():
    # G.
    names = core_names()
    assert len(names) == len(set(names))
    assert len(names) == len(CANDIDATE_CORES)


def test_no_duplicate_candidate_objects():
    # J. No two entries share identical property sets either.
    signatures = {
        (c.name, c.density, c.shear_modulus_L, c.shear_modulus_W) for c in CANDIDATE_CORES
    }
    assert len(signatures) == len(CANDIDATE_CORES)
    assert len({id(c) for c in CANDIDATE_CORES}) == len(CANDIDATE_CORES)


def test_all_candidate_properties_positive_and_finite():
    # H.
    for core in CANDIDATE_CORES:
        assert isinstance(core, OrthotropicCoreMaterial)
        for value in (core.density, core.shear_modulus_L, core.shear_modulus_W):
            assert value > 0.0
            assert math.isfinite(value)


def test_database_order_is_deterministic():
    # I.
    first = core_names()
    for _ in range(5):
        assert core_names() == first
    assert isinstance(CANDIDATE_CORES, tuple)  # immutable, so order cannot drift


def test_database_is_ordered_by_ascending_density():
    densities = [c.density for c in CANDIDATE_CORES]
    assert densities == sorted(densities)


def test_every_candidate_carries_provenance_metadata():
    # K. An unlabelled number must never be able to pass for datasheet data.
    for core in CANDIDATE_CORES:
        assert core.source_note == ILLUSTRATIVE_DATA_NOTE
        assert "ILLUSTRATIVE" in core.source_note
        assert "not a manufacturer datasheet value" in core.source_note
        assert core.family is not None and core.family.strip()
        assert core.notes is not None and core.notes.strip()


def test_provenance_note_disclaims_allowables_and_qualification():
    note = ILLUSTRATIVE_DATA_NOTE.lower()
    assert "not a design allowable" in note
    assert "not qualification data" in note


def test_every_candidate_is_stiffer_in_L_than_in_W():
    # Physically required for honeycomb: the ribbon direction is the stiff one.
    for core in CANDIDATE_CORES:
        assert core.shear_modulus_L > core.shear_modulus_W
        assert core.directional_shear_ratio > 1.0


def test_anisotropy_ratios_are_in_a_plausible_band():
    for core in CANDIDATE_CORES:
        assert 1.5 <= core.directional_shear_ratio <= 3.5


def test_database_spans_a_useful_density_and_stiffness_range():
    densities = [c.density for c in CANDIDATE_CORES]
    moduli = [c.shear_modulus_L for c in CANDIDATE_CORES]
    assert max(densities) / min(densities) >= 2.0
    assert max(moduli) / min(moduli) >= 3.0


def test_database_contains_more_than_one_family():
    # A single monotonic family would leave the G/rho indicator nothing to say.
    assert len({c.family for c in CANDIDATE_CORES}) >= 2


def test_get_core_by_name():
    for name in core_names():
        assert get_core(name).name == name


def test_get_core_rejects_unknown_name():
    with pytest.raises(KeyError):
        get_core("NO-SUCH-CORE")


def test_get_core_is_exact_match_only():
    with pytest.raises(KeyError):
        get_core("hc-al-30")
