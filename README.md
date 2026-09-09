# honeycomb-core-selection

**STM-10 — Honeycomb Core Selection**
Preliminary sandwich-panel core selection for a spacecraft solar-panel substrate.

> **Milestone 1 establishes the verified sandwich-panel mechanics only. Candidate
> honeycomb materials and final core selection are intentionally deferred.**

> **Milestone 2 compares candidate-core mass and shear-stiffness behaviour under a
> common sandwich geometry. Strength-based core selection is intentionally
> deferred.**

> **Milestone 3 adds first-order face-yield and average core-shear screening only.
> Crushing, wrinkling, local indentation, inserts and other sandwich-specific
> failure modes remain intentionally deferred.**

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

In scope for **Milestone 1** (mechanics foundation):

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

Added in **Milestone 2** (candidate trade framework):

- orthotropic core representation with distinct L and W transverse shear moduli
- explicit, validated panel/core orientation selection
- a small canonical candidate-core database (illustrative values)
- candidate-by-candidate sandwich response on one common study basis
- mass-deflection trade table with an illustrative stiffness screen
- L-vs-W directional sensitivity, core-density and core-shear sensitivities
- a directional core-depth trade
- preliminary non-dominance (Pareto) screening on mass and deflection

Added in **Milestone 3** (first-order strength screening):

- face-sheet strength record and an explicit, separately held design factor
- directional honeycomb core shear strengths in L and W
- preliminary face yield margin and average effective core shear margin
- per-candidate governing strength mode, computed from the margins
- combined stiffness + strength feasibility, kept dimensionally separate
- preliminary central-point-load limits from face, core and deflection
- directional L/W strength sensitivity, load-level sensitivity and a
  mass-vs-capacity trade with a load-capacity-to-areal-mass indicator

Deliberately **not** implemented yet: final core selection or recommendation, core
compression and crushing, face wrinkling, intracell buckling, shear crimping, local
indentation, contact/bearing stress, insert and potting loads, adhesive failure,
panel buckling, damage tolerance, fatigue, thermal distortion, CTE mismatch,
vibration and modal analysis, optimisation, final portfolio plots and publication
polish.

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

## Verification summary — Milestone 1

`134 tests` (of `433` in the repository), all passing, unchanged since the
Milestone 1 commit. Expected values are written as **independent arithmetic** —
literal formulas or hand-computed constants — rather than by calling the helpers
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

---

# Milestone 2 — candidate core trade framework

> **Milestone 2 compares candidate-core mass and shear-stiffness behaviour under a
> common sandwich geometry. Strength-based core selection is intentionally
> deferred.**

The engineering question:

> How do candidate honeycomb-core density and directional shear stiffness affect
> sandwich-panel areal mass, total deflection and shear-dominated behaviour for the
> same face sheets, geometry and transverse load?

## Why real honeycomb needs L and W shear directions

Milestone 1 collapsed the core to a single effective transverse shear modulus
`G_c`. That is fine for establishing mechanics, but it is not how honeycomb
behaves and not how it is specified. Honeycomb is strongly orthotropic in
transverse shear, and datasheets quote two distinct moduli:

- **L** — the ribbon / longitudinal direction, where foil ribbons run and are
  doubled at the cell bond lines. This is the **stiffer** shear direction.
- **W** — the transverse / expansion direction, across the ribbons. This is the
  **softer** direction, typically roughly one third to one half of `G_L`.

Collapsing the two loses a real design decision. For the candidates below, running
the panel across the ribbon direction instead of along it increases the core shear
deflection by a factor of 1.9 to 2.8. Orientation therefore has to be a stated,
validated choice, and the two directions are **never silently averaged** — an L/W
average has no physical meaning for a strip loaded in one direction.

## Orthotropic candidate representation

`OrthotropicCoreMaterial(name, density, shear_modulus_L, shear_modulus_W,
family, notes, source_note)`, with all three physical quantities validated
positive and finite.

