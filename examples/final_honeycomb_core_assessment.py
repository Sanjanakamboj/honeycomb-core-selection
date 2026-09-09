"""STM-10 final canonical assessment: one script, the whole screening chain.

Reuses the existing package APIs only - no new physics is introduced here.

    ALL CANDIDATE PROPERTIES AND BOTH SCREENING THRESHOLDS ARE ILLUSTRATIVE
    ENGINEERING INPUTS, NOT MANUFACTURER ALLOWABLES.

Run with:

    python examples/final_honeycomb_core_assessment.py
"""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):  # allow running without installing the package
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sandwich_panel import (  # noqa: E402
    CANDIDATE_CORES,
    ILLUSTRATIVE_FACE_STRENGTH,
    CoreShearDirection,
    DeflectionRequirement,
    FaceMaterial,
    FrequencyRequirement,
    LocalPatchLoad,
    LocalScreenBasis,
    PreliminaryScreens,
    SandwichGeometry,
    StrengthBasis,
    StudyBasis,
    WrinklingModel,
    assess_integrated_design,
    build_integrated_table,
    deflection_limit_sweep,
    frequency_requirement_sweep,
    get_core,
    get_core_compression,
    get_core_strength,
    select_preliminary_core,
)

MM = 1.0e-3
KPA = 1.0e3
MPA = 1.0e6
GPA = 1.0e9

# --- canonical study basis, unchanged since Milestone 1 -------------------

GEOMETRY = SandwichGeometry(
    width=0.500, face_thickness=0.4 * MM, core_thickness=20.0 * MM, span=1.500
)
FACE = FaceMaterial(
    name="Illustrative aluminium-like face sheet",
    youngs_modulus=70.0 * GPA,
    density=2700.0,
)
GLOBAL_LOAD = 50.0  # N, transverse central point load
BASIS = StudyBasis(geometry=GEOMETRY, face=FACE, load=GLOBAL_LOAD)

PATCH = LocalPatchLoad.square(force=100.0, side=25.0 * MM)
SCREENS = PreliminaryScreens(
    deflection=DeflectionRequirement(
        maximum_total_deflection=GEOMETRY.span / 1000.0,
        label="illustrative static deflection limit = span/1000",
    ),
    strength=StrengthBasis(face_strength=ILLUSTRATIVE_FACE_STRENGTH, face_design_factor=1.0),
    local=LocalScreenBasis(
        wrinkling_model=WrinklingModel(
            coefficient=0.5,
            source_note="ILLUSTRATIVE screening coefficient - not a validated allowable.",
        ),
        patch_load=PATCH,
    ),
    frequency=FrequencyRequirement(
        minimum_frequency_hz=25.0,
        mode_number=1,
        label="illustrative minimum fundamental-frequency requirement",
    ),
)


def _rule(title: str) -> None:
    print()
    print(title)
    print("-" * len(title))


