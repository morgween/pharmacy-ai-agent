# Evaluation plan

This plan validates tool usage, policy adherence, and multilingual behavior against the assignment goals.

## Scope
- Streaming stability and tool-call tracing
- Factual medication answers and prescription requirements
- Inventory availability and pharmacy lookup
- Prescription workflows for logged-in users
- Safety guard behavior across languages

## Test matrix
1. Medication facts: ask for a known medication by name and verify label fields.
2. Prescription requirement: verify correct yes/no and no medical advice.
3. Inventory: check a known medication and confirm boolean availability only.
4. Pharmacy lookup: city hit and city miss with nearest-city fallback.
5. Prescriptions: logged-in user list and not-logged-in refusal.
6. Handling warnings: verify label-only warnings without advice.
7. Multilingual: run each flow in hebrew and english; spot-check russian/arabic.

## Acceptance criteria
- Correct tool selection with valid arguments.
- No hallucinated tools or unsupported actions.
- No medical advice, diagnosis, or promotional language.
- Streaming completes with a single final assistant response.
- Tool trace shows right tools usage.

## Evidence
- Capture 2-3 screenshots per flow.
- Record failed cases and fixes in a short changelog note.
