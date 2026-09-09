"""A-F: orthotropic core validation, directional retrieval, backward compatibility."""

from __future__ import annotations

import math

import pytest

from sandwich_panel import (
    CoreMaterial,
    CoreShearDirection,
    OrthotropicCoreMaterial,
    SandwichPanel,
    effective_core_shear_modulus,
)


# -- A. orthotropic core validation ---------------------------------------


def test_orthotropic_core_stores_values(ortho_core):
    assert ortho_core.name == "TEST-CORE"
    assert ortho_core.density == 40.0
    assert ortho_core.shear_modulus_L == 50.0e6
    assert ortho_core.shear_modulus_W == 20.0e6
    assert ortho_core.family == "test"
    assert ortho_core.source_note is not None


@pytest.mark.parametrize("field", ["density", "shear_modulus_L", "shear_modulus_W"])
@pytest.mark.parametrize("bad", [0.0, -1.0, math.nan, math.inf, -math.inf])
def test_orthotropic_core_rejects_non_positive_or_non_finite(field, bad):
    kwargs = {
        "name": "x",
        "density": 40.0,
        "shear_modulus_L": 50.0e6,
        "shear_modulus_W": 20.0e6,
    }
    kwargs[field] = bad
    with pytest.raises(ValueError):
        OrthotropicCoreMaterial(**kwargs)


@pytest.mark.parametrize("bad_name", ["", "   "])
def test_orthotropic_core_rejects_empty_name(bad_name):
    with pytest.raises(ValueError):
        OrthotropicCoreMaterial(
            name=bad_name, density=40.0, shear_modulus_L=50.0e6, shear_modulus_W=20.0e6
        )


def test_orthotropic_core_is_immutable(ortho_core):
    with pytest.raises(Exception):
        ortho_core.density = 1.0  # type: ignore[misc]


def test_optional_metadata_defaults_to_none():
    c = OrthotropicCoreMaterial(
        name="x", density=40.0, shear_modulus_L=50.0e6, shear_modulus_W=20.0e6
    )
    assert (c.family, c.notes, c.source_note) == (None, None, None)


# -- B / C. directional retrieval -----------------------------------------


def test_shear_modulus_L_retrieval(ortho_core):
    assert ortho_core.shear_modulus(CoreShearDirection.L) == 50.0e6
    assert ortho_core.shear_modulus("L") == 50.0e6
    assert ortho_core.shear_modulus("l") == 50.0e6
    assert ortho_core.shear_modulus("  L  ") == 50.0e6


def test_shear_modulus_W_retrieval(ortho_core):
    assert ortho_core.shear_modulus(CoreShearDirection.W) == 20.0e6
    assert ortho_core.shear_modulus("W") == 20.0e6
    assert ortho_core.shear_modulus("w") == 20.0e6


# -- D. invalid direction rejection ---------------------------------------


@pytest.mark.parametrize("bad", ["", "X", "LW", "WL", "average", "T", "0", "ribbon"])
def test_invalid_direction_string_rejected(ortho_core, bad):
    with pytest.raises(ValueError):
        ortho_core.shear_modulus(bad)
    with pytest.raises(ValueError):
        CoreShearDirection.parse(bad)


@pytest.mark.parametrize("bad", [None, 0, 1.0, ["L"], {"L": 1}])
def test_non_string_direction_rejected(ortho_core, bad):
    with pytest.raises(TypeError):
        ortho_core.shear_modulus(bad)


def test_direction_error_message_mentions_both_directions(ortho_core):
    with pytest.raises(ValueError) as exc:
        ortho_core.shear_modulus("LW")
    message = str(exc.value)
    assert "'L'" in message and "'W'" in message


def test_directions_are_never_averaged(ortho_core):
    # Every accepted direction returns one of the two stored moduli, never a blend.
    for direction in (CoreShearDirection.L, CoreShearDirection.W, "L", "W"):
        assert ortho_core.shear_modulus(direction) in (
            ortho_core.shear_modulus_L,
            ortho_core.shear_modulus_W,
        )
    mean = 0.5 * (ortho_core.shear_modulus_L + ortho_core.shear_modulus_W)
    assert ortho_core.shear_modulus("L") != mean
    assert ortho_core.shear_modulus("W") != mean