The Milestone 1 `CoreMaterial` is **unchanged** — it remains the
direction-independent effective shear layer, and every Milestone 1 test still
passes against it byte-for-byte. The two are bridged explicitly:

```
CoreShearDirection.L | CoreShearDirection.W      # or the strings "L" / "W"

core.shear_modulus(direction)          -> G_L or G_W          [Pa]
core.directional_shear_ratio           -> G_L / G_W           [-]
core.specific_shear_stiffness(dir)     -> G_eff / rho_c        [m^2/s^2]
core.as_effective_core(direction)      -> Milestone 1 CoreMaterial
effective_core_shear_modulus(core, direction)                  # handles both types
```

Orientation is resolved **before** the panel is built. `SandwichPanel` still takes
a Milestone 1 `CoreMaterial` carrying one scalar modulus and knows nothing about
honeycomb ribbons — it rejects an `OrthotropicCoreMaterial` passed directly rather
than silently guessing a direction. Any invalid direction (`""`, `"X"`, `"LW"`,
`"average"`, a number, `None`) raises immediately.

## Candidate database

`src/sandwich_panel/core_database.py` — five candidates spanning two families.

> **ILLUSTRATIVE HONEYCOMB-EQUIVALENT CANDIDATES.** No value below is a
> manufacturer datasheet value. They are representative engineering-study inputs:
> **not** manufacturer data, **not** design allowables, **not** qualification or
> certification data. Every candidate carries an explicit `source_note` recording
> this, and a test asserts that provenance is present on all of them. The set is
> uniformly illustrative — sourced and illustrative numbers are never blended. If
> sourced data is added later it must arrive with its own provenance note.

Magnitudes were screened against the study basis *before* being fixed, to confirm
the set gives a useful, non-pathological comparison (core shear between ~1 % and
~16 % of total deflection at a 20 mm core) rather than a degenerate one.

| candidate | family | `rho_c` [kg/m³] | `G_L` [MPa] | `G_W` [MPa] | `G_L/G_W` |
| --- | --- | ---: | ---: | ---: | ---: |
| HC-AL-30 | aluminium-equivalent | 30 | 20.0 | 8.0 | 2.50 |
| HC-AL-45 | aluminium-equivalent | 45 | 40.0 | 15.0 | 2.67 |
| HC-AR-48 | aramid-paper-equivalent | 48 | 30.0 | 16.0 | 1.88 |
| HC-AL-60 | aluminium-equivalent | 60 | 70.0 | 25.0 | 2.80 |
| HC-AL-80 | aluminium-equivalent | 80 | 120.0 | 45.0 | 2.67 |

The aramid-equivalent entry exists so the trade is not one monotonic family: at
essentially the same density as HC-AL-45 it is softer in shear and less
anisotropic, which gives the shear-stiffness-to-density indicator something real
to discriminate.

## Common study basis

Every candidate is evaluated on **one** basis — the Milestone 1 representative
panel, reused verbatim. Geometry is never tuned per candidate, so this is a clean
material-property-only comparison:

`L = 1.5 m`, `b = 0.5 m`, `t_f = 0.4 mm`, `t_c = 20 mm`, face `E_f = 70 GPa`,
`rho_f = 2700 kg/m³`, central point load `P = 50 N` (stiffness demonstration only,
not a launch or qualification load).

Because the faces carry all the bending stiffness and the core carries none, two
quantities are **identical for every candidate**:

```
EI       = 2.9135e+03 N m^2
delta_b  = 1.2067 mm
```

Only areal mass (through `rho_c t_c`) and shear deflection (through `G_eff`) move.
That invariance is asserted bit-for-bit in the tests — it is the backbone of the
whole trade.

## Deflection requirement

The **only** Milestone 2 feasibility check is `delta_total <= delta_allowable`.

```
margin            = allowable - actual        [m]   positive is good
normalised_margin = allowable / actual - 1    [-]   positive is good
PASS when actual <= allowable                       (exact equality passes)
```

