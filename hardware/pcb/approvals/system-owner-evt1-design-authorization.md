# EVT1 System Owner design authorization

Date: 2026-08-25

Authorizing owner: Quchaosheng, System Owner

Source: Codex task `01a01485-08ce-7dd0-9615-6a511aba18f9`. The owner stated that
the PCB is their own design and explicitly requested that the repository-side
approval and design optimization work be completed.

## Authorized scope

- Approve the System Owner role for the J1 and J3 system connector selections
  at the exact EVT1 BOM hash recorded in `component-approval-signatures.csv`.
- Authorize the repository ECO that replaces the U2 and U7 design placeholders
  and adds TP9 through TP15, provided all engineering checks remain fail-closed.
- Preserve the existing 36-60 V system input, 12 V Jetson interface, and
  controlled connector envelopes.

## Excluded scope

This record is not an Electrical Owner calculation, Procurement Owner AVL or
quote approval, Safety Owner determination, supplier DFM response, harness
release, or physical bring-up result. Those independent roles and evidence
remain required.
