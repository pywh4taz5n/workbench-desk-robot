# Controller PCB engineering package

Eight-layer controller/power-distribution board for a 48 V desk robot. The package
defines the electrical architecture, interfaces, protection, isolated CAN,
stackup, placement/thermal constraints, DFM limits, and manufacturing outputs.

## Reproduce checks

```bash
python hardware/pcb/tools/electrical_checks.py
```

The report is written to `generated/electrical_report.json`. Open
`kicad/controller.kicad_pro` with KiCad 10. The detailed EVT companion board has
117 controlled electrical components, four M3 NPTH mounting holes (121 total
footprints), fifteen SMT test pads, more than 1,300 track/via items, 31 filled copper zones,
eight copper layers, and a physical 8 mm primary/secondary isolation region.
Reproduce the controlled sources with:

```bash
<kicad>/bin/python hardware/pcb/tools/generate_footprints.py
python hardware/pcb/tools/generate_kicad_schematic.py
python hardware/pcb/tools/generate_expected_connectivity.py
python hardware/pcb/tools/generate_bom.py
<kicad>/bin/python hardware/pcb/tools/generate_kicad_board.py --session hardware/pcb/kicad/controller.ses
python hardware/pcb/tools/electrical_checks.py
python hardware/pcb/tools/audit_connectivity.py
python hardware/pcb/tools/layout_audit.py
python hardware/pcb/tools/export_fabrication.py
python hardware/pcb/tools/release_readiness.py
```

The default command is a production-release gate and returns non-zero while
the PCB remains blocked. Use `--stage evt` for prototype-order gating or
`--stage structure` when you only need the repository engineering audit.

`kicad/controller.ses` is the checked Freerouting 2.3.0 routing session. The
board generator validates every footprint position against that session before
importing the checked routing branches. Deterministic cleanup and local
supplements preserve more than 1,000 segments while adding the U2/U7 and fixture-pad migration. A
stale session cannot silently attach to moved footprints.
Generated schematic UUIDs use a resettable deterministic sequence. Board output
UUIDs are normalized after KiCad saves the file, preserving repeated references
while removing run-to-run UUID noise; routing tie-breakers use stable reference,
pad, and coordinate keys rather than process memory addresses.

The layout audit hard-gates the Q36SR U2 input, return, `12V_ISO` source and
`GND` return with separate eight-via rings on 3 x 3, 1.5 mm-pitch grids around
the THT pads, along with nominal-width coverage and bounded package escapes.
The exact 20 A manufacturer revision, lifecycle, quote, heat-spreader and AVL
remain procurement and thermal gates. The audit also requires top-layer, zero-via
oscillator routing, matched CAN via counts, and an `In1.Cu` `GND_CAN_ISO` zone
declaration. NXF1 U7 has an all-eight-layer no-track/no-via/no-pour corridor
across its 4.08 mm board pad-edge gap; this does not satisfy the 8 mm system
target or replace Safety Owner review.
CAN coupling, branch/stub geometry, reference-plane continuity, and 120 ohm field
solving remain explicit manual or supplier risks rather than being inferred from
aggregate route lengths. The report now includes per-net graph metrics, declared
reference-zone endpoint coverage, reference-layer low-speed occupancy, oscillator
length delta and load-capacitor ground-via distance, plus every accepted power-net
neckdown. These measurements bound the review; they do not claim field-solved
impedance, uninterrupted filled copper, or thermal adequacy.

Test access is separated by electrical domain: TP1 remains in the 48 V primary
region, TP2-TP5/TP8 are on the logic side, and TP6/TP7 sit beside the isolated
CAN connectors. This keeps secondary probes out of the primary test area and
avoids long CAN test stubs.
`fixture-access-plan.csv` controls the additional safety, power-good, fault,
current-monitor, and domain-reference access required by the EVT fixture. Existing
connector access is cross-checked against `connector-pinout.csv`; TP9-TP15 are
implemented as dedicated pads while every row remains fail-closed until physical
fixture evidence is attached.

The checked-in ERC and DRC reports contain zero violations and zero unconnected
items. Gerbers, drills, IPC-D-356, position data, drawings, statistics, and a
rendered inspection preview are under `fabrication/`.
`kicad/controller.kicad_dru` enforces 8 mm copper clearance between the primary
48 V domain and every non-primary net; release readiness fails if this rule is
missing even when the base DRC report is otherwise clean.

## Critical design-review correction

The original task suggestion (`TPS54160 + RT8059 + AMS1117`) is not load-capable:

