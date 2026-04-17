# SOP-DEV-001 — GMP Deviation Management Procedure
**Document ID:** SOP-DEV-001  
**Version:** 4.1  
**Effective Date:** 2025-09-01  
**Review Date:** 2026-09-01  
**Owner:** Quality Assurance Department  
**Site:** Plant-01, Pharmaceutical Manufacturing

---

## 1. Purpose

This Standard Operating Procedure defines the process for detecting, classifying, investigating, documenting, and closing GMP deviations at Plant-01. The procedure ensures compliance with GMP Annex 15, ICH Q10, and 21 CFR Part 211.

---

## 2. Scope

Applies to all manufacturing deviations including:
- Process parameter excursions (temperature, pressure, speed, flow rate)
- Equipment malfunctions and failures
- In-process test failures
- Environmental monitoring excursions
- Material deviations

---

## 3. Definitions

**Deviation:** Any departure from an approved procedure, specification, or standard.

**Minor Deviation:** Short duration excursion unlikely to affect product quality. Impact can be ruled out without additional testing. Example: temperature excursion < 2°C for < 2 minutes.

**Major Deviation:** Excursion with potential to affect product quality; requires investigation and risk assessment. Additional testing typically required.

**Critical Deviation:** Deviation that may have direct patient safety impact or significantly compromises GMP compliance. Immediate QA notification required. Batch rejection likely.

---

## 4. Deviation Classification

### 4.1 Automatic Classification Criteria

| Severity | Duration | Magnitude | Required Action |
|----------|----------|-----------|-----------------|
| Minor    | < 2 min  | < 5% outside limit | Record, justify, close |
| Major    | 2–30 min | 5–20% outside limit | Investigation, risk assessment, additional testing |
| Critical | > 30 min OR | > 20% outside limit | Immediate QA notification, potential batch reject |

### 4.2 Process Parameter Excursions — Granulation

For High-Shear Granulators (GR series):
- **Impeller Speed:** Critical for granule size distribution. Deviations > 10% below minimum for > 5 min require moisture and PSD testing.
- **Spray Rate:** Affects binder distribution. Low spray rate increases risk of ungranulated fines. Test granule distribution at 3 sampling points.
- **Inlet Air Temperature:** Controls product temperature and moisture evaporation. Excursions above upper limit risk thermal degradation of heat-sensitive APIs.
- **Product Temperature:** Monitor continuously. Exceeding upper limit by > 3°C for > 3 min requires risk assessment.

### 4.3 Equipment-Related Deviations

Equipment failures causing parameter excursions must be treated as Major or Critical deviations regardless of excursion duration:
1. Immediate: Notify maintenance team via CMMS
2. Equipment tagged out and quarantined
3. Batch held pending investigation
4. Bearing wear, motor failure, pump blockages: assess full production run impact
5. Calibration drift: review all batches since last confirmed calibration

---

## 5. Investigation Process

### 5.1 Immediate Response (within 30 minutes)
1. Document deviation in system (automatic via Sentinel Intelligence AI)
2. Assess immediate patient safety risk
3. Segregate/quarantine affected batch if critical risk
4. Notify QA on-call if Critical deviation

### 5.2 Root Cause Analysis (within 24 hours for Major, 4 hours for Critical)
Use 5-Why or Fishbone methodology:
- Review SCADA/DCS trending data for 4-hour window around event
- Check CMMS maintenance history for equipment
- Review operator batch record entries
- Compare with similar historical incidents
- Check environmental monitoring data (temperature, humidity, pressure)

### 5.3 CAPA Requirements

**For Minor deviations:** Trending review only; formal CAPA not required unless repetitive (same deviation 3×/quarter).

**For Major deviations:** CAPA required within 30 days:
- Corrective Action: address root cause
- Preventive Action: prevent recurrence
- Effectiveness check within 90 days

**For Critical deviations:** CAPA required within 7 days. Escalate to quality system for tracking.

---

## 6. Batch Disposition

After investigation and CAPA, QA assessment of batch disposition:

1. **Release:** Parameter excursion has no impact on quality attributes; additional testing confirms specification compliance.
2. **Conditional Release:** Product meets specifications after additional testing; CAPA must be in place.
3. **Reject/Destroy:** Impact on quality confirmed or cannot be ruled out.

Human approval by QA Manager required for all dispositions of Major and Critical deviations.

---

## 7. Documentation Requirements

All deviations must be documented in the QMS system with:
- Equipment ID and batch number
- Exact time, duration, and magnitude of deviation
- Detected parameter values and validated limits
- Immediate actions taken
- Root cause analysis
- CAPA actions with owners and due dates
- Batch disposition decision and justification
- Regulatory reference citations

Electronic records must comply with 21 CFR Part 11 requirements: audit trail, electronic signatures, and data integrity.

---

## 8. Regulatory References

- GMP Annex 15: Qualification and Validation
- ICH Q10: Pharmaceutical Quality System
- 21 CFR Part 211: Current Good Manufacturing Practice for Finished Pharmaceuticals
- 21 CFR Part 11: Electronic Records; Electronic Signatures
- EU GMP Chapter 3: Premises and Equipment
- EMA Guideline on Process Validation

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 4.1 | 2025-09-01 | O. Kovalenko | Updated §4.2 for granulator parameters |
| 4.0 | 2024-09-01 | O. Kovalenko | Added AI-assisted detection section |
| 3.2 | 2023-03-15 | M. Sydorenko | CAPA timeline updates |