The limit used is `span/1000 = 1.5 mm`, chosen **by convention** as a common
precision-structure deflection guideline — deliberately not a number
reverse-engineered from the candidate results to manufacture a winner. It is an
`illustrative panel deflection limit` for preliminary stiffness screening. It is
**not** a qualification limit, verification requirement or certification criterion.

No strength allowable of any kind is applied. Face stress and core shear stress are
still reported, as **demand diagnostics only** — there is nothing to compare them
against until a later milestone introduces allowables.

## L-vs-W directional comparison and the mass–deflection trade

`examples/core_candidate_trade.py`. Areal mass and total deflection, with the
`1.5 mm` illustrative screen:

| candidate | `m_A` [kg/m²] | `G_L` [MPa] | `delta_L` [mm] | shear frac L | `G_W` [MPa] | `delta_W` [mm] | shear frac W | screen |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :--- |
| HC-AL-30 | 2.760 | 20.0 | 1.3004 | 7.21 % | 8.0 | 1.4410 | 16.26 % | PASS / PASS |
| HC-AL-45 | 3.060 | 40.0 | 1.2535 | 3.74 % | 15.0 | 1.3317 | 9.39 % | PASS / PASS |
| HC-AR-48 | 3.120 | 30.0 | 1.2692 | 4.92 % | 16.0 | 1.3239 | 8.85 % | PASS / PASS |
| HC-AL-60 | 3.360 | 70.0 | 1.2335 | 2.17 % | 25.0 | 1.2817 | 5.85 % | PASS / PASS |
| HC-AL-80 | 3.760 | 120.0 | 1.2223 | 1.28 % | 45.0 | 1.2483 | 3.34 % | PASS / PASS |

**The screen does not discriminate at this geometry.** All 10 candidate-direction
combinations pass, because at a 20 mm core the response is bending-dominated
(`delta_b = 1.2067 mm` against a `1.5 mm` limit, so at most 20 % of the budget is
available to core shear). That is reported as found. The data was not tuned to
force a mixed outcome, and the limit was not moved to create one. Where the limit
*does* bite is core depth: at `t_c <= 15 mm` every candidate fails it (see below).

**Directional penalty.** For a fixed geometry and load the identity

```
delta_s,W / delta_s,L  ==  G_L / G_W
```

holds exactly, and is verified numerically for every candidate. The W-direction
total-deflection penalty ranges from `+0.026 mm` (HC-AL-80) to `+0.141 mm`
(HC-AL-30) — the softest core is punished hardest by a poor orientation.

**Shear-stiffness-to-density indicator.** `G_eff / rho_c` [m²/s²] is reported as a
`first-order shear-stiffness-to-density indicator`. It is a coarse screening aid,
**not** a universal optimisation index and not a ranking on its own — it ignores
strength, stability, minimum manufacturable density and cost entirely. On `G_L/rho`
the aluminium-equivalent set rises monotonically (6.67e5 → 1.50e6 m²/s²) while
HC-AR-48 sits at 6.25e5, below the lighter HC-AL-45 — which is exactly why the
lightest core is not automatically the best one.

**Non-dominance.** On the two axes *lower areal mass* and *lower total deflection*,
the L-direction front is HC-AL-30, HC-AL-45, HC-AL-60, HC-AL-80; HC-AR-48 is
dominated by HC-AL-45 (lighter *and* stiffer). This is a screening aid on two
stiffness/mass axes only. It is not optimisation and it does not select a core: a
candidate dominated here may still win once strength, stability, thermal and
manufacturing criteria enter.

**No core is selected.** Candidates are retained for later strength/failure
screening.

## Core-depth observation

Sweeping `t_c` for HC-AL-45 in both directions shows core depth acting on **three**
things simultaneously:

