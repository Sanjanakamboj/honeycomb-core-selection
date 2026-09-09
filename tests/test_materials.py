"""A. Material validation."""

from __future__ import annotations

import math

import pytest

from sandwich_panel import CoreMaterial, FaceMaterial


def test_face_material_stores_values():
    m = FaceMaterial(name="Al-like", youngs_modulus=70.0e9, density=2700.0)
    assert m.name == "Al-like"
    assert m.youngs_modulus == 70.0e9
    assert m.density == 2700.0
    assert m.poissons_ratio is None


@pytest.mark.parametrize("bad", [0.0, -1.0, -70.0e9])
def test_face_material_rejects_non_positive_modulus(bad):
    with pytest.raises(ValueError):
        FaceMaterial(name="x", youngs_modulus=bad, density=2700.0)


@pytest.mark.parametrize("bad", [0.0, -2700.0])
def test_face_material_rejects_non_positive_density(bad):
    with pytest.raises(ValueError):
        FaceMaterial(name="x", youngs_modulus=70.0e9, density=bad)


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
def test_face_material_rejects_non_finite(bad):
    with pytest.raises(ValueError):
        FaceMaterial(name="x", youngs_modulus=bad, density=2700.0)
    with pytest.raises(ValueError):
        FaceMaterial(name="x", youngs_modulus=70.0e9, density=bad)


@pytest.mark.parametrize("bad_name", ["", "   "])
def test_material_rejects_empty_name(bad_name):
    with pytest.raises(ValueError):
        FaceMaterial(name=bad_name, youngs_modulus=70.0e9, density=2700.0)
    with pytest.raises(ValueError):
        CoreMaterial(name=bad_name, density=48.0, shear_modulus=50.0e6)


@pytest.mark.parametrize("nu", [-1.0, 0.5, 0.9, math.nan])
def test_face_material_rejects_out_of_range_poisson(nu):
    with pytest.raises(ValueError):
        FaceMaterial(name="x", youngs_modulus=70.0e9, density=2700.0, poissons_ratio=nu)


def test_face_material_accepts_valid_poisson():
    m = FaceMaterial(name="x", youngs_modulus=70.0e9, density=2700.0, poissons_ratio=0.33)
    assert m.poissons_ratio == pytest.approx(0.33)


def test_core_material_stores_values():
    c = CoreMaterial(name="hc", density=48.0, shear_modulus=50.0e6)
    assert (c.density, c.shear_modulus) == (48.0, 50.0e6)


@pytest.mark.parametrize("bad", [0.0, -1.0, math.nan, math.inf])
def test_core_material_rejects_bad_values(bad):
    with pytest.raises(ValueError):
        CoreMaterial(name="hc", density=bad, shear_modulus=50.0e6)
    with pytest.raises(ValueError):
        CoreMaterial(name="hc", density=48.0, shear_modulus=bad)


def test_materials_are_immutable():
    m = FaceMaterial(name="x", youngs_modulus=70.0e9, density=2700.0)
    with pytest.raises(Exception):
        m.youngs_modulus = 1.0  # type: ignore[misc]
