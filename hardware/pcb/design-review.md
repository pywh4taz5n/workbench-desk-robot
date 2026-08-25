# Electrical design review

## Architecture and protection sequence

```text
48 V battery
  -> 10 A fuse -> reverse-polarity MOSFET -> 58 V TVS
  -> hot-swap/inrush controller (UV 34 V, OV 62 V, 8 A limit)
  -> Q36SR12020NRFH 18-75 V-to-12 V / 20 A isolated design candidate
       -> protected 12 V motor auxiliary output
       -> protected 12 V / 5 A branch -> Jetson developer-kit DC input
       -> 3.3 V / 5 A synchronous buck -> MCU, sensors, isolated CAN logic

CH32V307 <-> reinforced digital isolation <-> CAN FD transceiver
Dual-channel E-stop + manual reset -> K1/K2 force-guided relay candidates
  -> MOTOR_ENABLE_SAFE; U8 provides isolated channel diagnostics only
MCU supplies MOTOR_ENABLE_REQ and observes state but cannot bypass K1/K2
```

Power-good sequencing is `12V_ISO` then `JETSON_12V` then `3V3_LOGIC` with 10 ms
minimum spacing. The design target is for any input UV/OV, hot-swap fault,
channel discrepancy, or E-stop assertion to disable `MOTOR_ENABLE_SAFE` within
1 ms while logic rails remain up; instrumented trip-time evidence is still required.
Recovery from E-stop requires loop restoration plus a separate physical reset.
U8 remains an interface carrier: order release is blocked until the Safety Owner
freezes the safety architecture, diagnostic coverage, reset circuit, implementation,
and failure-mode analysis.

U2 is implemented as the `Q36SR12020NRFH` design candidate with the Q36SR
eight-pin quarter-brick family land pattern. Authorized-distributor records list
18-75 V input, 12 V/20 A and 240 W. The local Delta manufacturer PDF is for the
12 V/19 A family variant, so it is mechanical-family evidence rather than the
exact 20 A electrical release source. Exact manufacturer revision, lifecycle,
authorized-channel quote, heat-spreader choice and AVL remain procurement gates.
`DCM3623T50M31C2T00` remains excluded by its 16-50 V input, 28 V output and
incompatible nine-terminal package.

## Signal integrity and grounding

- The eight-layer stack assigns L2/In1 and L5/In4 to ground-reference and
  low-speed routing duties. L7/In6 carries controlled logic and safety signals;
  L3/In2, L4/In3, and L6/In5 carry separated primary, protected-Jetson, logic,
  and isolated-CAN power distribution plus routed escape segments. The released
  Gerbers, rather than a generic layer label, are the source of truth for copper.
- CAN targets 120 ohm differential. `CANH_RAW/CANL_RAW` are top-layer,
  point-to-point routes using two matched F.Cu-to-In3.Cu blind vias per net,
  measuring 12.210/13.942 mm (1.732 mm aggregate delta). The field-side
  `CANH/CANL` trees are top-layer and zero-via, with 72.352/72.073 mm aggregate
  totals (0.279 mm delta); both
  nets branch to two connectors, protection, termination, and testpoints.
- The isolated CAN corridor declares an adjacent `GND_CAN_ISO` zone on `In1.Cu`.
  Pair coupling, stub geometry, branch correspondence, reference-plane
  continuity, supplier field solving, and an impedance coupon remain release gates.
- SPI series-termination footprints are populated; return-path geometry must be
  reviewed against the released Gerbers and the supplier's final stackup.
- The custom DRC rules enforce 8 mm copper clearance between primary and
  secondary domains. Finished-board creepage and contamination class still
  require supplier and safety review.
- U7 is `NXF1S0305MC-R7`, a regulated 3.3 V-input to 5 V/200 mA, 1 W SMD
  module documented by KDC_NXF1.C01. Its implemented logic/field pad-edge gap
  is 4.08 mm and is protected by an all-eight-layer no-track/no-via/no-pour
  rule area. Component dielectric test voltage and board geometry do not by
  themselves close the 8 mm system target; Safety Owner review remains open.

Controlled impedance values must be recalculated from the selected fabricator's
actual dielectric table. No generic trace width is released as an impedance guarantee.

## Thermal plan

The 15 W, 25 W and conservative 40 W Jetson load cases are external to this board;
the protected 12 V branch and harness are screened at 5 A continuous. The Jetson
thermal solution conducts to the chassis and is validated separately from the PCB.
Power distribution uses 2 oz copper on L1/L3/L6/L8. The implemented Q36SR
candidate has separate eight-via rings on 3 x 3, 1.5 mm-pitch grids around its
input, input-return, output and output-return transfer pads, using 0.8 mm vias
with 0.4 mm drills and nominal-width current-sharing spokes. This geometry and
the passing neckdown audit establish the checked current-transfer layout, not
thermal adequacy or the exact 20 A module revision. Heat-spreader selection,
airflow/derating, copper-area adequacy and supplier process remain review items.
Thermal acceptance is converter
junction below 110 C and Jetson module below 80 C at 35 C ambient, measured with
the production enclosure closed.

U3's exposed pad has a 3 x 3, 0.4 mm-pitch array of 0.45/0.15 mm F.Cu-to-In1.Cu
laser microvias, offset 0.25 mm from pad center to clear the PGTH route. Its 5 A
output uses four parallel 0.8/0.4 mm plated through vias into the In3.Cu Jetson
plane. Laser-via fill, cap, planarization, registration, stencil aperture, and
voiding controls remain a supplier DFM gate rather than a DRC inference.

## EMI pre-compliance

- The CAN common-mode choke and TVS are placed before the field connectors.
- Any input-filter change driven by LISN data requires an ECO and renewed DRC/thermal review.
- Keep switch-node copper on L1, minimal, with its return directly below on L2.
- Any spread-spectrum mode is allowed only after CAN and power-rail noise comparison.
- Pre-scan conducted emissions 150 kHz-30 MHz and radiated emissions 30 MHz-1 GHz.
- Test ESD at accessible connectors and EFT/burst on the battery input before certification.

## Fabrication and assembly release checklist

1. KiCad ERC has zero errors; all waivers are signed and included.
2. DRC uses 0.15 mm trace/space, 0.30 mm finished drill, 0.15 mm annular ring, and 8 mm barrier creepage.
3. Plot Gerber X2, Excellon PTH/NPTH, IPC-356 netlist, drill map, stackup, fab drawing, and board PDF.
4. Export BOM with manufacturer part numbers and AVL state; no `HOLD` line may be ordered.
5. Export centroid, assembly drawings, paste layers, and polarity drawing.
6. Independently compare Gerber-to-PCB nets and inspect all planes, clearances, labels, and pin 1 marks.
7. Obtain the exact Q36SR12020NRFH manufacturer datasheet, lifecycle and quote evidence; approve its heat-spreader/thermal plan and AVL before ordering.
