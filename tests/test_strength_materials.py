"""A-F: strength material validation, directional retrieval, provenance."""

from __future__ import annotations

import math

import pytest

from sandwich_panel import (
    CoreShearDirection,
    FaceStrength,
    LimitingConstraint,
    OrthotropicCoreStrength,
    StrengthBasis,
)


# -- A. FaceStrength validation -------------------------------------------


def test_face_strength_stores_values(face_strength):
    assert face_strength.yield_strength == 270.0e6
    assert face_strength.ultimate_strength is None
    assert face_strength.source_note is not None


@pytest.mark.parametrize("bad", [0.0, -1.0, -270.0e6, math.nan, math.inf, -math.inf])
def test_face_strength_rejects_bad_yield(bad):
    with pytest.raises(ValueError):
        FaceStrength(name="x", yield_strength=bad)


@pytest.mark.parametrize("bad_name", ["", "   "])
def test_face_strength_rejects_empty_name(bad_name):
    with pytest.raises(ValueError):
        FaceStrength(name=bad_name, yield_strength=270.0e6)


@pytest.mark.parametrize("bad", [0.0, -1.0, math.nan, math.inf])
def test_face_strength_rejects_bad_ultimate(bad):
    with pytest.raises(ValueError):
        FaceStrength(name="x", yield_strength=270.0e6, ultimate_strength=bad)


def test_ultimate_below_yield_rejected():
    with pytest.raises(ValueError):
        FaceStrength(name="x", yield_strength=270.0e6, ultimate_strength=200.0e6)


def test_ultimate_above_yield_accepted():
    f = FaceStrength(name="x", yield_strength=270.0e6, ultimate_strength=310.0e6)
    assert f.ultimate_strength == 310.0e6


def test_face_strength_is_immutable(face_strength):
    with pytest.raises(Exception):
        face_strength.yield_strength = 1.0  # type: ignore[misc]


# -- design factor lives on the basis, not the material -------------------


def test_design_factor_is_not_a_material_property(face_strength):
    assert not hasattr(face_strength, "design_factor")
    assert not hasattr(face_strength, "face_design_factor")


def test_allowable_stress_hand_calc(face_strength):
    assert StrengthBasis(face_strength=face_strength).face_allowable_stress == pytest.approx(
        270.0e6, rel=1e-15
    )
    basis = StrengthBasis(face_strength=face_strength, face_design_factor=1.5)
    assert basis.face_allowable_stress == pytest.approx(270.0e6 / 1.5, rel=1e-15)
    assert basis.face_allowable_stress == pytest.approx(180.0e6, rel=1e-12)


def test_design_factor_defaults_to_one(face_strength):
    assert StrengthBasis(face_strength=face_strength).face_design_factor == 1.0


@pytest.mark.parametrize("bad", [0.999, 0.5, 0.0, -1.0])
def test_design_factor_below_one_rejected(face_strength, bad):
    with pytest.raises(ValueError):
        StrengthBasis(face_strength=face_strength, face_design_factor=bad)


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
def test_design_factor_must_be_finite(face_strength, bad):
    with pytest.raises(ValueError):
        StrengthBasis(face_strength=face_strength, face_design_factor=bad)


def test_strength_basis_type_checked():
    with pytest.raises(TypeError):
        StrengthBasis(face_strength="not a FaceStrength")  # type: ignore[arg-type]


# -- B. OrthotropicCoreStrength validation --------------------------------


def test_core_strength_stores_values(ortho_core_strength):
    assert ortho_core_strength.shear_strength_L == 1.0e6
    assert ortho_core_strength.shear_strength_W == 0.4e6
    assert ortho_core_strength.source_note is not None


@pytest.mark.parametrize("field", ["shear_strength_L", "shear_strength_W"])
@pytest.mark.parametrize("bad", [0.0, -1.0, math.nan, math.inf, -math.inf])
def test_core_strength_rejects_bad_values(field, bad):
    kwargs = {"name": "x", "shear_strength_L": 1.0e6, "shear_strength_W": 0.4e6}
    kwargs[field] = bad
    with pytest.raises(ValueError):
        OrthotropicCoreStrength(**kwargs)


@pytest.mark.parametrize("bad_name", ["", "   "])
def test_core_strength_rejects_empty_name(bad_name):
    with pytest.raises(ValueError):
        OrthotropicCoreStrength(name=bad_name, shear_strength_L=1.0e6, shear_strength_W=0.4e6)


def test_core_strength_is_immutable(ortho_core_strength):
    with pytest.raises(Exception):
        ortho_core_strength.shear_strength_L = 1.0  # type: ignore[misc]


def test_core_strength_has_no_compression_property(ortho_core_strength):
    # No through-thickness load exists in the model, so no crush allowable is
    # invented to sit next to one.
    for banned in (
        "compressive_strength",
        "crush_strength",
        "compression_strength",
        "flatwise_compressive_strength",
    ):
        assert not hasattr(ortho_core_strength, banned)


# -- C / D. directional retrieval -----------------------------------------


def test_shear_strength_L_retrieval(ortho_core_strength):
    assert ortho_core_strength.shear_strength(CoreShearDirection.L) == 1.0e6
    assert ortho_core_strength.shear_strength("L") == 1.0e6
    assert ortho_core_strength.shear_strength("  l ") == 1.0e6


def test_shear_strength_W_retrieval(ortho_core_strength):
    assert ortho_core_strength.shear_strength(CoreShearDirection.W) == 0.4e6
    assert ortho_core_strength.shear_strength("W") == 0.4e6
    assert ortho_core_strength.shear_strength("w") == 0.4e6


# -- E. invalid direction rejection ---------------------------------------


@pytest.mark.parametrize("bad", ["", "X", "LW", "average", "T"])
def test_invalid_direction_string_rejected(ortho_core_strength, bad):
    with pytest.raises(ValueError):
        ortho_core_strength.shear_strength(bad)


@pytest.mark.parametrize("bad", [None, 0, 1.0, ["L"]])
def test_non_string_direction_rejected(ortho_core_strength, bad):
    with pytest.raises(TypeError):
        ortho_core_strength.shear_strength(bad)


def test_strengths_are_never_averaged(ortho_core_strength):
    mean = 0.5 * (ortho_core_strength.shear_strength_L + ortho_core_strength.shear_strength_W)
    assert ortho_core_strength.shear_strength("L") != mean
    assert ortho_core_strength.shear_strength("W") != mean
    for d in ("L", "W"):
        assert ortho_core_strength.shear_strength(d) in (
            ortho_core_strength.shear_strength_L,
            ortho_core_strength.shear_strength_W,
        )


def test_directional_strength_ratio_hand_calc(ortho_core_strength):
    # 1.0 MPa / 0.4 MPa = 2.5
    assert ortho_core_strength.directional_strength_ratio == pytest.approx(2.5, rel=1e-15)


# -- F. limiting-constraint enum ------------------------------------------


def test_limiting_constraint_values():
    assert LimitingConstraint.DEFLECTION == "deflection"
    assert LimitingConstraint.FACE_YIELD == "face_yield"
    assert LimitingConstraint.CORE_SHEAR == "core_shear"
    assert str(LimitingConstraint.CORE_SHEAR) == "core_shear"
    assert len(list(LimitingConstraint)) == 3