| `t_c` [mm] | `EI` [N m²] | `m_A` [kg/m²] | `delta_b` [mm] | `delta_s,L` [mm] | `delta_s,W` [mm] | `delta_L` [mm] | screen (1.5 mm) |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | :--- |
| 5 | 2.045e+02 | 2.385 | 17.1919 | 0.1875 | 0.5000 | 17.3794 | FAIL |
| 10 | 7.575e+02 | 2.610 | 4.6411 | 0.0938 | 0.2500 | 4.7349 | FAIL |
| 15 | 1.661e+03 | 2.835 | 2.1172 | 0.0625 | 0.1667 | 2.1797 | FAIL |
| 20 | 2.913e+03 | 3.060 | 1.2067 | 0.0469 | 0.1250 | 1.2535 | PASS |
| 25 | 4.517e+03 | 3.285 | 0.7784 | 0.0375 | 0.1000 | 0.8159 | PASS |

Increasing core depth (i) raises `EI` steeply through face separation, (ii) adds
core mass linearly, and (iii) **also reduces shear deflection**, because the core
shear area `A_s = b t_c` grows with it. Points (i) and (iii) both help stiffness;
only (ii) costs. This is why the deflection screen is a core-depth question before
it is a core-material question. Core depth is **not** optimised in this milestone.

## Verification summary — Milestone 2

`139 additional tests` (repository total `433`, all passing). Milestone 1's 134
tests are unchanged and still green; their files are byte-identical to the
Milestone 1 commit.

Covered:

- orthotropic core validation; positive, finite, named, immutable
- `G_L` / `G_W` retrieval, including case- and whitespace-tolerant strings
- invalid-direction rejection (`""`, `"X"`, `"LW"`, `"average"`, numbers, `None`)
- L and W are never averaged; the error message names both valid directions
- `G_L/G_W` ratio identity and the `G/rho` indicator, by hand calculation
- backward compatibility: Milestone 1 `CoreMaterial` unchanged and still usable;
  the panel still rejects an orthotropic core passed directly
- database: unique names, no duplicates, deterministic order, all properties
  positive and finite, provenance metadata present on every candidate, `G_L > G_W`
  for all, plausible anisotropy band, useful density and stiffness spread, more
  than one family
- `EI` and bending deflection bit-for-bit identical across every candidate and
  direction; face stress and core shear stress likewise
- areal mass moves only with core density, and is identical between L and W
- shear deflection moves only with the selected modulus
- `delta_s,W / delta_s,L == G_L / G_W` for every candidate
- total-deflection identity; shear fraction strictly in (0, 1)
- panel-mass consistency; areal-mass hand calculation
- requirement: pass, fail, exact-boundary pass, margin identity, input validation
- density sweep: mass linear, every stiffness quantity bit-for-bit unmoved
- shear sweep: mass and `EI` unmoved, `delta_s` exactly `1/G`, total approaching
  the bending-only floor
- core depth: `EI` up, mass up, shear deflection down in both directions, basis
  not mutated
- determinism of results, trade tables and sweeps
- load scaling: all deflection and stress demands linear in `P`; mass, `EI` and
  shear fraction unaffected
- trade example smoke test, plus an assertion that it never prints a selection,
  recommendation or winner

---

# Milestone 3 — first-order strength screening

> **Milestone 3 adds first-order face-yield and average core-shear screening only.
> Crushing, wrinkling, local indentation, inserts and other sandwich-specific
> failure modes remain intentionally deferred.**

The engineering question:

> Which candidate cores remain structurally feasible when the common sandwich panel
> is checked for face-sheet normal stress and directional core shear strength, and
> how much central-point-load capacity does each candidate retain?

## Why deflection alone was insufficient

Milestone 2 ended with all ten candidate-direction combinations passing the
`1.5 mm` stiffness screen, so deflection did not discriminate the set. The obvious
next discriminator is strength — but only two strength checks are actually
supported by the current beam-strip mechanics, and Milestone 3 implements exactly
those two and nothing else:

- **face longitudinal normal stress** vs a face allowable
- **average effective core shear stress** vs a directional core shear strength

There is no through-thickness compression load anywhere in the model, so no core
crushing check is invented to sit alongside them. No wrinkling equation is added.
`OrthotropicCoreStrength` deliberately has no compressive-strength attribute, and a
test asserts that.

