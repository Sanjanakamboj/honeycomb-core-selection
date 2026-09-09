"""Milestone 5: first-order modal screening and the illustrative preliminary core selection.

ALL CANDIDATE MATERIAL PROPERTIES IN THIS REPOSITORY ARE ILLUSTRATIVE - stiffness,
strength, compression and wrinkling alike. Both screening thresholds (the static
deflection limit and the minimum-frequency requirement) are illustrative too.

Any selection printed below is therefore an ILLUSTRATIVE PRELIMINARY CORE
SELECTION. It is not a qualified core, not a flight-selected material, not a
certified design, not a manufacturer recommendation and not an optimised solution.

Run with:

    python examples/modal_core_selection.py
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
    assess_core_modal,
    build_integrated_table,
    core_depth_modal_sweep,
    deflection_limit_sweep,
    frequency_requirement_sweep,
    get_core,
    modal_density_sweep,
    modal_face_thickness_sweep,
    modal_shear_modulus_sweep,
    select_preliminary_core,
)

MM = 1.0e-3
MPA = 1.0e6
GPA = 1.0e9

# --- study basis: unchanged from Milestones 1-4 ---------------------------

GEOMETRY = SandwichGeometry(
    width=0.500, face_thickness=0.4 * MM, core_thickness=20.0 * MM, span=1.500
)
FACE = FaceMaterial(
    name="Illustrative aluminium-like face sheet (not a datasheet value)",
    youngs_modulus=70.0 * GPA,
    density=2700.0,
)
LOAD = 50.0
BASIS = StudyBasis(geometry=GEOMETRY, face=FACE, load=LOAD)

# Illustrative minimum fundamental-frequency requirement.
#
# Chosen AFTER computing the candidate range (27.10-31.10 Hz) and deliberately set
# as a clean round value BELOW that whole range, so it cannot manufacture a winner
# by excluding part of the set. The requirement sweep below shows what a
# discriminating threshold would look like, and confirms the selection is the same
# at every threshold from 5 Hz up to 30 Hz.
FREQUENCY_LIMIT_HZ = 25.0

SCREENS = PreliminaryScreens(
    deflection=DeflectionRequirement(
        maximum_total_deflection=GEOMETRY.span / 1000.0,
        label="illustrative panel deflection limit = span/1000",
    ),
    strength=StrengthBasis(face_strength=ILLUSTRATIVE_FACE_STRENGTH, face_design_factor=1.0),
    local=LocalScreenBasis(
        wrinkling_model=WrinklingModel(
            coefficient=0.5,
            source_note="ILLUSTRATIVE screening convention - not a validated allowable.",
        ),
        patch_load=LocalPatchLoad.square(force=100.0, side=25.0 * MM),
    ),
    frequency=FrequencyRequirement(
        minimum_frequency_hz=FREQUENCY_LIMIT_HZ,
        mode_number=1,
        label="illustrative minimum fundamental-frequency requirement",
    ),
)


def _rule(title: str) -> None:
    print()
    print(title)
    print("-" * len(title))


def main() -> None:
    print("=" * 98)
    print("MODAL SCREENING AND ILLUSTRATIVE PRELIMINARY CORE SELECTION - Milestone 5")
    print("Milestone 5 introduces a first-order free-vibration screening requirement")
    print("because the prior static screens retained every candidate. The frequency")
    print("threshold and all material properties remain ILLUSTRATIVE.")
    print("=" * 98)

    table = build_integrated_table(BASIS, SCREENS)
    l_rows = [a for a in table if a.result.direction is CoreShearDirection.L]
    w_rows = [a for a in table if a.result.direction is CoreShearDirection.W]

    _rule("STUDY BASIS")
    print(f"  span L = {GEOMETRY.span:.3f} m, width b = {GEOMETRY.width:.3f} m, "
          f"t_f = {GEOMETRY.face_thickness * 1e3:.2f} mm, t_c = {GEOMETRY.core_thickness * 1e3:.1f} mm")
    print(f"  face: E_f = {FACE.youngs_modulus / GPA:.1f} GPa, rho_f = {FACE.density:.0f} kg/m^3")
    print(f"  EI = {l_rows[0].result.flexural_rigidity:.4e} N m^2 (identical for every candidate)")
    print()
    print("  DATA POLICY: every candidate property in this repository is ILLUSTRATIVE -")
    print("    stiffness (M2), strength (M3), compression and wrinkling (M4). None is a")
    print("    manufacturer allowable, a design allowable or qualification data.")
    print()
    print(f"  static screens : central point load P = {LOAD:.1f} N")
    print(f"    {SCREENS.deflection.label} = "
          f"{SCREENS.deflection.maximum_total_deflection * 1e3:.3f} mm")
    print(f"    face yield {ILLUSTRATIVE_FACE_STRENGTH.yield_strength / MPA:.0f} MPa, "
          f"design factor {SCREENS.strength.face_design_factor:.2f}")
    print(f"    wrinkling C_wr = {SCREENS.local.wrinkling_model.coefficient}, "
          f"local patch {SCREENS.local.patch_load.force:.0f} N over "
          f"{SCREENS.local.patch_load.patch_width * 1e3:.0f} x "
          f"{SCREENS.local.patch_load.patch_length * 1e3:.0f} mm")
    print(f"  modal screen   : {SCREENS.frequency.label}")
    print(f"    f_1 >= {FREQUENCY_LIMIT_HZ:.1f} Hz, mode {SCREENS.frequency.mode_number}, "
          f"simply supported, self-mass only")
    print("    NOT a launch-provider requirement, not a coupled-loads result, not a")
    print("    qualification threshold")

    _rule("CANDIDATE MODAL TABLE (first mode)")
    print(f"  {'config':<14}{'m_A':>7}{'mu':>8}{'G_eff':>8}{'f_bend':>9}{'f_1':>9}"
          f"{'shear pen':>11}{'margin':>9}{'f_1/m_A':>10}  {'modal':<6}")
    print(f"  {'':<14}{'kg/m2':>7}{'kg/m':>8}{'MPa':>8}{'Hz':>9}{'Hz':>9}{'%':>11}{'Hz':>9}"
          f"{'Hz m2/kg':>10}")
    for a in table:
        m = a.modal
        print(f"  {a.label:<14}{a.areal_mass:>7.3f}{m.distributed_mass:>8.3f}"
              f"{m.effective_shear_modulus / MPA:>8.0f}{m.bending_only_frequency:>9.3f}"
              f"{m.frequency:>9.3f}{m.modal.shear_frequency_penalty_fraction * 100:>11.2f}"
              f"{m.margin_hz:>9.2f}{m.frequency_to_areal_mass:>10.3f}"
              f"  {'PASS' if m.modal_feasible else 'FAIL':<6}")
    freqs = [a.modal.frequency for a in table]
    print(f"  -> f_1 spans {min(freqs):.2f} - {max(freqs):.2f} Hz across all 10 configurations.")
    print("  -> The bending-only frequency is IDENTICAL for L and W (EI and mass do not")
    print("     depend on shear direction); only the shear correction differs.")
    print("  -> KEY RESULT: the LIGHTEST core has the HIGHEST frequency in both directions,")
    print("     despite having the lowest G. Added core mass costs more frequency than the")
    print("     extra shear stiffness buys back. This was computed, not assumed.")

    _rule("INTEGRATED SCREEN (all four families, combined only by logical AND)")
    print(f"  {'config':<14}{'defl':>6}{'strength':>9}{'local':>7}{'modal':>7}{'OVERALL':>9}"
          f"   {'closest global screen':<22}{'util':>7}{'patch util':>12}")
    for a in table:
        u = a.utilisation
        print(f"  {a.label:<14}"
              f"{'PASS' if a.deflection_feasible else 'FAIL':>6}"
              f"{'PASS' if a.global_strength_feasible else 'FAIL':>9}"
              f"{'PASS' if a.local_failure_feasible else 'FAIL':>7}"
              f"{'PASS' if a.modal_feasible else 'FAIL':>7}"
              f"{'PASS' if a.overall_feasible else 'FAIL':>9}"
              f"   {u.closest_global_screen:<22}{u.closest_global_utilisation:>7.4f}"
              f"{u.core_compression_local_patch:>12.4f}")
    n_ok = sum(1 for a in table if a.overall_feasible)
    print(f"  {n_ok}/{len(table)} configurations pass all four screens.")
    print("  -> Utilisations are demand/capacity, so <= 1 passes and they ARE comparable")
    print("     across modes; the raw margins (m, [-], Hz) are never blended.")
    print("  -> The local patch utilisation is an INDEPENDENT load case and is reported")
    print("     separately, never mixed into the global comparison.")
    print("  -> For the two heaviest cores the closest screen is now FREQUENCY, not")
    print("     deflection - the first time any other screen has been critical.")

    _rule("DIRECTIONAL EFFECT (L vs W)")
    print(f"  {'candidate':<10}{'f_bend':>9}{'f_1,L':>9}{'f_1,W':>9}{'penalty':>10}"
          f"{'penalty':>10}{'G_L/G_W':>10}")
    print(f"  {'':<10}{'Hz':>9}{'Hz':>9}{'Hz':>9}{'Hz':>10}{'%':>10}{'[-]':>10}")
    for core in CANDIDATE_CORES:
        al = next(a for a in l_rows if a.result.core_name == core.name)
        aw = next(a for a in w_rows if a.result.core_name == core.name)
        print(f"  {core.name:<10}{al.modal.bending_only_frequency:>9.3f}"
              f"{al.modal.frequency:>9.3f}{aw.modal.frequency:>9.3f}"
              f"{al.modal.frequency - aw.modal.frequency:>10.3f}"
              f"{100 * (aw.modal.frequency / al.modal.frequency - 1):>10.2f}"
              f"{core.shear_modulus_L / core.shear_modulus_W:>10.3f}")
    print("  -> f_1,L >= f_1,W always, since G_L > G_W. The penalty is NOT a simple ratio")
    print("     identity as in the static case: bending stiffness and mass both contribute.")
    print("  -> The softest core (HC-AL-30) pays the largest directional penalty.")

    _rule("CORE-DEPTH MODAL TRADE (HC-AL-45)")
    print(f"  {'dir':>4}{'t_c':>7}{'EI':>11}{'m_A':>8}{'mu':>8}{'shear ratio':>13}"
          f"{'f_bend':>9}{'f_1':>9}  {'modal':<6}")
    print(f"  {'':>4}{'mm':>7}{'N m^2':>11}{'kg/m2':>8}{'kg/m':>8}{'[-]':>13}{'Hz':>9}{'Hz':>9}")
    for r in core_depth_modal_sweep(
        BASIS, get_core("HC-AL-45"),
        [5 * MM, 10 * MM, 15 * MM, 20 * MM, 25 * MM, 30 * MM], SCREENS.frequency,
    ):
        print(f"  {r.direction.value:>4}{r.core_thickness * 1e3:>7.1f}"
              f"{r.flexural_rigidity:>11.1f}{r.areal_mass:>8.3f}{r.distributed_mass:>8.3f}"
              f"{r.shear_flexibility_ratio:>13.4f}{r.bending_only_frequency:>9.3f}"
              f"{r.frequency:>9.3f}  {'PASS' if r.modal_feasible else 'FAIL':<6}")
    print("  -> Core depth raises f_1 strongly and monotonically (9.1 -> 41.4 Hz in L),")
    print("     because EI grows roughly as t_c^2 while mass grows only linearly.")
    print("  -> The shear flexibility ratio RISES with depth (EI grows faster than A_s), so")
    print("     the shear penalty grows too - but the bending gain dominates by far.")
    print("  -> Core depth is NOT optimised here.")

    _rule("DENSITY SENSITIVITY (G = 40 MPa, geometry fixed)")
    print(f"  {'rho_c':>8}{'EI':>11}{'mu':>8}{'f_bend':>9}{'f_1':>9}")
    print(f"  {'kg/m3':>8}{'N m^2':>11}{'kg/m':>8}{'Hz':>9}{'Hz':>9}")
    for r in modal_density_sweep(BASIS, [25.0, 40.0, 60.0, 80.0, 100.0], 40.0 * MPA,
                                 SCREENS.frequency):
        print(f"  {r.swept_value:>8.0f}{r.flexural_rigidity:>11.1f}{r.distributed_mass:>8.3f}"
              f"{r.bending_only_frequency:>9.3f}{r.frequency:>9.3f}")
    print("  -> EI unchanged; mu rises linearly; f_1 falls monotonically as 1/sqrt(mu).")

    _rule("SHEAR-MODULUS SENSITIVITY (rho_c = 45 kg/m3, geometry fixed)")
    print(f"  {'G':>8}{'m_A':>8}{'f_bend':>9}{'f_1':>9}{'shear penalty':>15}")
    print(f"  {'MPa':>8}{'kg/m2':>8}{'Hz':>9}{'Hz':>9}{'%':>15}")
    for r in modal_shear_modulus_sweep(
        BASIS, [5 * MPA, 10 * MPA, 20 * MPA, 40 * MPA, 80 * MPA, 160 * MPA, 500 * MPA],
        45.0, SCREENS.frequency,
    ):
        print(f"  {r.swept_value / MPA:>8.0f}{r.areal_mass:>8.3f}{r.bending_only_frequency:>9.3f}"
              f"{r.frequency:>9.3f}"
              f"{100 * (1 - r.frequency / r.bending_only_frequency):>15.2f}")
    print("  -> Mass and the bending-only frequency are untouched; f_1 rises monotonically")
    print("     and approaches the bending-only limit from below as G grows.")

    _rule("FACE-THICKNESS MODAL SENSITIVITY (t_c fixed, HC-AL-45)")
    print(f"  {'t_f':>7}{'EI':>11}{'m_A':>8}{'f_bend':>9}{'f_1':>9}")
    print(f"  {'mm':>7}{'N m^2':>11}{'kg/m2':>8}{'Hz':>9}{'Hz':>9}")
    for r in modal_face_thickness_sweep(
        BASIS, [0.2 * MM, 0.3 * MM, 0.4 * MM, 0.5 * MM, 0.6 * MM],
        get_core("HC-AL-45"), SCREENS.frequency,
    ):
        print(f"  {r.swept_value * 1e3:>7.1f}{r.flexural_rigidity:>11.1f}{r.areal_mass:>8.3f}"
              f"{r.bending_only_frequency:>9.3f}{r.frequency:>9.3f}")
    print("  -> Both EI and face mass rise with t_f. Stiffness wins over this range, so f_1")
    print("     increases monotonically - computed, not assumed. The gain flattens because")
    print("     EI/mu tends to a constant once the faces dominate the mass.")

    _rule("MULTI-MODE SANITY (HC-AL-45, L)")
    print(f"  {'mode':>6}{'f_bend':>11}{'f_1':>11}{'shear penalty':>16}{'f_n/f_1':>10}")
    first = assess_core_modal(BASIS, get_core("HC-AL-45"), "L", SCREENS.frequency, mode_number=1)
    for n in (1, 2, 3):
        a = assess_core_modal(BASIS, get_core("HC-AL-45"), "L", SCREENS.frequency, mode_number=n)
        print(f"  {n:>6}{a.bending_only_frequency:>11.3f}{a.frequency:>11.3f}"
              f"{a.modal.shear_frequency_penalty_fraction * 100:>15.2f}%"
              f"{a.frequency / first.frequency:>10.4f}")
    print("  -> The bending-only reference scales exactly as n^2. The shear-corrected values")
    print("     fall increasingly short of it, because the correction term grows as n^2 too.")
    print("  -> Rotary inertia is neglected, so only mode 1 is used as a design screen.")

    _rule("REQUIREMENT SENSITIVITY (the threshold is illustrative, so this matters)")
    print(f"  {'f_required':>12}{'feasible':>11}{'lightest feasible configuration':>36}")
    print(f"  {'Hz':>12}{'of 10':>11}")
    for r in frequency_requirement_sweep(BASIS, SCREENS, [5.0, 10.0, 15.0, 20.0, 25.0, 28.0, 30.0, 32.0]):
        label = r.lightest_feasible_label or "-- none feasible --"
        print(f"  {r.required_frequency_hz:>12.1f}{r.feasible_count:>7}/{r.total_count:<3}"
              f"{label:>36}")
    print("  -> The modal screen only starts to discriminate above ~28 Hz, and excludes")
    print("     everything above ~31 Hz.")
    print("  -> Crucially, the SAME configuration is selected at every threshold where any")
    print("     configuration is feasible, so the selection is not an artefact of the")
    print("     threshold choice.")

    _rule("STATIC DEFLECTION-LIMIT SENSITIVITY (the M2 limit is also a placeholder)")
    print(f"  {'limit':>10}{'allowable':>12}{'static':>9}{'overall':>9}{'selected':>16}")
    print(f"  {'':>10}{'mm':>12}{'of 10':>9}{'of 10':>9}")
    for r in deflection_limit_sweep(BASIS, SCREENS, [500, 750, 1000, 1500, 2000]):
        print(f"  {'span/' + format(r.span_divisor, '.0f'):>10}"
              f"{r.allowable_deflection * 1e3:>12.3f}{r.static_feasible_count:>9}"
              f"{r.overall_feasible_count:>9}{r.selected_label or '-- none --':>16}")
    print("  -> The static screen is BRITTLE: everything passes down to span/1000 and")
    print("     nothing passes at span/1500. The selection is unchanged wherever anything")
    print("     is feasible, but the placeholder limit controls whether a design exists")
    print("     at all. That is a limitation of the requirement, not of the candidates.")

    selection = select_preliminary_core(table)
    _rule("ILLUSTRATIVE PRELIMINARY CORE SELECTION")
    if selection is None:
        print("  No configuration passes all four preliminary screens.")
        print("  No selection is made.")
    else:
        print(f"  candidate                     : {selection.candidate}")
        print(f"  orientation                   : {selection.direction} "
              f"(beam strip aligned with the core {selection.direction} shear direction)")
        print(f"  core density                  : {selection.core_density:.1f} kg/m^3")
        print(f"  panel areal mass              : {selection.areal_mass:.3f} kg/m^2")
        print(f"  total strip mass              : {selection.total_panel_mass:.3f} kg")
        print(f"  first-mode frequency          : {selection.first_mode_frequency:.3f} Hz")
        print(f"  frequency margin              : {selection.frequency_margin_hz:+.3f} Hz "
              f"(vs {FREQUENCY_LIMIT_HZ:.1f} Hz illustrative requirement)")
        print(f"  total deflection at {LOAD:.0f} N      : "
              f"{selection.total_deflection * 1e3:.4f} mm")
        print(f"  deflection / strength / local / modal : "
              f"{selection.deflection_feasible} / {selection.global_strength_feasible} / "
              f"{selection.local_failure_feasible} / {selection.modal_feasible}")
        print(f"  closest global screen         : {selection.closest_global_screen} "
              f"(utilisation {selection.closest_global_utilisation:.4f})")
        print(f"  local patch utilisation       : {selection.local_patch_utilisation:.4f} "
              f"(independent load case)")
        print(f"  feasible configurations       : {selection.feasible_configuration_count} "
              f"of {len(table)}")
        print()
        print("  selection basis:")
        print(f"    {selection.selection_basis}")
        print()
        print("  This configuration wins on mass AND carries the highest frequency of the")
        print("  set, so the minimum-mass rule and the modal screen agree rather than")
        print("  trading against each other. The result is driven by the assumed model and")
        print("  requirements as much as by the candidate data.")

    print()
    print("=" * 98)
    print("The selected configuration is an illustrative preliminary choice within this")
    print("simplified candidate set, not a flight-qualified material selection.")
    print("This selection is conditional on illustrative material properties and screening")
    print("requirements; sourced allowables and higher-fidelity panel analysis are still")
    print("required.")
    print("=" * 98)


if __name__ == "__main__":
    main()
