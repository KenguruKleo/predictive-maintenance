# EU GMP Annex 15 — Process Validation and Deviation Management (Relevant Excerpts)

**Source:** EU Guidelines for Good Manufacturing Practice — Annex 15: Qualification and Validation  
**Version Referenced:** EudraLex Volume 4, Annex 15 (Revised 2015, consolidated 2022)  
**Excerpted Sections:** §6 (Process Validation), §8 (Continued Process Verification), §10 (Change Control), §12 (Cleaning Validation)

> **Note:** This document contains excerpts relevant to deviation management and process parameter excursions in oral solid dosage manufacturing. Full regulatory text: EudraLex Vol. 4 Annex 15.

---

## §6 — Process Validation

### §6.1 General Principles

Process validation shall establish scientific evidence that a manufacturing process, operating within established parameters, can effectively and reproducibly produce a medicinal product meeting its predetermined specifications and quality attributes.

**Critical Process Parameters (CPPs):** Process parameters whose variability has an impact on a Critical Quality Attribute (CQA) and therefore should be monitored or controlled to ensure the process produces the desired quality. CPPs must be defined during process development and documented in the validated range.

**Normal Operating Range (NOR) vs Proven Acceptable Range (PAR):**
- **Proven Acceptable Range (PAR):** The validated range within which a process parameter may be varied without adversely impacting product quality. Defined experimentally during validation.
- **Normal Operating Range (NOR):** The tighter, operational range used during routine manufacturing (subset of PAR). NOR is typically set in the BPR.
- An excursion from the NOR (but within PAR) requires deviation assessment but does not automatically result in batch rejection.
- An excursion from the PAR requires mandatory root cause investigation and batch disposition assessment per CAPA procedure.

> **Application to GR-204:** Impeller speed validated PAR: 200–800 RPM. Product-specific NOR may be set at 600–700 RPM in the BPR. An event at 585 RPM (below NOR, within PAR) requires deviation investigation (SOP-DEV-001) but batch rejection is not automatic — depends on duration, magnitude, and product-specific risk assessment.

### §6.3 — Process Parameter Deviations During Validation and Routine Manufacturing

When a process parameter excursion occurs during commercial manufacturing:

**6.3.1** The deviation shall be detected promptly — ideally in real time via SCADA monitoring — and documented with exact timestamps.

**6.3.2** The impact on product quality shall be assessed based on:
- Duration of excursion
- Magnitude of excursion relative to validated limits
- Product/API sensitivity to the affected parameter
- Stage of manufacturing at which the excursion occurred
- Historical precedent from similar events (if available)

**6.3.3** Where real-time data and historical analysis are insufficient for definitive root cause identification, additional in-process or end-product testing shall be performed before batch disposition.

**6.3.4** The outcome of the deviation investigation, the disposition decision, and supporting data shall be documented in the batch record and deviation management system.

**6.3.5** Repeated deviations of the same type shall trigger a formal CAPA process and may indicate the process is operating outside its validated design space.

---

## §8 — Continued Process Verification (CPV)

### §8.1 Objectives

Continued Process Verification provides ongoing assurance that the process remains in a state of control during routine commercial production. It requires:

- Systematic collection and statistical analysis of process data
- Identification of process variability and trends
- Detection of drifts toward out-of-specification conditions **before** deviations occur

### §8.2 Data Collection Requirements

The following data shall be collected for CPV purposes:
- All in-process measurements (CPPs and CQAs per BPR)
- All in-process test results
- All deviations, investigations, and CAPA outcomes
- Equipment condition monitoring data (where available)

### §8.3 Trending and Early Warning

Manufacturers should establish statistical process control (SPC) measures appropriate to the process. Trending analysis should identify:
- **Gradual drift:** Process parameter trending toward a limit over multiple batches — requires investigation before limit is actually breached.
- **Step change:** Sudden change in process parameter baseline — often equipment-related, requires immediate investigation.
- **Increased variability:** Widening of process parameter distribution — may indicate equipment wear or raw material variability.

> **Example application:** GR-204 impeller motor current increasing 8% over three consecutive batches (as occurred prior to INC-2026-0005) constitutes a CPV trending signal that should trigger CMMS preventive maintenance even before a speed deviation alarm occurs.

---

## §10 — Change Control and Corrective Actions

### §10.1 Scope of Change Control

Any change to the manufacturing process, equipment, raw materials, or procedures that could affect product quality must be subject to a formal change control procedure. This includes:
- Equipment replacement or major repair
- Changes to critical components (impeller, heating elements, sensors)
- Changes to validated process parameters
- Changes to manufacturing site or scale

### §10.2 Post-Deviation Change Assessment

Following a critical deviation (severity: major or critical), any corrective actions that modify the manufacturing process shall be implemented under change control. This includes:
- Repair or replacement of critical equipment components (e.g., bearing replacement)
- Modification of validated process parameter setpoints or ranges
- Changes to in-process monitoring frequency

**Requalification requirements after equipment repair:**
Following repair of critical equipment components, an Operational Qualification (OQ) or Performance Qualification (PQ) run may be required before return to production, depending on the extent of repair. This must be assessed on a risk basis:
- Bearing replacement on impeller shaft → OQ verification recommended
- Full motor replacement → full IQ/OQ required
- Thermocouple replacement → calibration + IQ check

---

## §12 — Cleaning Validation

### §12.1 General

Cleaning validation demonstrates that the cleaning procedure consistently removes residues of product, cleaning agents, and microbial contamination to below pre-defined acceptance limits, preventing cross-contamination between products and batches.

### §12.2 Acceptance Limits

Cleaning acceptance limits shall be based on:
- **10 ppm criterion:** Residue of any product in the next product ≤10 ppm (conservative standard)
- **0.1% therapeutic dose criterion:** No more than 0.1% of the minimum therapeutic daily dose of the previous product per maximum daily dose of the next product
- The more stringent of the two criteria applies

For equipment used in GMP oral solid dosage manufacturing (including GR-204), product-specific limits shall be calculated and documented in the cleaning validation protocol.

### §12.3 Visual Inspection

Visual inspection ("clean to sight") is required for all equipment between batches but does not replace validated cleaning procedures or analytical verification for product changeovers.

Equipment that fails visual inspection (visible residue) after the validated cleaning procedure shall be:
1. Re-cleaned per the validated procedure
2. Re-inspected
3. If residue persists: equipment quarantine and root cause investigation

---

## §15 — Glossary of Key Terms (Relevant Extracts)

| Term | Definition |
|---|---|
| **Critical Process Parameter (CPP)** | A process parameter whose variability has an impact on a CQA and therefore should be monitored or controlled to ensure the process produces the desired quality |
| **Critical Quality Attribute (CQA)** | A physical, chemical, biological, or microbiological property or characteristic that should be within an appropriate limit, range, or distribution to ensure the desired product quality |
| **Deviation** | A departure from an approved instruction or established standard |
| **CAPA** | Corrective Action and Preventive Action — the system for investigating deviations, identifying root causes, and implementing corrections to prevent recurrence |
| **Proven Acceptable Range (PAR)** | The characterized range of a process parameter for which operation within this range, while keeping all other parameters constant, will result in producing a material meeting relevant quality criteria |
| **Out-of-Specification (OOS)** | A result for a finished product, in-process test, or raw material that falls outside the specifications established in the approval or official compendia |
| **Out-of-Trend (OOT)** | A result that, while within specification, indicates a potential trend toward OOS — requires investigation |
