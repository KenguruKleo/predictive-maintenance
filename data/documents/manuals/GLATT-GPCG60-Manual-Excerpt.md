# GLATT GPCG-60 — Technical Manual Excerpt

**Document Reference:** GLATT-GPCG60-MAN-EN-v4.2  
**Equipment:** Glatt GPCG-60 High-Shear Granulator / Fluid Bed Processor  
**Serial Number Applies To:** GR-204 (GLATT-2019-GR204), Plant-01 Building-B Room-204  
**Manufacturer:** Glatt GmbH, Binzen, Germany  
**Extracted Sections:** Chapter 3 (Technical Specifications), Chapter 6 (Alarm and Fault Codes), Chapter 8 (Predictive Maintenance)

> **Note:** This is an excerpt for AI knowledge base purposes. Full manual reference: GLATT-GPCG60-MAN-EN-v4.2.

---

## Chapter 3 — Technical Specifications

### 3.1 Drive System

The Glatt GPCG-60 uses a frequency-controlled (VFD) drive system for both the impeller and chopper, allowing precise speed regulation across the full validated range.

**Impeller Drive:**
- Drive type: Frequency-controlled AC motor
- Rated power: 22 kW
- Speed range: 100–1200 RPM (full mechanical range), validated for pharmaceutical use: 200–800 RPM
- Speed regulation accuracy: ±5 RPM under normal load
- Motor current nominal: 42 A at 600 RPM typical operating point
- **Motor current threshold:** Current draw >10% above running baseline indicates increased mechanical resistance. Current draw >20% above baseline for >5 minutes is indicative of bearing deterioration — initiate CMMS inspection.
- Torque monitoring: Software-calculated from VFD current draw. Available via ServoStar interface.

**Chopper Drive:**
- Drive type: Direct-drive high-speed motor
- Speed range: 500–4000 RPM (full range), validated: 1000–3000 RPM
- Rated power: 3 kW

### 3.2 Spray System

The GPCG-60 uses a top-spray peristaltic pump delivery system.

- **Pump type:** Peristaltic, dual-head
- **Flow rate range:** 10–400 g/min
- **Validated pharmaceutical range:** 50–200 g/min
- **Nozzle type:** 2-fluid spray nozzle (solution + atomizing air)
- **Atomizing air pressure:** 1.5–3.0 bar
- **Nozzle filter:** 100-mesh inline filter. **Replacement interval:** 30 days for aqueous binders; 15 days for high-viscosity or suspended-particle binders.
- **Tubing wear:** Peristaltic tubing shall be replaced every 200 operating hours or at visible signs of crack/deformation. Degraded tubing causes progressive spray rate drift (typically starts as ±5% then worsens to ±15%).

### 3.3 Temperature Control System

- **Inlet air heating:** PID-controlled resistance heater
- **Inlet air temperature range:** Ambient to 120°C (validated pharmaceutical: 40–70°C)
- **Temperature sensor type:** PT-100 thermocouple, dual-redundant
- **Thermocouple calibration interval:** 6 months. Drift beyond ±1.5°C requires recalibration.
- **PID controller overshoot characteristics:** Standard PID tuning may result in 2–4°C overshoot during set-point step changes >10°C. For temperature-sensitive processes, use ramp-rate limiting (configurable in SCADA interface).

### 3.4 Vibration Monitoring (Optional, installed on GR-204)

GR-204 is equipped with the optional Glatt SmartMonitor vibration module:
- **Sensor locations:** Impeller shaft bearing (primary), chopper shaft bearing
- **Measurement:** RMS vibration amplitude, mm/s
- **Baseline establishment:** Measured during IQ/OQ. Recorded in qualification protocol.
- **Alarm thresholds:** Configurable. Recommended Glatt default: alarm at 1.5× baseline, emergency stop at 3.0× baseline.
- **Bearing wear signature:** Progressive increase in vibration amplitude over consecutive batches is characteristic of bearing race degradation. A 10% per-week increase in vibration RMS, sustained over 2+ weeks, should trigger CMMS inspection before threshold alarm.

---

## Chapter 6 — Alarm and Fault Codes (GR-204 SCADA Integration)

