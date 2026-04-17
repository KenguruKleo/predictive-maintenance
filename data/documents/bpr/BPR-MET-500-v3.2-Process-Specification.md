# BPR-MET-500-v3.2 · Metformin HCl 500mg Tablets — Master Batch Process Specification

**Document ID:** BPR-MET-500-v3.2  
**Product Name:** Metformin Hydrochloride 500mg Immediate Release Tablets  
**Product Code:** MET-500-TAB  
**Batch Size:** 200 kg (standard); 100 kg (development scale)  
**Document Type:** Master Batch Production Record — Process Specification  
**Version:** 3.2 | **Effective Date:** 2025-06-01 | **Next Review:** 2027-06-01  
**Owner:** Technical Operations / Process Development  
**Associated Equipment:** GR-204 (Granulation), DRY-303 (Drying), MIX-102 (Final Blend)  
**Associated SOPs:** SOP-MAN-GR-001, SOP-MAN-DRY-001, SOP-DEV-001

---

## 1. Product Overview

Metformin HCl 500mg is a biguanide antidiabetic agent. The API is highly water-soluble, hygroscopic, and requires controlled humidity conditions during processing. Wet granulation with aqueous binder is the standard manufacturing approach.

**Critical Quality Attributes (CQAs):**
- Content uniformity (target: 98–102% of label claim; limit: 95–105%)
- Dissolution (Q = 80% at 30 min, USP Apparatus II, 50 rpm, 900 mL water)
- Moisture content of granules (target: 8–12%; limit: ≤13%)
- Particle Size Distribution: D50 380–450 µm; D90 ≤1000 µm
- Tablet hardness: 12–18 kP (target 15 kP)
- Disintegration: ≤15 minutes

**API Properties relevant to processing:**
- Hygroscopic — absorbs moisture above 50% RH. Room humidity must be ≤50% during granulation and blending.
- Thermally stable to >200°C — no thermal degradation risk during standard drying (≤70°C)
- Solubility: freely soluble in water — binder solution must be prepared fresh (max 4h hold)

---

## 2. Manufacturing Flow

```
Dispensing → Dry Mixing (GR-204) → Wet Granulation (GR-204)
           → Drying (DRY-303) → Milling → Final Blending (MIX-102)
           → Compression → Film Coating → Packaging
```

This specification covers: **Wet Granulation (GR-204)** and **Drying (DRY-303)** stages.

---

## 3. Stage 1 — Wet Granulation on GR-204

### 3.1 Materials

| Material | Role | Quantity (200 kg batch) |
|---|---|---|
| Metformin HCl | API | 100.0 kg |
| Microcrystalline Cellulose PH101 | Diluent / Binder | 52.0 kg |
| Povidone K30 (in binder solution) | Binder | 4.0 kg |
| Purified Water | Binder solvent | 28.0 kg |
| Crospovidone | Disintegrant (intragranular) | 6.0 kg |

**Binder solution:** Dissolve 4.0 kg Povidone K30 in 28.0 kg Purified Water. Mix until clear. Use within 4 hours of preparation.

### 3.2 Product-Specific Critical Process Parameters — Wet Granulation

> These are **product-specific validated operating ranges** (NOR/PAR). They are narrower than the equipment validated range stated in SOP-MAN-GR-001 §4.1. In case of conflict, **these product-specific limits take precedence** for this product.

| Parameter | Product NOR | Product PAR | Equipment Validated Range | Unit |
|---|---|---|---|---|
| Impeller speed — dry mix | 350 ± 50 | 250–450 | 200–800 | RPM |
| Impeller speed — wet granulation | **650 ± 50** | **600–750** | 200–800 | RPM |
| Chopper speed | 2200 ± 200 | 1800–2600 | 1000–3000 | RPM |
| Spray rate | **90 ± 15** | **70–110** | 50–200 | g/min |
| Inlet air temperature | 55 ± 5 | 48–62 | 40–70 | °C |
| Product temperature at endpoint | 37 ± 3 | 33–42 | 30–50 | °C |
| Binder addition time | 18 ± 3 | 14–24 | — | min |
| Post-addition mixing time | 5 ± 1 | 3–8 | — | min |
| Total granulation time | **24 ± 4** | **18–32** | 5–60 | min |

> ⚠️ **Deviation trigger (impeller speed):** An impeller speed below **600 RPM** for more than **2 minutes** during wet granulation constitutes a deviation requiring SOP-DEV-001 action. Duration 2–5 min with speed 580–599 RPM: minor deviation — perform granule moisture check before proceeding. Duration >5 min or speed <580 RPM: major deviation — batch hold required.

> ⚠️ **Deviation trigger (spray rate):** Spray rate below **70 g/min** for more than **3 minutes** during binder addition: major deviation — batch hold. Peristaltic pump inspection required. Risk: non-uniform binder distribution → granule heterogeneity.