## Face yield allowable convention

`FaceStrength(name, yield_strength, ultimate_strength=None, source_note, notes)` is
**pure material data**. The design factor lives separately, on the study's
`StrengthBasis`, so a knockdown can never hide inside a material property:

```
sigma_face_allowable = yield_strength / face_design_factor      (face_design_factor >= 1)
```

A test asserts `FaceStrength` exposes no design-factor attribute at all. Yield is
the single allowable basis for Milestone 3; `ultimate_strength` is accepted and
recorded but never used as a basis, and is not supplied for the shipped record.

## Directional core shear strengths

`OrthotropicCoreStrength(name, shear_strength_L, shear_strength_W, ...)`, using the
same L/W convention as the Milestone 2 moduli, with the same rule: **L and W are
never averaged**, and an invalid direction raises.

> **ILLUSTRATIVE STRENGTH INPUT — NOT MANUFACTURER ALLOWABLE.** No verifiable
> manufacturer strength data was obtained, so every strength value is a
> representative engineering-study input: not a manufacturer allowable, not a
> design allowable or A/B-basis value, not qualification data. Every record carries
> an explicit `source_note`, asserted present by test. Sourced and illustrative
> values are never blended.

The face record is an illustrative aluminium-like yield strength of **270 MPa**; no
alloy is claimed, because the elastic face material was never tied to one (a test
asserts no alloy designation appears in the record).

| candidate | `tau_L` [MPa] | `tau_W` [MPa] | `tau_L/tau_W` |
| --- | ---: | ---: | ---: |
| HC-AL-30 | 0.90 | 0.55 | 1.636 |
| HC-AL-45 | 1.60 | 0.95 | 1.684 |
| HC-AR-48 | 1.20 | 0.70 | 1.714 |
| HC-AL-60 | 2.40 | 1.40 | 1.714 |
| HC-AL-80 | 3.60 | 2.10 | 1.714 |

The strength database is aligned one-to-one with the elastic database — same names,
same order, no extras — and the module fails at import time if the two ever drift.

## Strength-margin definitions

Both strength margins are dimensionless margins of safety:

```
MS_face = sigma_allowable / sigma_face,max - 1      preliminary face yield margin
MS_core = tau_allowable   / tau_core        - 1      average effective core shear margin
```

`MS >= 0` passes, so exactly reaching the allowable **passes**. These are
preliminary screening margins, **not certification margins**; `MS_core` in
particular carries no cell-wall stress fidelity.

The governing strength mode is whichever has the **smaller** margin. It is computed
from the margins, never assumed — a test sweeps the core allowable so that each
mode takes a turn governing.

### Stiffness and strength are kept separate

`CandidateDesignAssessment` reports `deflection_feasible`, `strength_feasible` and
`overall_feasible = deflection_feasible AND strength_feasible`. The deflection
margin is a **length** and the strength margins are **dimensionless**; they are
never numerically combined. A test asserts no blended-margin attribute exists.

## Preliminary allowable-load calculation

Every demand in this model is exactly linear in the central point load `P`, so each
capacity is an exact scaling (the core one also has a closed form):

```
P_face        = P_ref * sigma_allowable / sigma_face(P_ref)
P_core        = 2 b t_c tau_allowable                        (closed form)
P_deflection  = P_ref * delta_allowable / delta_total(P_ref)

P_strength    = min(P_face, P_core)                          strength only
P_preliminary = min(P_face, P_core, P_deflection)
```

with the governing constraint reported as `"deflection"`, `"face_yield"` or
`"core_shear"`. These are **preliminary central-point-load limits** for a
simplified beam-strip model — not ultimate loads, not limit loads, not design loads
and not certification allowables. Tests confirm each returned load produces a zero
margin in its own check, that 0.1 % below passes and 0.1 % above fails, and that
the capacities are independent of the load the reference response was evaluated at.

## The 50 N screen, and the headline finding

