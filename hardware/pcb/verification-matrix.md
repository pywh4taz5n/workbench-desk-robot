# PCB verification matrix

| Task | Evidence | Status / gate |
|---|---|---|
| PCB1 | KiCad project, 117-symbol detailed schematic, routed EVT carrier, ERC report | ENGINEERING COMPLETE; component and safety approvals remain order gates |
| PCB2 | electrical spec, generated report, candidate BOM, Q36SR distributor and family-mechanical evidence | DESIGN CANDIDATE IMPLEMENTED; exact 20 A manufacturer datasheet, lifecycle, quote, heat-spreader review and AVL remain blocked |
| PCB3 | 5 kVrms isolated CAN FD, U6 8.1 mm and NXF1 U7 4.08 mm full-layer barriers, choke/TVS/termination plan | BLOCKED: U7 does not meet the 8 mm system target; safety suitability and surge test remain external |
| PCB4 | fuse, reverse protection, hot-swap UV/OV/inrush, E-stop sequence | DESIGN COMPLETE; bench trip-time test pending |
| PCB5 | `connectors.csv`, `connector-pinout.csv`, request/safe enable separation | EVT INTERFACE BASELINE COMPLETE; owner pin-mux sign-off required |
| PCB6 | eight-layer 160 x 130 mm board, 121 footprints, more than 1,300 track/via items, 31 copper zones, 15 SMT test pads, Gerber/drill/IPC-D-356 | DRC AND LAYOUT HARD GATES PASS; supplier DFM and manual PI/thermal review remain open |
| PCB7 | 84-line grouped BOM, approval register and signed AVL/CTO gate | BLOCKED: independent role approvals remain incomplete; only authorized System Owner rows may be signed internally |
| PCB8 | CAN rules, matched RAW blind-via transitions, graph metrics, reference-zone endpoint coverage, zero-via field routes and open-risk audit | DESIGN COMPLETE; uncovered reference bounds, coupling/stub review and fabricator impedance coupon remain open |
| PCB9 | thermal plan and acceptance limits | ANALYTICAL; exact U2 heat-spreader/derating data and chamber evidence remain required |
| PCB10 | pre-compliance plan | COMPLETE; lab scan required |
| PCB11 | fabrication directory with Gerber, drill, BOM, positions and drawings | COMPLETE |
| PCB12 | order package, DFM response fields and automated release audit | NOT ORDER READY; U2 exact manufacturer/AVL evidence plus independent procurement, supplier and safety gates remain open |
| PCB13 | 36/48/60 V rails, UV/OV/reverse/short/transient, E-stop/CAN captures, four-hour soak and controlled fixture-access plan | DESIGN ACCESS COMPLETE: TP9-TP15 implemented; assembled-prototype and fixture evidence required |
| PCB14 | pre-certification/certification report | HOLD: accredited lab required |
| PCB15 | signed ECN and production Gerbers | HOLD: PCB12-14 closure required |
| PCB16 | 20 assembled boards and AOI/X-ray record | HOLD: production required |
| PCB17 | temperature-cycle and vibration report | HOLD: test facilities required |
| PCB18 | controlled assembly, test, rework and evidence process | COMPLETE |
