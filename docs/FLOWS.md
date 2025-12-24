# Multi-step flows

This section lists the required multi-step flows and the expected tool usage. Each flow ends with a short, factual response and optional follow-up question.

## Flow 1: medication facts + prescription requirement
1. User asks about a medication (name, typo, or mixed language).
2. Agent calls `resolve_medication_id` if needed.
3. Agent calls `get_medication_info` to fetch label facts.
4. Agent answers with prescription requirement plus concise label details.

## Flow 2: inventory availability + nearest pharmacy
1. User asks if a medication is in stock and requests a nearby pharmacy.
2. Agent resolves the medication name to an internal id.
3. Agent calls `check_stock` and returns availability only (no quantities).
4. Agent calls `find_nearest_pharmacy` with the provided city or zip.
5. Agent returns the nearest pharmacy details and asks if the user wants directions.

## Flow 3: user prescriptions (logged-in) + check stock
1. User asks about prescriptions.
2. Agent calls `get_user_prescriptions` with `active_only=true`.
3. Agent calls `check_stock`
4. Agent provides information about medication prescription (if there any)
   and provides information about availability.
5. If not logged in, agent asks the user to log in or provide a prescription id.

## Flow 4: handling and warnings (label only)
1. User asks how to use or store a medication.
2. Agent calls `get_medication_info` and `get_handling_warnings`.
3. Agent returns label usage instructions and handling warnings only.
