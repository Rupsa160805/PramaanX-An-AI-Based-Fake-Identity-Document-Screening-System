# PramaanX P4 demo script

This service uses synthetic/sample records and authorized team photos only.
It is decision support for an officer, not an automatic genuine/fake verdict.

## Before the demo

1. Start the service and verify `GET /api/health` returns `{"status":"ok"}`.
2. Set `P4_DATABASE_PATH` to the team's local reference store.
3. Put the team's authorized reference photos in the paths recorded by the
   reference store. Do not commit those photos.
4. Run threshold calibration under the actual counter lighting and record the
   chosen threshold in the evidence log.
5. Confirm that P2's `/api/analyze` can reach `POST /api/verify-face`.

## Suggested judging sequence

| Case | Input | Expected evidence |
|---|---|---|
| Clean pass | Genuine document + matching live face | database record found, high similarity, match, low overall risk |
| Tampered document | P3 synthetic tampered sample + matching face | P3 tamper signal raises overall risk; biometric may still match |
| Face mismatch | Genuine document + a different authorized team member | database record found, similarity below threshold, mismatch reason |
| Unknown document | document number absent from the reference store | `found_in_database: false`, no guessed similarity, graceful handling |
| No face | camera pointed away or blank image | `error: "no face detected"`, no guessed similarity, no 500 |

## Honest liveness wording

"Our MVP liveness check looks for motion across two or more frames and can
reject a completely static print. It is not a production anti-spoofing model;
a determined video replay could still defeat it. Production would require a
validated presentation-attack detector, consent, encrypted biometric
templates, retention/deletion controls, and legal authorization."

