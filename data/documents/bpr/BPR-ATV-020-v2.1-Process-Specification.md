# BPR-ATV-020-v2.1 · Atorvastatin Calcium 20mg Tablets — Master Batch Process Specification

**Document ID:** BPR-ATV-020-v2.1  
**Product Name:** Atorvastatin Calcium 20mg Film-Coated Tablets  
**Product Code:** ATV-020-TAB  
**Batch Size:** 150 kg (standard)  
**Document Type:** Master Batch Production Record — Process Specification  
**Version:** 2.1 | **Effective Date:** 2025-03-15 | **Next Review:** 2027-03-15  
**Owner:** Technical Operations / Process Development  
**Associated Equipment:** GR-204 (Granulation), DRY-303 (Drying), MIX-102 (Blending)  
**Associated SOPs:** SOP-MAN-GR-001, SOP-MAN-DRY-001, SOP-DEV-001

---

## 1. Product Overview

Atorvastatin Calcium is an HMG-CoA reductase inhibitor (statin) used for dyslipidemia management. The API is slightly hygroscopic, practically insoluble in water, and thermally sensitive above 60°C (risk of lactonisation above 65°C in presence of moisture). The 20mg dose requires precise blend uniformity due to the low drug load (approximately 13.4% w/w in the final blend).

**Critical Quality Attributes (CQAs):**
- Content uniformity (target: 98–102%; limit: 92–108%) — **critical due to low drug load**
- Dissolution: Q = 70% at 30 min, USP Apparatus II, 75 rpm, 900 mL phosphate buffer pH 6.8
- Related substances (API degradation): atorvastatin lactone ≤0.2%; any individual impurity ≤0.1%
- Moisture content of granules: 1.0–2.5% (critical — moisture accelerates lactonisation)
- Particle Size Distribution post-drying: D50 300–420 µm

**API Properties relevant to processing:**
- Thermal sensitivity: at temperatures >65°C and moisture >3%, lactonisation rate increases significantly. Drying must not exceed product temperature 42°C.
- Low drug load: granulation homogeneity is a critical concern — impeller speed and granulation time directly impact content uniformity.
- Photosensitive: protect from light during processing; batch hold time in open vessels ≤4 hours under normal lighting.

---

## 2. Manufacturing Flow

```
Dispensing → Sieving (API + intragranular excipients)
           → Dry Mixing (GR-204) → Wet Granulation (GR-204)
           → Drying (DRY-303) → Milling → Final Blending (MIX-102)
           → Compression → Film Coating → Packaging
```

---

## 3. Stage 1 — Wet Granulation on GR-204

### 3.1 Materials

| Material | Role | Quantity (150 kg batch) |
|---|---|---|
| Atorvastatin Calcium | API | 21.8 kg (equivalent to 20.0 kg atorvastatin) |
| Calcium Carbonate | Stabiliser / Diluent | 30.0 kg |
| Lactose Monohydrate | Diluent | 52.0 kg |
| Microcrystalline Cellulose PH102 | Diluent / Binder | 24.0 kg |
| Croscarmellose Sodium | Disintegrant (intragranular) | 6.0 kg |
| Hydroxypropyl Cellulose LF (binder) | Binder | 4.5 kg |
| Purified Water | Binder solvent | 22.0 kg |

> **Note on Calcium Carbonate:** Alkaline excipient included to maintain microenvironmental pH, inhibiting lactonisation. Do not substitute without formal change control.

### 3.2 Product-Specific Critical Process Parameters — Wet Granulation

> These are **product-specific validated operating ranges** (NOR/PAR). They are narrower than the equipment validated range stated in SOP-MAN-GR-001 §4.1. In case of conflict, **these product-specific limits take precedence** for this product.

| Parameter | Product NOR | Product PAR | Equipment Validated Range | Unit |
|---|---|---|---|---|
| Impeller speed — dry mix | 300 ± 50 | 200–400 | 200–800 | RPM |
| Impeller speed — wet granulation | **650 ± 30** | **580–730** | 200–800 | RPM |
| Chopper speed | 2250 ± 150 | 2000–2500 | 1000–3000 | RPM |
| Spray rate | **88 ± 12** | **72–105** | 50–200 | g/min |
| Inlet air temperature | 52 ± 4 | 46–58 | 40–70 | °C |
| Product temperature during granulation | 37 ± 3 | 32–42 | 30–50 | °C |
| Product temperature (absolute max) | — | **≤42** | ≤50 | °C |
| Binder addition time | 16 ± 2 | 12–22 | — | min |
| Post-addition mixing time | 5 ± 1 | 3–8 | — | min |
| Total granulation time | **22 ± 4** | **16–28** | 5–60 | min |

> ⚠️ **Deviation trigger (product temperature):** Product temperature exceeding **42°C** during any granulation phase constitutes a **major deviation** due to lactonisation risk. Immediate action: reduce inlet air temperature; notify QA immediately. If >45°C for >2 minutes: batch hold, enhanced related substances testing required.

