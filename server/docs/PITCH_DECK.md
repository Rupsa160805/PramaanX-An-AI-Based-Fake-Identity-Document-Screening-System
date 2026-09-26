# Pitch deck outline — PramaanX

## 1. The problem

Identity-document review is slow, inconsistent, and vulnerable to genuine
documents presented by the wrong person. Officers need evidence they can
inspect, not a black-box verdict.

## 2. The innovation

PramaanX fuses independent evidence: OCR/MRZ consistency, reference-record
cross-check, image tampering signals, and live-face verification against the
database's original reference photo. Every signal carries a reason.

## 3. Architecture

```text
React officer dashboard
          |
       P2 Flask API  ---- P3 document analysis
          |
       P4 Flask biometric service
          |-- /api/capture (webcam)
          |-- /api/verify-face (reference photo + live face)
          `-- /api/liveness-check (basic motion MVP)
```

P4 is isolated so a camera/model failure can degrade to an explainable
"face verification unavailable" state without taking down document analysis.

## 4. Live demo

Show one clean match, one tampered document, one face mismatch, and one
unknown document. Point to the returned reason and the stable JSON contract,
not just the final color on the dashboard.

## 5. What we would add for production

Validated anti-spoofing and calibration on representative data; encrypted
biometric templates; explicit consent and deletion/retention controls; access
auditing; secure deployment; monitoring; and legal/privacy review. The
prototype uses synthetic/sample identity records and is not connected to
government databases.