At the Milestone 1–2 study load the demands are `sigma_face,max = 4.6851 MPa` and
`tau_core = 2.5 kPa` — identical for every candidate, since both depend on geometry
and load alone.

**All ten candidate-direction combinations pass both screens**, with:

- `MS_face = 56.63` for every candidate (the face limit cannot depend on the core)
- `MS_core` between `219` (HC-AL-30 W) and `1439` (HC-AL-80 L)

Strength margins are two to three orders of magnitude clear. The strength screen
**does not discriminate the candidate set**. That is reported as found: the
illustrative strengths were deliberately not reduced to manufacture a failure or a
preferred candidate. For core shear even to tie face yield here, the allowable
would have to fall to about `0.144 MPa` — far below any real honeycomb.

## Allowable-load trade

| candidate | `m_A` [kg/m²] | `P_defl` [N] | `P_face` [N] | `P_core` [N] | `P_prelim` [N] | governing | `P/m_A` [N·m²/kg] |
| --- | ---: | ---: | ---: | ---: | ---: | :--- | ---: |
| HC-AL-30 [L] | 2.760 | 57.67 | 2881.5 | 18000 | 57.67 | deflection | 20.90 |
| HC-AL-45 [L] | 3.060 | 59.83 | 2881.5 | 32000 | 59.83 | deflection | 19.55 |
| HC-AR-48 [L] | 3.120 | 59.09 | 2881.5 | 24000 | 59.09 | deflection | 18.94 |
| HC-AL-60 [L] | 3.360 | 60.80 | 2881.5 | 48000 | 60.80 | deflection | 18.10 |
| HC-AL-80 [L] | 3.760 | 61.36 | 2881.5 | 72000 | 61.36 | deflection | 16.32 |
| HC-AL-30 [W] | 2.760 | 52.05 | 2881.5 | 11000 | 52.05 | deflection | 18.86 |
| HC-AL-45 [W] | 3.060 | 56.32 | 2881.5 | 19000 | 56.32 | deflection | 18.41 |
| HC-AR-48 [W] | 3.120 | 56.65 | 2881.5 | 14000 | 56.65 | deflection | 18.16 |
| HC-AL-60 [W] | 3.360 | 58.52 | 2881.5 | 28000 | 58.52 | deflection | 17.42 |
| HC-AL-80 [W] | 3.760 | 60.08 | 2881.5 | 42000 | 60.08 | deflection | 15.98 |

**DEFLECTION governs every candidate in both directions.** The face limit is about
**50×** the deflection limit and the core-shear limit is **211× to 1173×** it. This
panel is *stiffness-critical, not strength-critical* — a real and useful negative
result, and exactly what one expects of a thin, light substrate on a 1.5 m span.

`P_preliminary / m_A` is reported as a `preliminary load-capacity-to-areal-mass
indicator`: a coarse screening diagnostic, **not** a universal optimisation metric.
Because deflection governs throughout, it currently just re-expresses the
Milestone 2 stiffness-per-mass picture — the lightest core, HC-AL-30 [L], leads it
at 20.90 N·m²/kg while HC-AL-80 [L] has the highest absolute capacity at 61.36 N.

## L/W strength comparison

For a fixed geometry the identity

```
P_core,L / P_core,W  ==  tau_L / tau_W
```

holds exactly, and is verified for every candidate. The directional strength
penalty is real (1.636–1.714×) but **never governs here**; the L/W penalty that
actually bites is the Milestone 2 *stiffness* one, which moves the overall
preliminary limit by only 2–11 % because the bending term dominates.

## Load sensitivity

Sweeping HC-AL-45 from 25 N to 3000 N (loads far above the deflection limit shown
only to locate the crossings, not proposed as design loads): every demand is
exactly linear in `P`, so the deflection screen fails first, just above ~56–60 N,
and face yield only at ~2.9 kN (`MS_face = -0.040` at 3000 N). Core shear never
becomes critical anywhere in the range.

## Core-depth strength observation

