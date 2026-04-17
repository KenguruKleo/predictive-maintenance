# SOP-MAN-GR-001 · High-Shear Granulator — Operation Procedure

**Document ID:** SOP-MAN-GR-001  
**Version:** 3.1  
**Effective Date:** 2025-09-01  
**Next Review:** 2026-09-01  
**Owner:** Manufacturing Operations  
**Equipment Applies To:** Glatt GPCG-60 (GR-204), and equivalent high-shear granulators  
**Associated SOPs:** SOP-DEV-001, SOP-CLN-GR-002, SOP-QA-001

---

## 1. Purpose

This SOP describes the step-by-step operation of the Glatt GPCG-60 High-Shear Granulator (GR-204) for wet granulation of oral solid dosage forms in compliance with GMP requirements (EU GMP Annex 15, 21 CFR Part 211).

---

## 2. Scope

Applies to all wet granulation operations performed on GR-204 (Building B, Room 204, Line 2) and any equivalent high-shear granulators at Plant-01.

---

## 3. Responsibilities

| Role | Responsibility |
|---|---|
| Production Operator | Execute granulation per this SOP and the applicable BPR |
| IPQA Officer | Verify in-process parameters and sign BPR |
| Supervisor | Authorize deviations from standard operation |

---

## 4. Equipment Description — Glatt GPCG-60

The Glatt GPCG-60 is a high-shear wet granulator with the following critical components:

- **Impeller:** Bottom-mounted, drives wet mass shear force. Validated speed range: **200–800 RPM**.
- **Chopper:** Side-mounted cutter to break agglomerates. Validated speed range: **1000–3000 RPM**.
- **Spray nozzle system:** Peristaltic pump delivers binder solution. Validated spray rate: **50–200 g/min**.
- **Inlet air system:** Provides temperature-controlled air for product drying during granulation. Validated range: **40–70 °C**.
- **Product bowl:** 60-liter working capacity. Product contact surface: 316L stainless steel.
- **Temperature and moisture sensors:** Continuous in-process monitoring.

### 4.1 Critical Process Parameters (CPPs)

| Parameter | Validated Range | Unit | Alarm Threshold |
|---|---|---|---|
| Impeller speed | 200 – 800 | RPM | <600 or >800 for >2 min triggers alert |
| Chopper speed | 1000 – 3000 | RPM | <1000 triggers alert |
| Spray rate | 50 – 200 | g/min | <45 or >210 triggers alert |
| Inlet air temperature | 40 – 70 | °C | >70 triggers immediate alert |
| Product temperature | 30 – 50 | °C | >50 triggers alert |
| Granulation time | Product-specific per BPR | min | Configurable per product |

> **Note:** Product-specific validated operating ranges may be narrower than the equipment validated range. Always refer to the applicable BPR for product-specific CPP limits.

---

## 5. Pre-Operation Checklist

Before starting any granulation batch, the operator shall verify and document in the BPR:

- [ ] GR-204 cleaning status verified (reviewed cleaning logbook and cleaning label)
- [ ] Previous batch residues absent (visual inspection of bowl, impeller, chopper, spray nozzle)
- [ ] Calibration status of all instruments valid (check calibration tags: impeller tachometer, inlet air thermocouple, spray rate sensor, product temperature probe)
- [ ] Room environmental conditions within limits: temperature ≤28°C, relative humidity ≤50% (log in BPR)
- [ ] Compressed air pressure confirmed ≥3.0 bar (check facility panel)
- [ ] All process parameters pre-set per BPR and verified by second operator
- [ ] SCADA monitoring screen active and alarmed

---

## 6. Operating Procedure

### 6.1 Equipment Start-Up

1. Power on GR-204 control panel. Confirm no active fault alarms.
2. Set impeller speed to pre-granulation speed as per BPR (typically 200–300 RPM for dry mixing).
3. Set chopper speed per BPR.
4. Start inlet air system. Allow 5 minutes for temperature stabilization before introducing product.
5. Verify inlet air temperature is within BPR range before proceeding.

### 6.2 Dry Mixing Phase

1. Charge dry ingredients into bowl per BPR dispensing order.
2. Close bowl lid. Confirm interlock engaged.
3. Start impeller at dry mixing speed (per BPR, typically 300–400 RPM).
4. Run dry mixing for time specified in BPR (typically 3–5 minutes).
5. IPQA to observe dry blend homogeneity at end of dry mixing step.

### 6.3 Wet Granulation — Binder Addition Phase

> **Critical Phase:** CPP excursions during binder addition have the highest impact on granule quality. Operator must monitor SCADA in real time during this phase.

1. Increase impeller speed to wet granulation setpoint per BPR (typically 600–700 RPM).
2. Start chopper at BPR-specified speed.
3. Start peristaltic pump at BPR-specified spray rate.
4. Begin binder addition. Note start time in BPR.
5. Monitor impeller speed, chopper speed, spray rate, and product temperature continuously.