> ⚠️ **Deviation trigger (impeller speed):** Impeller speed below **580 RPM** for >3 minutes during wet granulation: minor deviation if 560–579 RPM; major deviation if <560 RPM. Low impeller speed with atorvastatin formulation risks inadequate distribution of the API at low drug load → content uniformity failure.

> ⚠️ **Granulation time:** Exceeding **28 min** total granulation time is a major deviation. Risk: API thermal stress accumulation + over-granulation → poor dissolution profile and potential content uniformity issues.

### 3.3 In-Process Controls — Granulation

| Test | Specification | Frequency | Action if OOS |
|---|---|---|---|
| Product temperature | ≤42°C (absolute) | Continuous | If >42°C: immediate action per above |
| SCADA parameter log | All CPPs within NOR | Continuous | Deviation per SOP-DEV-001 |
| Wet granule visual | Uniform wet mass, no visible API agglomerates | End of binder addition | Extend mix 2–3 min, inspect again |
| Granulation time | 16–28 min | At endpoint call | If >28 min: hold, QA notification |

---

## 4. Stage 2 — Drying on DRY-303

### 4.1 Product-Specific Critical Process Parameters — Drying

| Parameter | Product NOR | Product PAR | Unit | Rationale |
|---|---|---|---|---|
| Inlet air temperature | 60 ± 4 | 54–65 | °C | Balances drying efficiency vs. lactonisation risk |
| Product temperature (max) | 38 (target) | ≤**42** | °C | Thermal stability limit for atorvastatin |
| Air flow rate | 850 ± 100 | 700–1000 | m³/h | |
| Drying time (standard) | 75 ± 10 | 55–100 | min | |
| Moisture endpoint | **1.0–2.5%** (target 1.5%) | ≤3.0% | %w/w | Above 3%: lactonisation risk; below 1%: brittle granules |

> ⚠️ **Critical drying endpoint:** Unlike most products, atorvastatin granules have both an **upper** (≤3.0%) **and lower** (≥0.5% functional limit) moisture boundary. Over-drying below 1.0% NOR limit produces brittle granules that over-fragment during milling, leading to dissolution deceleration. If LOD <1.0%: stop drying immediately, cool bed, measure equilibrium moisture.

> ⚠️ **Product temperature during drying:** This is the **most critical parameter** for this product. Inlet air temperature must be reduced to 54°C (PAR lower bound) if product temperature approaches 40°C. Do not exceed 42°C at any time during drying.

### 4.2 In-Process Controls — Drying

| Test | Specification | Timing | Action if OOS |
|---|---|---|---|
| Moisture — intermediate | 3–8% | At 45 min | If >8%: normal, extend; if <3%: reduce inlet temp to 54°C immediately |
| Product temperature | ≤42°C | Continuous | Reduce inlet temp; deviation report if exceeded |
| Moisture — endpoint | **1.0–2.5%** | At standard endpoint | If >2.5%: extend 15 min; if <1.0%: over-dried — hold |

### 4.3 Post-Drying Granule Release Tests

| Test | Specification | Method |
|---|---|---|
| Moisture content (LOD) | 1.0–2.5% | LOD, 80°C, 5 min (thermostable method) |
| Related substances (atorvastatin lactone) | Lactone ≤0.10% (in-process limit; tighter than final) | HPLC-UV |
| Bulk density | 0.38–0.52 g/mL | USP method |
| Particle size: D50 | 300–420 µm | Laser diffraction |

---

## 5. Stage 3 — Final Blending on MIX-102

| Parameter | Product NOR | Product PAR | Unit |
|---|---|---|---|
| Blending speed — main blend | 75 ± 10 | 60–90 | RPM |
| Blending time — main blend | 20 ± 3 | 15–26 | min |
| Temperature | ≤28°C | ≤30°C | °C |
| Relative humidity (blend room) | 30–50% | 20–55% | % |

> Lubrication blend (magnesium stearate): 55 RPM, 3 min ± 30 s. Exceeding 5 min lubrication time constitutes a deviation — risk of over-lubrication → reduced tablet hardness and dissolution.

---

## 6. Batch Disposition Framework

| Scenario | Classification | Disposition |
|---|---|---|
| All CPPs within NOR, all IPTs pass | Normal | Release |
| Product temperature 42–44°C, <2 min, lactone IPT pass | Major deviation | Release with enhanced related substances testing + QA approval |
| Product temperature >44°C or >2 min above 42°C | Critical deviation | Batch hold — full related substances panel required |
| Moisture endpoint >3.0% (over PAR) | Major deviation | Hold; extended drying requires QA approval |
| Moisture endpoint <0.5% (over-drying) | Major deviation | Compression performance study required before release |
| Impeller <580 RPM >3 min: content uniformity failure | Major deviation | Hold; content uniformity must be demonstrated via dosage unit testing |

---

## 7. Revision History

| Version | Date | Changes |
|---|---|---|
| 1.0 | 2020-04-01 | Initial issue |
| 1.1 | 2021-10-01 | Tightened product temperature PAR to ≤42°C based on stability data |
| 2.0 | 2023-06-01 | New granulation time PAR (16–28 min); added post-drying lactone IPT |
| 2.1 | 2025-03-15 | Added moisture over-drying lower limit; updated blend room humidity requirement |