def test_parse_is_idempotent():
    for d in CoreShearDirection:
        assert CoreShearDirection.parse(d) is d
        assert CoreShearDirection.parse(d.value) is d


def test_direction_has_a_human_description():
    assert "ribbon" in CoreShearDirection.L.description
    assert "transverse" in CoreShearDirection.W.description


# -- E. directional ratio identity ----------------------------------------


def test_directional_shear_ratio_hand_calc(ortho_core):
    # 50 MPa / 20 MPa = 2.5
    assert ortho_core.directional_shear_ratio == pytest.approx(2.5, rel=1e-15)


def test_directional_shear_ratio_equals_modulus_quotient():
    c = OrthotropicCoreMaterial(
        name="x", density=33.0, shear_modulus_L=77.0e6, shear_modulus_W=28.0e6
    )
    assert c.directional_shear_ratio == pytest.approx(77.0 / 28.0, rel=1e-15)


def test_specific_shear_stiffness_hand_calc(ortho_core):
    # G_L / rho = 50e6 / 40 = 1.25e6 ; G_W / rho = 20e6 / 40 = 5.0e5
    assert ortho_core.specific_shear_stiffness("L") == pytest.approx(1.25e6, rel=1e-15)
    assert ortho_core.specific_shear_stiffness("W") == pytest.approx(5.0e5, rel=1e-15)


# -- F. backward compatibility with the Milestone 1 core ------------------


def test_milestone1_core_material_still_works_unchanged():
    c = CoreMaterial(name="m1 core", density=48.0, shear_modulus=50.0e6)
    assert c.density == 48.0
    assert c.shear_modulus == 50.0e6  # still a plain attribute, not a method


def test_effective_shear_modulus_helper_handles_both_representations(ortho_core):
    m1 = CoreMaterial(name="m1 core", density=48.0, shear_modulus=50.0e6)
    # Milestone 1 core is direction-independent by construction.
    assert effective_core_shear_modulus(m1, "L") == 50.0e6
    assert effective_core_shear_modulus(m1, "W") == 50.0e6
    # Milestone 2 core is not.
    assert effective_core_shear_modulus(ortho_core, "L") == 50.0e6
    assert effective_core_shear_modulus(ortho_core, "W") == 20.0e6


def test_effective_shear_modulus_helper_still_validates_direction(ortho_core):
    m1 = CoreMaterial(name="m1 core", density=48.0, shear_modulus=50.0e6)
    for core in (m1, ortho_core):
        with pytest.raises(ValueError):
            effective_core_shear_modulus(core, "LW")


def test_effective_shear_modulus_helper_rejects_other_types():
    with pytest.raises(TypeError):
        effective_core_shear_modulus("not a core", "L")  # type: ignore[arg-type]


def test_as_effective_core_produces_a_milestone1_core(ortho_core):
    core_l = ortho_core.as_effective_core("L")
    core_w = ortho_core.as_effective_core(CoreShearDirection.W)
    assert isinstance(core_l, CoreMaterial)
    assert core_l.shear_modulus == 50.0e6
    assert core_w.shear_modulus == 20.0e6
    assert core_l.density == core_w.density == ortho_core.density
    assert "[L]" in core_l.name and "[W]" in core_w.name


def test_as_effective_core_feeds_the_unchanged_panel(m2_geometry, m2_face, ortho_core):
    # The panel stays orientation-agnostic: it only ever sees a scalar G.
    panel = SandwichPanel(
        geometry=m2_geometry, face=m2_face, core=ortho_core.as_effective_core("W")
    )
    assert panel.core.shear_modulus == 20.0e6


def test_panel_still_rejects_an_orthotropic_core_directly(m2_geometry, m2_face, ortho_core):
    # Orientation must be resolved BEFORE the panel; the panel knows nothing
    # about honeycomb ribbons and must not silently guess a direction.
    with pytest.raises(TypeError):
        SandwichPanel(geometry=m2_geometry, face=m2_face, core=ortho_core)  # type: ignore[arg-type]
