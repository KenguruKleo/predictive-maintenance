# Sentinel Intelligence — Design System

## Philosophy

Industrial business application. Operators work 8–12 hour shifts, often in bright control rooms. The interface must be:

- **Utilitarian first** — every pixel earns its place. No decorative elements.
- **High contrast** — text and status colors must read clearly under fluorescent light or on older monitors.
- **Scannable** — operators make fast decisions. Critical information must be visible without scrolling.
- **Calm under pressure** — the UI itself should not feel alarming. Only status indicators use red/yellow. Chrome is neutral.

Reference systems for tone and density: IBM Carbon, SAP Fiori, Atlassian Design System.

---

## Color Palette

### Neutral Scale

| Token            | Value     | Use                                      |
|------------------|-----------|------------------------------------------|
| `--gray-50`      | `#f4f5f7` | Page background                          |
| `--gray-100`     | `#ebecf0` | Sidebar/panel background tint            |
| `--gray-200`     | `#dfe1e6` | Borders, dividers                        |
| `--gray-300`     | `#c1c7d0` | Disabled borders, placeholder            |
| `--gray-500`     | `#97a0af` | Muted text, secondary labels             |
| `--gray-600`     | `#5e6c84` | Secondary body text                      |
| `--gray-700`     | `#344563` | Body text                                |
| `--gray-900`     | `#172b4d` | Headings, primary text                   |

### Navigation Chrome

| Token             | Value     | Use                                   |
|-------------------|-----------|---------------------------------------|
| `--chrome-bg`     | `#1c2b3a` | Header, dark elements                 |
| `--chrome-border` | `#2e4057` | Subtle borders within chrome          |
| `--chrome-text`   | `#b3bac5` | Secondary text on dark               |
| `--chrome-text-strong` | `#ffffff` | Primary text on dark              |

### Brand / Interactive

| Token              | Value     | Use                                  |
|--------------------|-----------|--------------------------------------|
| `--blue-primary`   | `#0052cc` | Primary buttons, links, focus rings  |
| `--blue-hover`     | `#0747a6` | Button hover                         |
| `--blue-light`     | `#deebff` | Selected nav item background         |
| `--blue-text`      | `#0052cc` | Link text on light backgrounds       |

### Semantic — Severity

> Based on ISA-18.2 HMI alarm priority conventions.

| Token                 | Value     | Background   | Use                        |
|-----------------------|-----------|--------------|----------------------------|
| `--sev-critical-fg`   | `#de350b` | `#ffebe6`    | Critical severity tag      |
| `--sev-major-fg`      | `#ff8b00` | `#fffae6`    | Major severity             |
| `--sev-moderate-fg`   | `#ca7d01` | `#fff8d6`    | Moderate (amber, readable) |
| `--sev-minor-fg`      | `#006644` | `#e3fcef`    | Minor / resolved           |

### Semantic — Incident Status

| Token                 | Value     | Background   | Use                        |
|-----------------------|-----------|--------------|----------------------------|
| `--status-pending`    | `#ff8b00` | `#fffae6`    | Pending approval           |
| `--status-analyzing`  | `#0052cc` | `#deebff`    | AI processing              |
| `--status-escalated`  | `#ca7d01` | `#fff8d6`    | Escalated                  |
| `--status-approved`   | `#006644` | `#e3fcef`    | Approved                   |
| `--status-rejected`   | `#de350b` | `#ffebe6`    | Rejected                   |
| `--status-executing`  | `#0052cc` | `#deebff`    | Executing actions          |
| `--status-closed`     | `#5e6c84` | `#ebecf0`    | Closed                     |

### Semantic — Confidence

| Level  | Color        | Use                                |
|--------|--------------|------------------------------------|
| High   | `#006644`    | ≥ 80% confidence — green           |
| Medium | `#ca7d01`    | 60–79% — amber                     |
| Low    | `#de350b`    | < 60% — red, triggers banner       |

---

## Typography

```
Font stack: 'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif
Mono stack: 'JetBrains Mono', 'Consolas', 'Courier New', monospace
```

Use **Inter** for all body/UI text. Use **monospace** for: incident IDs, batch numbers, parameter values, timestamps.

### Type Scale

| Role              | Size    | Weight | Line-height | Use                          |
|-------------------|---------|--------|-------------|------------------------------|
| `page-title`      | 20px    | 700    | 1.3         | Page headings (H1)           |
| `section-heading` | 14px    | 700    | 1.4         | Card titles, section labels  |
| `body`            | 14px    | 400    | 1.5         | Default body text            |
| `body-sm`         | 13px    | 400    | 1.5         | Secondary info, descriptions |
| `label`           | 11px    | 600    | 1.4         | ALL-CAPS data labels, column headers |
| `mono`            | 13px    | 400    | 1.4         | IDs, batch numbers, values   |
| `badge`           | 11px    | 700    | 1           | Status/severity tags         |