| `t_c` [mm] | `m_A` [kg/m²] | `EI` [N·m²] | `P_face` [N] | `P_defl,L` [N] | `P_core,L` [N] | `P_lim,L` [N] | governing |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | :--- |
| 5 | 2.385 | 2.045e+02 | 725.3 | 4.32 | 8000 | 4.32 | deflection |
| 10 | 2.610 | 7.575e+02 | 1442.8 | 15.84 | 16000 | 15.84 | deflection |
| 15 | 2.835 | 1.661e+03 | 2161.9 | 34.41 | 24000 | 34.41 | deflection |
| 20 | 3.060 | 2.913e+03 | 2881.5 | 59.83 | 32000 | 59.83 | deflection |
| 25 | 3.285 | 4.517e+03 | 3601.2 | 91.92 | 40000 | 91.92 | deflection |

Core depth raises **all three** capacities simultaneously — the deflection limit
roughly with `t_c²` (through `EI`), and both the face limit and the core-shear
limit roughly with `t_c` — while core mass grows linearly. Deflection still governs
throughout, because it starts far lower and even its faster growth does not close
a ~48× gap over this range. Core depth is **not** optimised here.

## Verification summary — Milestone 3

`160 additional tests` (repository total `433`, all passing). The 273 Milestone 1–2
tests are unchanged and still green; their files are byte-identical to the
Milestone 2 commit, and the only prior source file touched is `__init__.py`
(exports and version).

Covered:

- `FaceStrength` and `OrthotropicCoreStrength` validation: positive, finite, named,
  immutable; ultimate-below-yield rejected
- the design factor is not a material property, must be >= 1, and scales the
  allowable exactly
- `OrthotropicCoreStrength` exposes no compressive/crush attribute
- directional strength retrieval, invalid-direction rejection, never averaged
- face and core margin hand calculations, exact-boundary PASS, fail cases
- governing mode is the minimum margin, computed not hard-coded, and never
  reports `deflection`
- `strength_feasible` is exactly `face_pass AND core_pass`; `overall_feasible` is
  exactly `deflection AND strength`, with each failing alone
- length-valued and dimensionless margins are never blended into one number
- face, core-shear and deflection allowable loads by independent hand arithmetic
- the closed-form core limit agrees with the linear-scaling form
- capacities independent of the reference load; face limit direction-independent
- `P_preliminary` is the minimum of three, with the governing constraint matching;
  a sweep makes each of the three constraints govern in turn
- zero margin at each returned load; 0.1 % below passes, 0.1 % above fails
- strength database aligned one-to-one with the elastic database: same names, same
  deterministic order, unique, no extras, all positive and finite, provenance
  present, no alloy claimed
- `P_core,L / P_core,W == tau_L / tau_W` for every candidate
- face limit, face stress, face margin, core shear stress, `EI` and bending
  deflection all identical across every candidate
- all demands exactly linear in `P`; demand ratios double when `P` doubles
- core depth raises `EI`, mass, and all three load limits monotonically, and the
  deflection limit grows faster than the strength limits
- Milestone 2 candidate results and deflection assessments reproduce byte-identically
  through the Milestone 3 layer
- determinism of assessments, tables and sweeps
- example smoke test, plus assertions that it never prints a selection and never
  reports a margin for a deferred failure mode

## Limitations

- symmetric sandwich only; identical face sheets
- isotropic / isotropic-equivalent face modulus
- core normal-stress bending stiffness neglected
- perfect bonding assumed; no adhesive layer modelled or mass-accounted
- no face wrinkling, core crushing, shear crimping or local indentation
- no insert / potting loads
- no panel or global buckling
- no thermal effects, gradients or CTE mismatch
- no vibration or modal analysis
- small-deflection linear elasticity only
- beam-strip model, not a two-dimensional plate model
- all material and geometry values in the examples are illustrative placeholders

Added by Milestone 2:

- candidate core properties are **illustrative unless explicitly sourced**; the
  shipped database is uniformly illustrative and labelled as such