| Fault Code | Description | Risk Level | Required Action |
|---|---|---|---|
| ALM-001 | Impeller speed below setpoint >10 RPM for >30 sec | MEDIUM | Check motor load; if persists, raise deviation SOP-DEV-001 |
| ALM-002 | Impeller speed below setpoint >30 RPM | HIGH | Stop batch evaluation; raise deviation immediately |
| ALM-003 | Chopper speed below setpoint >100 RPM | HIGH | Stop chopper; raise deviation |
| ALM-004 | Spray rate deviation >15% from setpoint | MEDIUM | Check nozzle and tubing; see SOP-MAN-GR-001 §7.2 |
| ALM-005 | Spray rate dropout (>80% loss) | HIGH | Stop pump; raise deviation |
| ALM-006 | Inlet air temperature >validated upper limit | CRITICAL | Activate emergency cool; raise deviation immediately |
| ALM-007 | Product temperature >validated upper limit | HIGH | Reduce inlet air temp; raise deviation |
| ALM-008 | Motor current >115% nominal | HIGH | Reduce load; inspect drive coupling |
| ALM-009 | Motor current >130% nominal | CRITICAL | Stop equipment immediately; raise CMMS emergency WO |
| ALM-010 | Vibration >1.5× baseline | HIGH | Evaluate bearing condition; schedule CMMS inspection within 24h |
| ALM-011 | Vibration >3.0× baseline | CRITICAL | Emergency stop; quarantine equipment; CMMS emergency WO |
| ALM-012 | Compressed air pressure <2.5 bar | MEDIUM | Notify facilities; do not start new batch |
| ALM-013 | Compressed air pressure <1.5 bar | CRITICAL | Stop spray system; evaluate batch integrity |

---

## Chapter 8 — Predictive Maintenance

### 8.1 Impeller Bearing — Condition Monitoring

The impeller bearing is the primary wear component in the GPCG-60 drive train. Failure to replace bearings on schedule is the most common cause of impeller speed deviation deviations in high-shear granulators.

**Standard PM interval:** 12 months or 500 operating hours, whichever is earlier.

**Predictive indicators to track between PM intervals:**

1. **Motor current trending:** Record peak motor current at standard operating point (600 RPM, 50% product load) at start of each batch. A sustained upward trend (>5% per month) indicates bearing wear.
2. **Speed regulation error:** At steady-state 600 RPM, the VFD corrects for load. Increasing correction signal (available from VFD diagnostic log) indicates increasing resistance.
3. **Vibration amplitude (if SmartMonitor installed):** Weekly trend plot. Bearing failure typically shows exponential increase in final 2–4 weeks before failure.
4. **Unusual noise:** Grinding or intermittent clicking during impeller rotation constitutes an immediate stop signal — do not defer.

**Bearing replacement procedure:** Requires full bowl disassembly. Estimated downtime: 4 hours. Always replace both primary and secondary bearings simultaneously. After replacement: run IQ/OQ verification before return to production service.

### 8.2 Spray Nozzle and Pump Tubing

- Peristaltic tubing: inspect visually at each PM. Cracks, hardening, or <1mm wall thickness → replace immediately.
- Spray nozzle 100-mesh filter: replace on interval (see §3.2). Partial blockages cause progressive spray rate drift that may not trigger alarms until >15% deviation.
- Atomizing air connection: check for blockage quarterly. Partial blockage causes droplet size increase and non-uniform binder distribution.

### 8.3 Thermocouple Calibration

- Calibrate every 6 months per calibration SOP.
- Known failure mode: gradual positive drift (reads lower than actual temperature). A +2°C drift will mask a genuine temperature excursion — actual product temperature may be 2°C higher than displayed.
- If two consecutive calibrations show drift >1°C in same direction: replace sensor, do not simply recalibrate.

### 8.4 Preventive Maintenance Schedule Summary

| Component | Interval | Type |
|---|---|---|
| Impeller bearings | 12 months / 500 hr | Replace |
| Chopper bearings | 18 months | Replace |
| Peristaltic pump tubing | 200 hr or 30 days | Replace |
| Inlet air temperature sensor | 6 months | Calibrate |
| Spray rate sensor | 6 months | Calibrate |
| Vibration sensor (SmartMonitor) | 12 months | Calibrate |
| Impeller seal | 12 months | Inspect + replace if worn |
| Drive belt (if equipped) | 6 months | Inspect; replace if wear >15% |