> **Rule:** Never use font-size below 11px. Never use font-weight 300 (too light for readability on monitors).

---

## Spacing

4px base grid. All spacing values are multiples of 4.

```
--space-1:  4px    (tight — icon gaps, inline elements)
--space-2:  8px    (compact — between related items)
--space-3:  12px   (default inline padding)
--space-4:  16px   (default component padding)
--space-5:  20px   (section spacing within a card)
--space-6:  24px   (card padding, layout gaps)
--space-8:  32px   (between sections)
--space-10: 40px   (page-level gaps)
--space-12: 48px   (large separations)
```

### Component Padding Conventions

| Component           | Padding              |
|---------------------|----------------------|
| Card                | `20px 24px`          |
| Table cell          | `10px 16px`          |
| Button (default)    | `7px 16px`           |
| Button (small)      | `4px 10px`           |
| Input / select      | `7px 12px`           |
| Sidebar nav item    | `10px 20px`          |
| Page content area   | `28px 32px`          |
| Badge               | `2px 8px`            |

---

## Layout

```
--header-height:  52px   (compact, fixed top)
--sidebar-width:  240px  (enough for labels, not too wide)
--content-max:    1400px (constrain for ultra-wide monitors)
```

### Grid

- **Dashboard cards**: `repeat(auto-fill, minmax(320px, 1fr))` — responsive grid
- **Incident detail**: `1fr 360px` — content + approval panel
- **Table pages**: full width within content area

### Elevation

No excessive shadows. Use **border** as primary separator. Shadows only for:

```
--shadow-sm:  0 1px 2px rgba(0,0,0,0.06)           (cards in light context)
--shadow-md:  0 2px 8px rgba(0,0,0,0.10)            (dropdowns, hover cards)
--shadow-lg:  0 8px 32px rgba(0,0,0,0.16)           (modals only)
```

---

## Borders & Radius

```
--radius-sm:  4px   (badges, small chips)
--radius-md:  6px   (cards, inputs, buttons)
--radius-lg:  8px   (modals)

--border-color: var(--gray-200)   #dfe1e6
--border: 1px solid var(--border-color)
```

**No**: rounded corners on tables, no card-inside-card patterns.

---

## Components

### Sidebar Navigation Item

```
height: 40px
padding: 0 20px
font-size: 13px, weight 500
icon: 16px, margin-right: 10px
active: blue-light background (#deebff), bold, blue text + 3px left border
hover: gray-50 background
```

### Status / Severity Badge

```
font-size: 11px, weight 700, uppercase
padding: 2px 8px
border-radius: 4px (--radius-sm)
color: semantic fg, background: semantic bg (from table above)
```

### Card

```
background: white
border: 1px solid #dfe1e6
border-radius: 6px
padding: 20px 24px
no shadow by default (border is enough)
```

### Primary Button

```
background: #0052cc
color: white
font-size: 14px, weight 600
padding: 7px 16px
border-radius: 6px
hover: #0747a6
focus: 2px solid #4c9aff outline
```

### Approve Button

```
background: #006644
color: white
... same sizing as primary
```

### Danger / Reject Button

```
background: #de350b
color: white
```

### Data Label

```
font-size: 11px
font-weight: 600
color: #5e6c84 (gray-600)
text-transform: uppercase
letter-spacing: 0.04em
margin-bottom: 4px
```

### Table

```
th: font-size 11px, weight 700, uppercase, gray-600, 10px 16px padding, bottom border 2px gray-200
td: font-size 13px, gray-700, 10px 16px padding, bottom border 1px gray-100
row hover: gray-50 background
no outer border on table
```

---

## Motion

Minimal animations. Only for:

- **Spinner**: rotate, 0.8s linear
- **Pulse** (connection dot): 1.2s opacity
- **Confidence bar fill**: width transition 0.3s ease
- **Modal appear**: `opacity 0→1, translateY 8px→0`, 0.15s ease

No page-level transitions. No slide animations on sidebar.

---

## Do / Don't

| ✅ Do                                              | ❌ Don't                                     |
|----------------------------------------------------|----------------------------------------------|
| Use semantic colors only for status/severity       | Use green/red for decorative purposes        |
| Monospace for batch IDs, parameter values, timestamps | Serif fonts anywhere                      |
| High contrast text on all backgrounds              | Gray-on-gray text combinations               |
| 4px grid alignment                                 | Arbitrary pixel values for spacing           |
| Clear section labels (uppercase, gray-600)         | Section headers using H2 with bold+large     |
| One primary action per view                        | Multiple equal-weight CTAs in one area       |
| Compact info density in tables                     | Large whitespace gaps that reduce data per row |
| Border as visual separator                         | Shadows as visual separators                 |