- transverse shear is represented by **L and W moduli only** — there is no full
  orthotropic constitutive tensor
- no core compression (through-thickness) modulus
- no core shear strength, and no core compression strength
- no face wrinkling allowable
- no core crushing, shear crimping or local indentation
- no moisture or environmental knockdowns
- no temperature dependence of any core property
- no minimum manufacturable density or other producibility constraint
- no cell size, foil gauge, perforation or splice-line representation
- the deflection limit is **illustrative only** and is not a qualification limit
- the non-dominance screen uses two axes only (mass, deflection) and is not
  optimisation

Added by Milestone 3:

- strength values are **illustrative unless explicitly sourced**; the shipped face
  and core strength records are uniformly illustrative and labelled as such
- face **yield only**: no plastic redistribution, no ultimate basis, no
  ultimate/yield interaction
- **average** effective core shear stress only, with no cell-wall stress resolution
- no core compression modulus, no core compression strength, no crushing
- no face wrinkling allowable and no intracell (dimpling) buckling
- no shear crimping
- no local indentation and no contact- or bearing-pressure model
- no insert or potting loads
- no adhesive or bondline failure
- no damage tolerance and no fatigue
- no environmental, moisture or temperature knockdowns on strength
- margins are **preliminary screening margins, not certification margins**
- the preliminary load limits are not ultimate, limit or design loads
- the load-capacity-to-areal-mass indicator is a screening diagnostic, not an
  optimisation metric
- **no final core selection has been made**
- **no certification, qualification or flight-worthiness claim of any kind**

## Install and test

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[test]"
pytest
python examples/sandwich_panel_sanity.py
python examples/core_candidate_trade.py
python examples/core_strength_screen.py
```

The test suite and all three examples also run without installing (a root `conftest.py`
and a path fallback in each example put `src/` on `sys.path`).

## Repository layout

```
src/sandwich_panel/
  Milestone 1 - mechanics
    validation.py     shared positive/finite validators
    materials.py      FaceMaterial, CoreMaterial  (+ Milestone 2 additions)
    geometry.py       SandwichGeometry
    section.py        neutral axis, second moments, EI
    mass.py           areal mass and strip mass
    loads.py          central-point-load response
    panel.py          SandwichPanel (assembly + load cases)
    sensitivity.py    core-depth / face-thickness / core-shear sweeps
  Milestone 2 - candidate trade
    directions.py     CoreShearDirection (L / W) convention
    materials.py      OrthotropicCoreMaterial, effective_core_shear_modulus
    core_database.py  illustrative candidate cores
    requirements.py   DeflectionRequirement / DeflectionAssessment
    trade.py          StudyBasis, candidate evaluation, trade table, dominance,
                      density / shear / core-depth sweeps
  Milestone 3 - strength screening
    strength.py       FaceStrength, OrthotropicCoreStrength, StrengthBasis,
                      margins, LimitingConstraint
    strength_database.py  illustrative face and core strength records
    design_screen.py  strength assessment, preliminary load capacity, combined
                      design table, load / core-depth capacity sweeps
tests/                verification suite
                      (134 Milestone 1 + 139 Milestone 2 + 160 Milestone 3 = 433)
examples/             sandwich_panel_sanity.py     (Milestone 1)
                      core_candidate_trade.py      (Milestone 2)
                      core_strength_screen.py      (Milestone 3)
```

## Licensing

No licence has been chosen for this project yet. There is deliberately **no**
`LICENSE` file, and `pyproject.toml` deliberately carries **no** `license` field or
licence classifier, so no licence is claimed or implied.

## Next milestone

Milestone 4 will address the sandwich-specific failure modes that the beam-strip
model cannot currently reach — core crushing, face wrinkling, shear crimping, local
indentation and insert/potting loads. Those are *local* modes, and since Milestone 3
shows this panel to be stiffness-critical rather than strength-critical in its
global response, they are where a genuine selection is most likely to be decided.
Nothing in this repository yet constitutes a core selection, and all material
properties remain illustrative.