> ⚠️ **Granulation time:** If total granulation time exceeds **32 minutes** (product PAR upper limit): major deviation regardless of parameter values within range. Risk: over-granulation → increased granule density → reduced dissolution rate. Moisture check and particle size analysis required.

### 3.3 In-Process Controls — Granulation

| Test | Specification | Frequency | Action if OOS |
|---|---|---|---|
| Wet granule visual inspection | Uniform wet mass, no dry lumps | End of binder addition | Extend mixing 2 min; check again |
| SCADA parameter confirmation | All CPPs within NOR | Continuous | Deviation per SOP-DEV-001 |
| Product temperature at endpoint | 33–42°C | At massing endpoint | If >42°C: emergency cool; if <33°C: extend mixing |
| Granulation time | 18–32 min | At endpoint | If >32 min: hold, moisture check |

---

## 4. Stage 2 — Drying on DRY-303

### 4.1 Product-Specific Critical Process Parameters — Drying

| Parameter | Product NOR | Product PAR | Unit |
|---|---|---|---|
| Inlet air temperature | 65 ± 5 | 58–72 | °C |
| Product temperature (max) | 45 (limit) | ≤48 | °C |
| Air flow rate | 950 ± 100 | 800–1100 | m³/h |
| Drying time (standard) | 90 ± 15 | 60–120 | min |
| Drying endpoint: moisture | **8–12%** (target 9%) | ≤13% | %w/w |

> **Inlet moisture effect:** If inlet granule moisture is above 15% (possible after extended granulation), increase drying time by 30 minutes and add intermediate moisture check at 60 min. Do not reduce inlet air temperature to compensate — risk of uneven drying.

### 4.2 In-Process Controls — Drying

| Test | Specification | Timing | Action if OOS |
|---|---|---|---|
| Moisture — intermediate | ≤13% | At 60 min | If >13%: extend 30 min, retest |
| Moisture — endpoint | **8–12%** | At standard endpoint | If >12%: extend 15 min intervals, retest up to 3×; if still OOS: deviation |
| Product temperature | ≤48°C | Continuous | If >48°C: reduce inlet temp to 58°C; raise deviation |

### 4.3 Granule Testing After Drying (before milling)

| Test | Specification | Method |
|---|---|---|
| Moisture content | 8–12% | Loss on drying (LOD), 105°C, 30 min |
| Bulk density | 0.45–0.60 g/mL | USP method |
| Particle size (post-drying, pre-mill) | D50 600–900 µm | Sieve analysis |

---

## 5. Batch Disposition Framework

| Scenario | Classification | Disposition |
|---|---|---|
| All CPPs within NOR, all IPTs pass | Normal | Release — no additional testing |
| Any CPP outside NOR but within PAR, IPTs pass | Minor deviation | Release with deviation documentation |
| Any CPP outside PAR, duration <5 min, IPTs pass | Major deviation | Release pending QA review + enhanced testing |
| Any CPP outside PAR, duration >5 min | Major deviation | Batch hold — QA assessment required |
| Moisture endpoint >13% after 3 extended drying attempts | Critical deviation | Batch rejection |
| Granulation time >32 min AND moisture OOS | Major deviation | Batch hold; PSD + moisture assessment |
| Equipment failure during granulation (bearing, motor) | Equipment deviation | Reject — duration/impact per SOP-DEV-001 §5.1 |

---

## 6. Historical CAPA Learnings (relevant to this product)

> These are documented learnings from past deviations with this product formulation, referenced for deviation assessment context.

| CAPA Reference | Root Cause | Impact on BPR v3.2 |
|---|---|---|
| From INC-2026-0005 analogue | GR-204 bearing wear → sustained speed <600 RPM for full batch | Added bearing wear predictive indicators; PM interval review |
| From INC-2026-0003 | Spray nozzle filter blockage → spray rate 42 g/min for 8 min → granule non-uniformity | Added spray rate alarm threshold; filter replacement interval to 30 days |
| From INC-2026-0002 analogue | Inlet air temperature 72°C for 6 min → over-drying → batch rejection | Added inlet temp alarm at 68°C (not only at 70°C NOR limit) |

---

## 7. Revision History

| Version | Date | Changes |
|---|---|---|
| 1.0 | 2019-01-01 | Initial issue |
| 2.0 | 2021-05-01 | Updated CPP ranges based on process validation study |
| 3.0 | 2023-09-01 | Added PAR limits; updated drying endpoint spec; aligned to new DRY-303 qualification data |
| 3.1 | 2024-08-01 | Added spray rate deviation trigger; historical CAPA learnings section |
| 3.2 | 2025-06-01 | Revised granulation time PAR (18–32 min); updated moisture endpoint to 8–12% |