- TPS54160 is a 1.5 A regulator and cannot supply the proposed 12 V motor rail.
- RT8059 is a low-current converter and cannot supply a 5 V / 8 A Jetson rail.
- AMS1117 cannot provide 3.3 V / 5 A and would exceed its thermal limit.

The baseline therefore requires a protected 48 V input and an isolated,
regulated 36-60 V-to-12 V 240 W-class module, followed by a protected 12 V / 5 A
branch to the Jetson developer-kit DC
input, and a 12-to-3.3 V 20 W synchronous buck. It deliberately does not
back-power the developer kit through a 5 V header. Design candidates are listed
in the fabrication BOM; purchase requires all independent Electrical,
Procurement, Safety and other roles named in the approval registers. System
Owner authorization alone does not create an AVL.

U2 is the `Q36SR12020NRFH` design candidate. Distributor evidence identifies
18-75 V input, 12 V/20 A and 240 W, and the checked eight-pin footprint follows
the Q36SR family mechanical drawing. The local Delta PDF is for the 12 V/19 A
variant and cannot close exact 20 A procurement evidence. `DCM3623T50M31C2T00`
remains excluded by its 16-50 V input, 28 V output and incompatible package.

The board is a companion/control board for the NVIDIA developer kit, not a raw
260-pin Jetson module carrier. See `interface-control.md` and
`source-baseline.json` for controlled interfaces, official sources, assumptions,
owners, and freeze gates. J4 is populated on this board; J7-J9 describe downstream
harness or daughterboard endpoints and are not populated in revision A.
The ISO1042 bus side uses distinct `5V_CAN_ISO` and `GND_CAN_ISO` nets supplied
by U7; neither is tied to logic ground in the board database.
The populated J4 backplane carries the external `JETSON_ENABLE_REQ` on pin 8;
it is an MCU input and is deliberately distinct from the internal
`MOTOR_ENABLE_REQ` generated on U5 pin 53. The E-stop path has distinct
`MOTOR_ENABLE_REQ` and `MOTOR_ENABLE_SAFE` nets,
a dual-channel J10 loop, dual-channel manual reset at J12, diagnostic isolation
at U8, force-guided relay candidates K1/K2, and the J11 gated output.
`connector-pinout.csv` freezes the current EVT pin mapping.
`connectors.csv` separates contact capability from the controlled system
envelope: J2 contacts are a 16 A nominal interface, but the board and harness
are limited to 10 A aggregate (120 W at 12 V) until an external branch fuse,
inrush, regeneration and fault-current analysis is approved.
`component-selection-matrix.csv` tracks every active module, the source-backed
candidate or class, verification method, owner and procurement status.
Every matrix `source_id` must resolve to a complete HTTPS source entry in
`source-baseline.json`; excluded-source records are retained as history and may
not back a design candidate.
`fabrication/bom.csv` covers every board component and its grouped lines are
recomputed deterministically. `component-approval-register.csv` defines the
required approver roles for every procurement-controlled group.
`component-approval-signatures.csv`
contains one independent row per required role, bound to the EVT revision and
fabrication-BOM SHA-256. No group is approved until every role records an
orderable MPN, datasheet revision, identity, date, and evidence reference.
Changing a summary `decision` to `APPROVED` is insufficient.
`expected-connectivity.json` and `generated/connectivity_report.json` independently
check the physical pads across all 117 controlled components, plus input-protection, CAN
isolation, current-sense and dual-channel safety invariants.
`testpoint-coverage.csv` defines the measurement, limit, instrument and required
evidence for every physical test pad.
`fabrication/bringup-test-plan.csv` covers 36 V, 48 V, and 60 V operation, UV/OV,
reverse polarity, branch short, load and regeneration transients, E-stop
discrepancy, CAN FD, and a four-hour closed-enclosure thermal soak. These are
controlled test definitions, not completed physical evidence.

Run `python hardware/pcb/tools/release_readiness.py` before sharing an order
package. The checked-in schematic is component-level and has clean ERC. EVT
prototype ordering remains blocked by AVL, safety design, supplier DFM and U2/U7
external evidence. Physical bring-up,
measured safety timing, harness execution, and verified fixture access are
separate production-release gates so prototype evidence is not a circular EVT
ordering prerequisite.
The release audit fails closed if stale U2 placeholder or excluded-part markers
appear in controlled artifacts, and separately reports whether exact manufacturer
evidence and AVL have closed.
Do not order a populated board from engineering completeness alone.

## Release status

PCB1-11 have reproducible engineering evidence. PCB12-18 have complete order,
bring-up, reliability, and production procedures but still require physical boards,
lab instruments, EMC facilities, and production operators; see the verification
matrix for the evidence that must be attached rather than inferred.
