"""B. Geometry validation and D. face centroid location."""

from __future__ import annotations

import math

import pytest

from sandwich_panel import SandwichGeometry

from .conftest import B, L, T_C, T_F


@pytest.mark.parametrize(
    "field", ["width", "face_thickness", "core_thickness", "span"]
)
@pytest.mark.parametrize("bad", [0.0, -1.0e-3, math.nan, math.inf, -math.inf])
def test_geometry_rejects_non_positive_or_non_finite(field, bad):
    kwargs = {"width": B, "face_thickness": T_F, "core_thickness": T_C, "span": L}
    kwargs[field] = bad
    with pytest.raises(ValueError):
        SandwichGeometry(**kwargs)


def test_total_thickness_hand_calc(geometry):
    # h = 2 * 0.0005 + 0.015 = 0.016 m
    assert geometry.total_thickness == pytest.approx(0.016, rel=0, abs=1e-15)


def test_face_centroid_offset_hand_calc(geometry):
    # z_f = 0.015/2 + 0.0005/2 = 0.0075 + 0.00025 = 0.00775 m
    assert geometry.face_centroid_offset == pytest.approx(0.00775, rel=0, abs=1e-15)


def test_face_separation_is_twice_the_offset(geometry):
    # d = t_c + t_f = 0.0155 m
    assert geometry.face_separation == pytest.approx(0.0155, rel=0, abs=1e-15)


def test_areas_hand_calc(geometry):
    assert geometry.face_area == pytest.approx(0.4 * 0.0005)  # 2.0e-4 m^2
    assert geometry.core_area == pytest.approx(0.4 * 0.015)  # 6.0e-3 m^2
    assert geometry.core_shear_area == pytest.approx(0.006)
    assert geometry.plan_area == pytest.approx(0.4 * 1.2)  # 0.48 m^2


def test_geometry_is_immutable(geometry):
    with pytest.raises(Exception):
        geometry.width = 1.0  # type: ignore[misc]
