# BPR-PCT-500-v2.0 · Paracetamol 500mg Tablets — Master Batch Process Specification

**Document ID:** BPR-PCT-500-v2.0  
**Product Name:** Paracetamol (Acetaminophen) 500mg Tablets  
**Product Code:** PCT-500-TAB  
**Batch Size:** 250 kg (standard)  
**Document Type:** Master Batch Production Record — Process Specification  
**Version:** 2.0 | **Effective Date:** 2024-11-01 | **Next Review:** 2026-11-01  
**Owner:** Technical Operations / Process Development  
**Associated Equipment:** GR-204 (Granulation), DRY-303 (Drying), MIX-102 (Blending/Lubrication)  
**Associated SOPs:** SOP-MAN-GR-001, SOP-MAN-DRY-001, SOP-DEV-001

---

## 1. Product Overview

Paracetamol 500mg is a high-dose analgesic/antipyretic. The API makes up approximately 71% of the final tablet weight, making this a **high drug-load** formulation. This has two key implications:

1. Granulation homogeneity is inherently more forgiving than low drug-load products.
2. **Lubrication is the critical blending step** — at high API load, tablet compression behaviour is dominated by lubricant distribution. Over-lubrication (excess magnesium stearate coating of API/excipient surfaces) significantly reduces tablet hardness and dissolution rate.

**Critical Quality Attributes (CQAs):**
- Tablet hardness: 10–16 kP (target 13 kP)
- Dissolution: Q = 80% at 30 min, USP Apparatus II, 50 rpm, 900 mL water
- Content uniformity: 98–102% (target); limit 95–105%
- Moisture content of granules: 2–5% (target 3%)
- Disintegration: ≤5 min

**API Properties relevant to processing:**
- High drug load (71% w/w) — excellent flow, low compressibility as raw powder; granulation improves compressibility
- No thermal degradation concern at standard process temperatures (stable to >150°C)
- Minimal hygroscopicity — humidity control less critical than Metformin or Atorvastatin
- **Lubricant sensitivity:** High drug-load tablet is particularly sensitive to over-lubrication with magnesium stearate. Lubricant blend speed and time are tightly controlled CPPs.

---

## 2. Manufacturing Flow

```
Dispensing → Wet Granulation (GR-204)
           → Drying (DRY-303) → Milling
           → Pre-Lubrication Blend (MIX-102) → Lubrication Blend (MIX-102)
           → Compression → Packaging
```

*Note: Paracetamol 500mg is uncoated (plain film coat optional for some markets); core tablet specification applies.*

---

## 3. Stage 1 — Wet Granulation on GR-204

### 3.1 Materials

| Material | Role | Quantity (250 kg batch) |
|---|---|---|
| Paracetamol fine powder (USP) | API | 177.5 kg |
| Pregelatinised Starch | Diluent / Disintegrant | 40.0 kg |
| Povidone K29/32 (3% w/v binder solution) | Binder | 5.0 kg in 28 kg water |
| Purified Water | Binder solvent | 28.0 kg |
| Crospovidone XL-10 | Disintegrant (intragranular) | 6.0 kg |

### 3.2 Product-Specific Critical Process Parameters — Wet Granulation

> These are **product-specific validated operating ranges** (NOR/PAR). In case of conflict with SOP-MAN-GR-001 §4.1, these product-specific limits take precedence for this product.

| Parameter | Product NOR | Product PAR | Equipment Validated Range | Unit |
|---|---|---|---|---|
| Impeller speed — dry mix | 400 ± 50 | 300–500 | 200–800 | RPM |
| Impeller speed — wet granulation | **700 ± 50** | **620–780** | 200–800 | RPM |
| Chopper speed | 2000 ± 200 | 1600–2400 | 1000–3000 | RPM |
| Spray rate | **100 ± 20** | **70–130** | 50–200 | g/min |
| Inlet air temperature | 52 ± 5 | 44–62 | 40–70 | °C |
| Product temperature at endpoint | 38 ± 4 | 32–44 | 30–50 | °C |
| Binder addition time | 20 ± 3 | 15–26 | — | min |
| Post-addition mixing time | 4 ± 1 | 2–7 | — | min |
| Total granulation time | **26 ± 5** | **18–34** | 5–60 | min |

> ⚠️ **Note on impeller speed:** Paracetamol high-load granulation is less sensitive to moderate impeller speed variations than low-drug-load products. However, speeds below **620 RPM** for >5 min increase risk of wet lumps (granule agglomeration) due to the high API fraction. Deviation: speed 595–619 RPM for >5 min = minor deviation; speed <595 RPM for >5 min = major deviation.

### 3.3 In-Process Controls — Granulation

| Test | Specification | Frequency | Action if OOS |
|---|---|---|---|
| Wet granule screen test (16 mesh) | ≥85% passing | End of binder addition | If <85%: extend mixing 2 min; retest |
| SCADA parameter confirmation | All CPPs within NOR | Continuous | Deviation per SOP-DEV-001 |
| Product temperature | 32–44°C | At endpoint | If >44°C: investigate; if <32°C: insufficient granulation |

---

## 4. Stage 2 — Drying on DRY-303

### 4.1 Product-Specific Critical Process Parameters — Drying

