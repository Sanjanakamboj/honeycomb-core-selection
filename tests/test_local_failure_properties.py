"""A-E: core compression property validation and database integrity."""

from __future__ import annotations

import math

import pytest

from sandwich_panel import (
    CANDIDATE_CORES,
    CANDIDATE_CORE_COMPRESSION,
    ILLUSTRATIVE_LOCAL_NOTE,
    CoreCompressionProperties,
    core_compression_names,
    core_names,
    get_core,
    get_core_compression,
)


# -- A. validation ---------------------------------------------------------


def test_compression_properties_store_values(core_compression):
    assert core_compression.name == "TEST-CORE"
    assert core_compression.compression_strength == 2.0e6
    assert core_compression.compression_modulus == 500.0e6
    assert core_compression.source_note is not None


@pytest.mark.parametrize("field", ["compression_strength", "compression_modulus"])
@pytest.mark.parametrize("bad", [0.0, -1.0, -2.0e6, math.nan, math.inf, -math.inf])
def test_compression_properties_reject_bad_values(field, bad):
    kwargs = {"name": "x", "compression_strength": 2.0e6, "compression_modulus": 500.0e6}
    kwargs[field] = bad
    with pytest.raises(ValueError):
        CoreCompressionProperties(**kwargs)


@pytest.mark.parametrize("bad_name", ["", "   "])
def test_compression_properties_reject_empty_name(bad_name):
    with pytest.raises(ValueError):
        CoreCompressionProperties(
            name=bad_name, compression_strength=2.0e6, compression_modulus=500.0e6
        )


def test_compression_properties_are_immutable(core_compression):
    with pytest.raises(Exception):
        core_compression.compression_strength = 1.0  # type: ignore[misc]


def test_compression_is_not_confused_with_L_W_shear_directions(core_compression):
    # Through-thickness compression is a separate property axis; it must not
    # expose or accept an L/W direction.
    for banned in ("compression_strength_L", "compression_strength_W", "shear_strength"):
        assert not hasattr(core_compression, banned)
    assert not hasattr(core_compression, "compression_strength_direction")


# -- B / C. database determinism and one-to-one alignment ------------------


def test_every_candidate_has_exactly_one_compression_record():
    # C.
    assert core_compression_names() == core_names()
    for core in CANDIDATE_CORES:
        assert get_core_compression(core.name).name == core.name


def test_no_extra_compression_only_record_exists():
    assert set(core_compression_names()) == set(core_names())
    assert len(CANDIDATE_CORE_COMPRESSION) == len(CANDIDATE_CORES)


def test_compression_database_order_is_deterministic_and_matches():
    # B.
    first = core_compression_names()
    for _ in range(5):
        assert core_compression_names() == first
    assert isinstance(CANDIDATE_CORE_COMPRESSION, tuple)
    assert list(core_compression_names()) == [c.name for c in CANDIDATE_CORES]


def test_compression_record_names_are_unique():
    names = core_compression_names()
    assert len(names) == len(set(names))


def test_no_duplicate_compression_records():
    signatures = {
        (c.name, c.compression_strength, c.compression_modulus)
        for c in CANDIDATE_CORE_COMPRESSION
    }
    assert len(signatures) == len(CANDIDATE_CORE_COMPRESSION)


# -- D. all values positive and finite -------------------------------------


def test_all_compression_values_positive_and_finite():
    for c in CANDIDATE_CORE_COMPRESSION:
        for value in (c.compression_strength, c.compression_modulus):
            assert value > 0.0
            assert math.isfinite(value)


# -- E. provenance ---------------------------------------------------------


def test_every_compression_record_carries_provenance():
    for c in CANDIDATE_CORE_COMPRESSION:
        assert c.source_note == ILLUSTRATIVE_LOCAL_NOTE
        assert "ILLUSTRATIVE LOCAL-FAILURE INPUT" in c.source_note
        assert "NOT MANUFACTURER ALLOWABLE" in c.source_note
        assert c.notes is not None and c.notes.strip()


def test_provenance_note_disclaims_allowables_and_qualification():
    note = ILLUSTRATIVE_LOCAL_NOTE.lower()
    assert "not a design allowable" in note
    assert "not qualification data" in note


# -- physical trends -------------------------------------------------------


def test_compression_strength_and_modulus_rise_with_density_within_the_aluminium_family():
    aluminium = [c for c in CANDIDATE_CORES if c.family == "aluminium-honeycomb-equivalent"]
    pairs = sorted(
        (c.density, get_core_compression(c.name)) for c in aluminium
    )
    strengths = [r.compression_strength for _, r in pairs]
    moduli = [r.compression_modulus for _, r in pairs]
    assert strengths == sorted(strengths)
    assert moduli == sorted(moduli)


def test_the_aramid_candidate_has_a_much_lower_compression_modulus_than_its_density_peer():
    # The trend that drives the wrinkling result: aramid paper is far less stiff
    # than aluminium foil, even at comparable density.
    aramid = get_core_compression("HC-AR-48")
    aluminium = get_core_compression("HC-AL-45")
    assert get_core("HC-AR-48").density > get_core("HC-AL-45").density
    assert aramid.compression_modulus < 0.25 * aluminium.compression_modulus


def test_the_aramid_candidate_is_not_correspondingly_weak_in_crushing():
    # Low modulus does NOT imply low strength - that separation is the point.
    aramid = get_core_compression("HC-AR-48")
    lightest = get_core_compression("HC-AL-30")
    assert aramid.compression_strength > lightest.compression_strength


def test_compression_database_spans_a_useful_range():
    strengths = [c.compression_strength for c in CANDIDATE_CORE_COMPRESSION]
    moduli = [c.compression_modulus for c in CANDIDATE_CORE_COMPRESSION]
    assert max(strengths) / min(strengths) >= 4.0
    assert max(moduli) / min(moduli) >= 10.0


def test_get_core_compression_rejects_unknown_name():
    with pytest.raises(KeyError):
        get_core_compression("NO-SUCH-CORE")


def test_get_core_compression_is_exact_match_only():
    with pytest.raises(KeyError):
        get_core_compression("hc-al-30")