def main() -> None:
    table = build_integrated_table(BASIS, SCREENS)
    l_rows = [a for a in table if a.result.direction is CoreShearDirection.L]
    ref = l_rows[0]

    print("=" * 104)
    print("STM-10 HONEYCOMB CORE SELECTION - FINAL ASSESSMENT")
    print("Sandwich solar-panel substrate, preliminary beam-strip screening study")
    print("-" * 104)
    print("ALL CANDIDATE PROPERTIES IN THIS STUDY ARE ILLUSTRATIVE ENGINEERING INPUTS,")
    print("NOT MANUFACTURER ALLOWABLES. Both screening thresholds are illustrative too.")
    print("=" * 104)

    _rule("STUDY BASIS")
    print(f"  geometry      : L = {GEOMETRY.span:.3f} m, b = {GEOMETRY.width:.3f} m, "
          f"t_f = {GEOMETRY.face_thickness * 1e3:.2f} mm, t_c = {GEOMETRY.core_thickness * 1e3:.1f} mm, "
          f"h = {GEOMETRY.total_thickness * 1e3:.2f} mm")
    print(f"  face material : E_f = {FACE.youngs_modulus / GPA:.1f} GPa, "
          f"rho_f = {FACE.density:.0f} kg/m^3, "
          f"illustrative yield = {ILLUSTRATIVE_FACE_STRENGTH.yield_strength / MPA:.0f} MPa "
          f"(design factor {SCREENS.strength.face_design_factor:.2f})")
    print(f"  section       : EI = {ref.result.flexural_rigidity:.2f} N m^2 "
          f"(identical for every candidate - the faces carry the bending stiffness)")
    print(f"  global load   : central point load P = {GLOBAL_LOAD:.1f} N (simply supported strip)")
    print(f"  local load    : {PATCH.force:.0f} N over "
          f"{PATCH.patch_width * 1e3:.0f} x {PATCH.patch_length * 1e3:.0f} mm "
          f"= {PATCH.pressure / KPA:.1f} kPa")
    print("                  INDEPENDENT load case - not simultaneous with the global load")
    print(f"  static screen : {SCREENS.deflection.label} = "
          f"{SCREENS.deflection.maximum_total_deflection * 1e3:.3f} mm")
    print(f"  modal screen  : f_1 >= {SCREENS.frequency.minimum_frequency_hz:.1f} Hz "
          f"(mode {SCREENS.frequency.mode_number}, self-mass only)")
    print(f"  wrinkling     : C_wr = {SCREENS.local.wrinkling_model.coefficient} "
          f"(illustrative, no default exists in the package)")
    print()
    print("  DATA POLICY: no value in this study is a manufacturer allowable, a design")
    print("  allowable or qualification data. No flight qualification is claimed.")

    _rule("CANDIDATE SUMMARY")
    print(f"  {'configuration':<14}{'rho_c':>7}{'G_eff':>8}{'m_A':>8}{'delta':>9}{'f_1':>8}"
          f"   {'static':<7}{'strength':<9}{'local':<7}{'modal':<7}{'OVERALL':<8}")
    print(f"  {'':<14}{'kg/m3':>7}{'MPa':>8}{'kg/m2':>8}{'mm':>9}{'Hz':>8}")
    for a in table:
        print(f"  {a.label:<14}{a.result.core_density:>7.0f}"
              f"{a.modal.effective_shear_modulus / MPA:>8.0f}{a.areal_mass:>8.3f}"
              f"{a.result.total_deflection * 1e3:>9.4f}{a.modal.frequency:>8.3f}"
              f"   {'PASS' if a.deflection_feasible else 'FAIL':<7}"
              f"{'PASS' if a.global_strength_feasible else 'FAIL':<9}"
              f"{'PASS' if a.local_failure_feasible else 'FAIL':<7}"
              f"{'PASS' if a.modal_feasible else 'FAIL':<7}"
              f"{'PASS' if a.overall_feasible else 'FAIL':<8}")
    print(f"  {sum(1 for a in table if a.overall_feasible)}/{len(table)} configurations "
          f"pass all four preliminary screens.")

    _rule("LIMITING UTILISATIONS (demand / capacity, dimensionless; <= 1 passes)")
    print("  Global central-load and modal screens only. Margins in different units are")
    print("  never numerically combined - utilisations are the comparable form.")
    print(f"  {'configuration':<14}{'deflection':>12}{'face yield':>12}{'core shear':>12}"
          f"{'wrinkling':>11}{'modal':>9}   {'closest screen':<14}")
    for a in table:
        u = a.utilisation
        print(f"  {a.label:<14}{u.deflection:>12.4f}{u.face_yield:>12.4f}"
              f"{u.core_shear:>12.4f}{u.wrinkling:>11.4f}{u.frequency:>9.4f}"
              f"   {u.closest_global_screen:<14}")
    print("  -> face yield and core shear are two to three orders of magnitude from")
    print("     critical; deflection and the modal screen are the only close ones.")

    _rule("LOCAL PATCH SCREEN (independent local load case)")
    print("  Core through-thickness compression under the prescribed footprint.")
    print("  Direction-independent - crushing does not involve the L/W shear moduli.")
    print(f"  {'candidate':<10}{'p_patch':>10}{'sigma_c':>10}{'utilisation':>13}"
          f"{'F_crush':>10}   {'screen':<6}")
    print(f"  {'':<10}{'kPa':>10}{'MPa':>10}{'[-]':>13}{'N':>10}")
    for a in l_rows:
        lo = a.sandwich.local
        print(f"  {lo.candidate:<10}{lo.local_core_compression_stress / KPA:>10.1f}"
              f"{lo.core_compression_allowable / MPA:>10.2f}"
              f"{a.utilisation.core_compression_local_patch:>13.4f}"
              f"{lo.core_crush_force_limit:>10.1f}"
              f"   {'PASS' if lo.core_compression_pass else 'FAIL':<6}")

    selection = select_preliminary_core(table)
    _rule("ILLUSTRATIVE PRELIMINARY CORE SELECTION")
    if selection is None:
        print("  No configuration passes all four preliminary screens. No selection is made.")
    else:
        print(f"  selected configuration    : {selection.label}")
        print(f"    candidate               : {selection.candidate} "
              f"({selection.core_density:.0f} kg/m^3 illustrative honeycomb-equivalent)")
        print(f"    orientation             : {selection.direction} - beam strip aligned with the")
        print("                              core ribbon (L) shear direction")
        print(f"    panel areal mass        : {selection.areal_mass:.3f} kg/m^2")
        print(f"    total strip mass        : {selection.total_panel_mass:.3f} kg")
        print(f"    total deflection at {GLOBAL_LOAD:.0f} N: "
              f"{selection.total_deflection * 1e3:.4f} mm")
        print(f"    fundamental frequency   : {selection.first_mode_frequency:.3f} Hz")
        print(f"    frequency margin        : {selection.frequency_margin_hz:+.3f} Hz")
        print(f"    closest screen          : {selection.closest_global_screen} "
              f"(utilisation {selection.closest_global_utilisation:.4f})")
        print(f"    feasible configurations : {selection.feasible_configuration_count} of {len(table)}")
        print(f"    selection basis         : {selection.selection_basis}")

    _rule("ROBUSTNESS TO THE ILLUSTRATIVE REQUIREMENTS")
    print("  Both thresholds are placeholders, so their influence is measured, not assumed.")
    print()
    print(f"  {'f_required [Hz]':>16}{'feasible':>11}{'selected':>16}")
    for r in frequency_requirement_sweep(BASIS, SCREENS, [20.0, 25.0, 28.0, 30.0, 32.0]):
        print(f"  {r.required_frequency_hz:>16.1f}{r.feasible_count:>7}/{r.total_count:<3}"
              f"{r.lightest_feasible_label or '-- none --':>16}")
    print()
    print(f"  {'deflection limit':>18}{'allowable [mm]':>16}{'feasible':>11}{'selected':>16}")
    for r in deflection_limit_sweep(BASIS, SCREENS, [500, 750, 1000, 1250, 1500]):
        print(f"  {'span/' + format(r.span_divisor, '.0f'):>18}"
              f"{r.allowable_deflection * 1e3:>16.3f}"
              f"{r.overall_feasible_count:>7}/{r.total_count:<3}"
              f"{r.selected_label or '-- none --':>16}")
    print()
    print("  -> The SAME configuration is selected at every threshold where anything is")
    print("     feasible: the choice is not an artefact of the placeholder requirements.")
    print("  -> The static screen is BRITTLE - 10/10 feasible at span/1000, 0/10 at")
    print("     span/1250 - so the placeholder limit decides whether a design exists at all.")

    _rule("CORE-THICKNESS TRADE (HC-AL-45, both orientations)")
    core = get_core("HC-AL-45")
    strength = get_core_strength("HC-AL-45")
    compression = get_core_compression("HC-AL-45")
    print(f"  {'dir':>4}{'t_c':>6}{'EI':>10}{'m_A':>8}{'delta':>10}{'sigma_f':>10}"
          f"{'f_1':>9}{'f margin':>10}   {'overall':<8}")
    print(f"  {'':>4}{'mm':>6}{'N m^2':>10}{'kg/m2':>8}{'mm':>10}{'MPa':>10}{'Hz':>9}{'Hz':>10}")
    for direction in ("L", "W"):
        for t_c in (5, 10, 15, 20, 25, 30):
            local_basis = StudyBasis(
                geometry=SandwichGeometry(
                    width=GEOMETRY.width, face_thickness=GEOMETRY.face_thickness,
                    core_thickness=t_c * MM, span=GEOMETRY.span,
                ),
                face=FACE, load=GLOBAL_LOAD,
            )
            a = assess_integrated_design(
                local_basis, core, strength, compression, direction, SCREENS
            )
            print(f"  {direction:>4}{t_c:>6}{a.result.flexural_rigidity:>10.1f}"
                  f"{a.areal_mass:>8.3f}{a.result.total_deflection * 1e3:>10.4f}"
                  f"{a.sandwich.local.face_stress / MPA:>10.4f}{a.modal.frequency:>9.3f}"
                  f"{a.modal.margin_hz:>+10.3f}   "
                  f"{'PASS' if a.overall_feasible else 'FAIL':<8}")
    print("  -> Core depth is the strongest single lever: it raises EI roughly as t_c^2")
    print("     while adding mass only linearly, so both deflection and frequency improve.")
    print("     Nothing thinner than 20 mm passes at this span. t_c is NOT optimised here.")

    _rule("KEY ENGINEERING FINDING")
    lightest = min(table, key=lambda a: a.areal_mass)
    print(f"  The lightest core ({lightest.result.core_name}, "
          f"{lightest.modal.effective_shear_modulus / MPA:.0f} MPa in L - the LOWEST shear")
    print(f"  modulus of the set) also gives the HIGHEST fundamental frequency "
          f"({lightest.modal.frequency:.2f} Hz).")
    print("  EI is set by the identical face sheets and common geometry, so the core only")
    print("  affects (a) distributed mass and (b) the shear-flexibility correction. Over")
    print("  this candidate range the mass penalty of a denser core outweighs the")
    print("  shear-stiffness benefit.")
    print()
    print("  This ordering is specific to the current geometry, face-sheet design, and")
    print("  illustrative candidate set. It is not a general property of sandwich panels.")

    print()
    print("=" * 104)
    print("The selected configuration is an illustrative preliminary choice within a")
    print("simplified beam-strip study. All material properties and screening thresholds")
    print("remain illustrative.")
    print("=" * 104)


if __name__ == "__main__":
    main()