| Parameter | Product NOR | Product PAR | Unit |
|---|---|---|---|
| Inlet air temperature | 70 ± 5 | 62–78 | °C |
| Product temperature (max) | 50 (target) | ≤55 | °C |
| Air flow rate | 1000 ± 100 | 850–1150 | m³/h |
| Drying time (standard) | 70 ± 10 | 50–90 | min |
| Moisture endpoint | **2–5%** (target 3%) | ≤6% | %w/w |

> Paracetamol permits a higher drying temperature than temperature-sensitive APIs (Metformin: 65°C; Atorvastatin: 60°C). Inlet air temperature of 70–75°C is standard NOR for this product.

### 4.2 In-Process Controls — Drying

| Test | Specification | Timing | Action if OOS |
|---|---|---|---|
| Moisture — intermediate | 6–10% | At 45 min | If >10%: extend 20 min; if <6%: may approach endpoint early |
| Moisture — endpoint | **2–5%** | At standard endpoint | If >5%: extend 15 min; if <2%: stop — risk of over-drying/brittle granules |

### 4.3 Post-Drying Granule Release Tests

| Test | Specification |
|---|---|
| Moisture (LOD) | 2–5% |
| Bulk density | 0.55–0.70 g/mL |
| Particle size: D50 | 350–500 µm |
| Friability of granules (1 m drop) | ≤3% |

---

## 5. Stage 3 — Blending and Lubrication on MIX-102

> **This is the most critical stage for this product.** Over-lubrication is the primary quality risk and the most frequent root cause of tablet hardness failures.

### 5.1 Pre-Lubrication Blend

| Material | Quantity (250 kg batch) |
|---|---|
| Dried granules (from above) | ~210 kg |
| Microcrystalline Cellulose PH102 (extragranular) | 20.0 kg |
| Crospovidone XL-10 (extragranular disintegrant) | 7.5 kg |

| Parameter | Product NOR | Product PAR | Unit |
|---|---|---|---|
| Blending speed | **75 ± 10** | 60–90 | RPM |
| Blending time | **30 ± 5** | 22–40 | min |
| Temperature | ≤28°C | ≤32°C | °C |

### 5.2 Lubrication Blend (Magnesium Stearate)

| Material | Role | Quantity |
|---|---|---|
| Magnesium Stearate (Hyqual Veg) | Lubricant | 1.25 kg (0.5% w/w of final blend) |

| Parameter | Product NOR | Product PAR | Unit |
|---|---|---|---|
| Lubrication blending speed | **55 ± 5** | **48–62** | RPM |
| Lubrication blending time | **3 min ± 30 s** | **2–4 min** | min |
| Temperature | ≤28°C | ≤32°C | °C |

> ⚠️ **CRITICAL — Over-lubrication risk:** This is the most frequent quality issue with this product. Magnesium stearate films onto API and excipient surfaces progressively — each additional minute above 4 min increases lubricant coverage approximately 8–12% (based on historical process analytical technology data). 
>
> **Deviation trigger:** Lubrication blend time >4 min = **major deviation** regardless of speed. Possible impact: tablet hardness below specification; dissolution failure. Mandatory compression characterisation run (6 tablets from first tooling change) before batch release.
>
> **If lubrication time was 4–5 min:** Minor deviation; tablet hardness test (n=20) required. If hardness within spec: release with deviation documentation. If hardness below spec: batch hold.
>
> **If lubrication time >5 min:** Major deviation; dissolution testing (n=12) required in addition to hardness. QA assessment before release.

### 5.3 In-Process Controls — Blending

| Test | Specification | Frequency | Action if OOS |
|---|---|---|---|
| Blend uniformity (pre-lubrication) | RSD ≤3.0% for API | At end of pre-lubrication blend | If >3%: extend 5 min, retest once |
| Lubrication time confirmation | 2–4 min | At endpoint | If >4 min: deviation per above |
| Temperature | ≤28°C | Continuous | If >28°C: pause blend, investigate heat source |

---

## 6. Batch Disposition Framework

| Scenario | Classification | Disposition |
|---|---|---|
| All CPPs within NOR, all IPTs pass | Normal | Release |
| Granulation impeller 595–619 RPM >5 min, IPTs pass | Minor deviation | Release with deviation documentation |
| Granulation impeller <595 RPM >5 min | Major deviation | Hold; granule PSD + dissolution test required |
| Lubrication time 4–5 min | Minor deviation | Release with hardness confirmation (n=20) |
| Lubrication time >5 min | Major deviation | Hold; hardness + dissolution required; QA approval |
| Drying over moisture spec (>6%) | Major deviation | Hold; extend drying with QA approval |
| Blend uniformity RSD >3% after 1 extension | Major deviation | Hold; full investigation required |

---

## 7. Revision History

| Version | Date | Changes |
|---|---|---|
| 1.0 | 2018-06-01 | Initial issue |
| 1.1 | 2020-11-01 | Lubrication blend time tightened to 3 min ± 30 s (from 3 ± 1 min) based on dissolution failures |
| 1.2 | 2022-04-01 | Added blend uniformity in-process test; updated particle size release criteria |
| 2.0 | 2024-11-01 | Major revision: updated CPP PAR ranges; added over-lubrication risk table and escalation criteria; re-confirmed granulation time PAR against validation batches |
