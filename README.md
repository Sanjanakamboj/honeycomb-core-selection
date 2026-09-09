# honeycomb-core-selection

**STM-10 — Honeycomb Core Selection**
Preliminary sandwich-panel core selection for a spacecraft solar-panel substrate.

> **Milestone 1 establishes the verified sandwich-panel mechanics only. Candidate
> honeycomb materials and final core selection are intentionally deferred.**

---

## Objective

Build and independently verify the structural mechanics foundation for a symmetric
sandwich panel made of two identical face sheets bonded to a lightweight honeycomb
core, so that later milestones can trade candidate cores on a trustworthy basis.

The key question Milestone 1 answers:

> Can the sandwich-panel model correctly capture the stiffness and mass leverage of
> increasing lightweight core depth while keeping the thin face sheets structurally
> active?

Answer, from the verified model: **yes** — see
[Stiffness vs core depth](#stiffness-vs-core-depth) below.

## Current scope

In scope for Milestone 1:

- validated face-sheet, core and panel geometry
- computed sandwich neutral axis and section properties
- flexural rigidity `EI` (exact parallel-axis formulation)
- areal mass and strip mass
- simply supported beam-strip response under a central transverse point load
- core transverse-shear contribution to deflection
- total bending + shear deflection, with a shear-fraction diagnostic
- face-sheet normal stress and average core shear stress
- independent hand-calculation verification
- core-depth, face-thickness and core-shear-modulus sensitivities
- one representative solar-panel-substrate sanity case

Deliberately **not** implemented yet: candidate core database, final core
selection, core crushing, face wrinkling, face yielding criteria, local
indentation, insert/potting loads, shear crimping, panel buckling, vibration and
modal analysis, thermal gradients, CTE mismatch, adhesive layers, orthotropic
honeycomb L/W directions, trade ranking, optimisation, portfolio plots.

## Sandwich idealisation

A symmetric three-layer beam strip: top face / core / bottom face.

Assumptions:

- identical top and bottom face sheets
- isotropic (or isotropic-equivalent) face material
- lightweight core, symmetric layup about the mid-plane
- small deflections, linear elasticity
- perfect bonding between faces and core
- the core carries the transverse shear
- the faces carry the bending normal stress

SI units are used throughout the package.

## Geometry convention

```
 z = +h/2  ----------------------  top face outer surface
           [ top face,    t_f ]
 z = 0     ======================  sandwich mid-plane
           [ core,        t_c ]
           [ bottom face, t_f ]
 z = -h/2  ----------------------  bottom face outer surface
```

| symbol | meaning | unit |
| --- | --- | --- |
| `b` | strip width | m |
| `t_f` | thickness of each face sheet | m |
| `t_c` | core thickness | m |
| `L` | span | m |
| `h = 2 t_f + t_c` | total thickness | m |
| `z_f = t_c/2 + t_f/2` | face centroid offset | m |
| `A_f = b t_f` | area of one face sheet | m² |
| `A_c = A_s = b t_c` | core area / core shear area | m² |

## Neutral-axis convention

`z = 0` is the geometric mid-plane. The neutral axis is **computed**, not assumed,
from the modulus-weighted first moment over the layers:

```
z_na = sum(E_i A_i z_i) / sum(E_i A_i)
```

For the symmetric layup modelled here this evaluates to exactly `z_na = 0`, which
the test suite asserts numerically (including when a core modulus is supplied).

## Section properties

One face sheet about the neutral axis, using the parallel-axis theorem **exactly**:

```
I_face  = b t_f^3 / 12 + (b t_f) z_f^2
I_faces = 2 I_face
```

The common thin-face approximation is computed alongside it for comparison, never
used in its place:

```
I_faces,approx = 2 (b t_f) z_f^2          (drops each face's own b t_f^3 / 12)
```

For the representative case below the approximation under-predicts `I_faces` by
**0.0128 %** — small, as expected for thin faces, and the model reports it rather
than assuming it.

### Core bending contribution

> **Core normal-stress bending stiffness is neglected; the core contributes
> transverse shear stiffness only.**

This is the standard lightweight-honeycomb idealisation. No core Young's modulus is
invented anywhere in the package. A caller may supply one explicitly
(`SandwichPanel(..., core_modulus=...)`) if a later study needs it; the default is
`None` (bending-inactive core).

`CoreMaterial` carries a single **effective** transverse shear modulus `G_c`. Real
honeycomb is strongly orthotropic — ribbon (L) and expansion (W) directions differ.
Nothing here should be read as a claim that honeycomb is isotropic; later milestones
may distinguish `G_L` / `G_W`.

## Flexural rigidity

```
EI = E_f * I_faces            [N m^2]      (primary structural quantity)
D_strip = EI / b              [N m]        (per-unit-width convenience only)
```

`D_strip` is *not* the plate rigidity `E t^3 / (12 (1 - nu^2))`: no Poisson
correction is applied in Milestone 1.

## Areal mass

```
m_A     = 2 rho_f t_f + rho_c t_c     [kg/m^2]
m_total = m_A * b * L                 [kg]
```

Bare faces + core only: no adhesive film, inserts, doublers or edge close-outs.

## Central-point-load response

Primary verified load case: **simply supported strip, central transverse point load
`P`**, chosen because the hand formulas are compact and independently checkable.

```
M_max   = P L / 4
V_max   = P / 2
delta_b = P L^3 / (48 EI)                        bending (Euler-Bernoulli)
delta_s = P L / (4 kappa G_c A_s)                core transverse shear, A_s = b t_c
delta   = delta_b + delta_s
```

**Shear-correction factor.** `kappa` is exposed explicitly and defaults to `1.0`,
because `G_c` is already an effective sandwich-core transverse shear modulus and the
shear is taken as carried uniformly by the core over `A_s = b t_c`. It is reported
in every result and never applied silently.

**Shear-fraction diagnostic.** `delta_s / delta_total` is reported, because a
sandwich can be very bending-stiff and still be core-shear-sensitive.

### Stress conventions

```
sigma_face,max = M_max (h/2) / I_faces      extreme fibre, OUTER face surface
tau_core       = V_max / (b t_c)            AVERAGE effective core shear stress
```

`sigma_face,max` is a beam-theory normal-stress estimate. `tau_core` is a
first-order screening quantity — it is **not** a honeycomb cell-wall stress.

## Representative sanity result

Illustrative solar-panel-substrate strip (`examples/sandwich_panel_sanity.py`).
**All values are illustrative placeholders, not datasheet or design values.** The
point load is a stiffness demonstration only — *not* a launch or qualification load.

Inputs: `L = 1.5 m`, `b = 0.5 m`, `t_f = 0.4 mm`, `t_c = 20 mm`;
face `E_f = 70 GPa`, `rho_f = 2700 kg/m³`; core `G_c = 40 MPa`, `rho_c = 32 kg/m³`;
`P = 50 N`.

| quantity | value |
| --- | --- |
| total thickness `h` | 20.80 mm |
| computed neutral axis `z_na` | 0.000000e+00 m (mid-plane) |
| face centroid offset `z_f` | 10.20 mm |
| `I_faces` exact | 4.162133e-08 m⁴ |
| `I_faces` thin-face approx. | 4.161600e-08 m⁴ (−0.0128 %) |
| `EI` | 2.913e+03 N m² |
| areal mass `m_A` | 2.800 kg/m² (faces 2.160, core 0.640) |
| strip mass | 2.100 kg |
| `M_max` / `V_max` | 18.750 N m / 25.000 N |
| max face stress (outer surface) | 4.685 MPa |
| avg core shear stress | 2.500 kPa |
| bending deflection `delta_b` | 1.2067 mm |
| shear deflection `delta_s` | 0.0469 mm |
| total deflection `delta` | 1.2535 mm |
| shear fraction `delta_s / delta` | 0.0374 |

### Stiffness vs core depth

`b`, `t_f`, `E_f` and `L` held fixed; core depth varied (baseline `t_c = 5 mm`):

| `t_c` [mm] | `h` [mm] | `EI` [N m²] | `EI / EI₀` | `m_A` [kg/m²] | `m_A / m_A₀` | `delta` [mm] |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 5 | 5.80 | 2.045e+02 | 1.00 | 2.320 | 1.000 | 17.379 |
| 10 | 10.80 | 7.575e+02 | 3.70 | 2.480 | 1.069 | 4.735 |
| 15 | 15.80 | 1.661e+03 | 8.12 | 2.640 | 1.138 | 2.180 |
| 20 | 20.80 | 2.913e+03 | 14.25 | 2.800 | 1.207 | 1.254 |
| 25 | 25.80 | 4.517e+03 | 22.09 | 2.960 | 1.276 | 0.816 |

**Interpretation.** Going from a 5 mm to a 25 mm core raises `EI` by ~22× for a
~28 % areal-mass increase: the faces stay thin and structurally active while the
light core pushes them apart. That is the whole point of a sandwich, and the model
reproduces it.

The growth is **not** an exact square law. `EI` scales with `z_f² = (t_c/2 + t_f/2)²`
plus the faces' own `b t_f³/12`, so with finite face thickness doubling the core
depth multiplies `EI` by slightly *less* than 4 (10 → 20 mm gives 3.85×). The test
suite asserts the ratio lies strictly between 3.5 and 4.0 rather than claiming 4.

The sanity example also prints face-thickness and core-shear-modulus sensitivities:
face thickness buys stiffness and stress margin but pays directly in mass;
`delta_b` is invariant with `G_c` while `delta_s` scales as `1/G_c`.

## Verification summary

`134 tests, all passing.` Expected values are written as **independent arithmetic**
— literal formulas or hand-computed constants — rather than by calling the helpers
under test.

Covered:

- material validation (positive, finite, named; Poisson range when supplied)
- geometry validation (all dimensions positive and finite)
- symmetric neutral axis exactly at `z = 0`, computed not assumed
- face centroid location, face local `I`, parallel-axis term, total `I`
- exact vs thin-face approximation, and the error's growth with face thickness
- `EI` linear in `E_f`, linear in `b`, independent of span, monotonic in `t_c`
- `EI` core-depth growth bounded strictly between 3.5× and 4× per doubling
- areal-mass hand calc, face/core decomposition, exact density scaling
- `M_max`, `V_max`, `delta_b`, `delta_s`, total-deflection identity
- face stress and core shear stress hand calcs; linearity in `P`
- `delta_b` bit-for-bit invariant with `G_c`; `delta_s` exactly `1/G_c`
- total deflection strictly decreasing with `G_c`; shear fraction in (0, 1)
- invalid load, invalid `kappa`, invalid core modulus and empty-sweep rejection
- determinism: repeated calculations byte-identical
- end-to-end smoke test of the sanity example

## Limitations

- symmetric sandwich only; identical face sheets
- isotropic / isotropic-equivalent face modulus
- effective isotropic core shear modulus; **no orthotropic L/W honeycomb
  distinction**
- core normal-stress bending stiffness neglected
- perfect bonding assumed; no adhesive layer modelled or mass-accounted
- no face wrinkling, core crushing, shear crimping or local indentation
- no insert / potting loads
- no panel or global buckling
- no thermal effects, gradients or CTE mismatch
- no vibration or modal analysis
- small-deflection linear elasticity only
- beam-strip model, not a two-dimensional plate model
- all material and geometry values in the example are illustrative placeholders
- **no certification, qualification or flight-worthiness claim of any kind**

## Install and test

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[test]"
pytest
python examples/sandwich_panel_sanity.py
```

The test suite and the example also run without installing (a root `conftest.py`
and a path fallback in the example put `src/` on `sys.path`).

## Repository layout

```
src/sandwich_panel/
    validation.py     shared positive/finite validators
    materials.py      FaceMaterial, CoreMaterial
    geometry.py       SandwichGeometry
    section.py        neutral axis, second moments, EI
    mass.py           areal mass and strip mass
    loads.py          central-point-load response
    panel.py          SandwichPanel (assembly + load cases)
    sensitivity.py    core-depth / face-thickness / core-shear sweeps
tests/                verification suite
examples/             sandwich_panel_sanity.py
```

## Licensing

No licence has been chosen for this project yet. There is deliberately **no**
`LICENSE` file, and `pyproject.toml` deliberately carries **no** `license` field or
licence classifier, so no licence is claimed or implied.

## Next milestone

Milestone 2 will introduce candidate honeycomb cores and the comparative trade.
Nothing in this repository yet constitutes a core selection.