**Parameter Excursion During Binder Addition:**
- Impeller speed deviation: refer to SOP-DEV-001 §4.2 immediately. Do not stop granulation unless directed by SOP-DEV-001 decision tree.
- Spray rate dropout >10%: stop pump, investigate nozzle blockage per §7.2 of this SOP.
- Inlet air temperature excursion: activate emergency cooling procedure (§6.5).

### 6.4 Endpoint Detection

Granulation endpoint is determined by:

- **Product temperature:** Shall reach target value specified in BPR (typically 35–42°C at endpoint)
- **Power consumption:** Monitored by SCADA. End-of-granulation signature is product-specific per BPR.
- **Granulation time:** Not to exceed BPR maximum. If endpoint not reached within BPR max time: raise deviation per SOP-DEV-001.
- **Visual check** (where specified by BPR): wet mass consistency check through bowl inspection port.

> **Important:** Granulation time beyond BPR product-specific maximum constitutes a deviation and shall be reported per SOP-DEV-001 §4.2, even if the equipment validated maximum (60 min) has not been reached.

### 6.5 Emergency Cooling Procedure

If product temperature exceeds BPR upper limit:
1. Immediately reduce inlet air temperature setpoint to 30°C.
2. Increase inlet air flow to maximum validated rate.
3. Document event in BPR and raise deviation per SOP-DEV-001.
4. Do not proceed to next step until product temperature returns to validated range.

---

## 7. Maintenance and Troubleshooting

### 7.1 Common Equipment Issues

| Symptom | Probable Cause | Action |
|---|---|---|
| Impeller speed below setpoint | Motor bearing wear, drive belt slip, power fluctuation | Stop if deviation; raise SOP-DEV-001; CMMS WO for inspection |
| Chopper speed below setpoint | Motor overload, bearing wear | Stop chopper; raise deviation; maintenance inspection |
| Spray rate low/dropout | Nozzle blockage, pump tubing wear | See §7.2 Spray System Troubleshooting |
| Inlet air temperature excursion | Heating element fault, thermocouple drift | Emergency cool (§6.5); raise deviation; CMMS WO |
| Unusual vibration | Bearing wear, imbalance | Stop immediately; quarantine equipment; CMMS WO |

### 7.2 Spray System Troubleshooting

If spray rate drops below BPR minimum:

1. Record exact time and measured spray rate in BPR.
2. Check pump tubing for visible blockage or wear.
3. If blockage suspected: stop spray, clear nozzle per cleaning procedure. Resume only if within granulation BPR time window.
4. If dropout >5 minutes and during binder addition: raise deviation per SOP-DEV-001 §4.3.
5. Inspect peristaltic pump tubing — replace if worn (PM interval: 30 days for high-viscosity binders).

### 7.3 Impeller Bearing — Predictive Maintenance Indicators

Early bearing wear presents as:
- Impeller speed 5–20 RPM below setpoint with consistent motor current increase
- Elevated vibration amplitude (>1.5× baseline triggers CMMS alert)
- Gradual motor current increase over consecutive batches (trend >8% over 3 batches)

> **Action:** If bearing wear pattern identified, raise CMMS PM work order immediately. Do not defer — bearing failure (as in INC-2026-0005) results in batch rejection and equipment quarantine.

---

## 8. Post-Granulation Steps

1. Stop binder addition pump.
2. Run impeller and chopper for post-granulation mixing time per BPR.
3. Stop impeller and chopper. Record end time and final granulation time in BPR.
4. Initiate drying phase per applicable BPR or transfer procedure.
5. Complete BPR sign-offs for all critical steps before releasing wet granules.

---

## 9. Deviation Management

All deviations from this SOP or from BPR-specified parameters must be:
1. Detected and documented immediately in the BPR.
2. Reported per **SOP-DEV-001 — Deviation Management**.
3. Assessed for batch impact before proceeding.

> Refer to **SOP-DEV-001 §4.2** for process parameter deviations and **SOP-DEV-001 §5.1** for equipment-related deviations.

---

## 10. Related Documents

| Document | Title |
|---|---|
| SOP-DEV-001 | Deviation Management |
| SOP-CLN-GR-002 | High-Shear Granulator Cleaning |
| SOP-QA-001 | Batch Production Record Completion |
| BPR-MET-500-v3.2 | Metformin HCl 500mg — Granulation BPR |
| BPR-ATV-020-v2.1 | Atorvastatin 20mg — Granulation BPR |
| GLATT-GPCG60 IQ/OQ | Installation and Operational Qualification Protocol |

---

## 11. Revision History

| Version | Date | Author | Change Summary |
|---|---|---|---|
| 1.0 | 2019-06-01 | Technical Operations | Initial issue |
| 2.0 | 2022-03-15 | Technical Operations | Added predictive maintenance indicators §7.3; updated spray system troubleshooting §7.2 |
| 3.0 | 2024-07-01 | Technical Operations | Aligned CPP limits with re-validation study results; added SCADA monitoring requirements |
| 3.1 | 2025-09-01 | Technical Operations | Added endpoint detection criteria §6.4; emergency cooling procedure §6.5 |
