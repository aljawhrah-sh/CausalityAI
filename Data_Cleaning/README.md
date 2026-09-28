# Causality & Reaction Data Cleaning

Cleaning of the WHO-UMC causality assessments and reaction data from
`file_new_ids.xlsx` (Case sheet: 50,000 rows; Causality sheet: 150,068 rows).

---

## Scripts

| File | Purpose |
|---|---|
| `explore_causality.py` | Explores the causality column: assessment counts per cell, method variants, verdict variants |
| `clean_causality.py` | Builds the cleaned causality table |
| `explore_reactions.py` | Explores the Outcome column and its alignment with reactions |
| `explore_umc_terms.py` | Explores the UMC term code column |
| `clean_reactions.py` | Builds the cleaned reaction-level table |
| `explore_dates.py` | Explores reaction start/end dates: precision and alignment |
| `clean_dates.py` | Builds the cleaned reaction date table |

Run order: any `explore_*` script is optional and read-only. The three
`clean_*` scripts are independent of each other and can be run in any order.

---

## Output files

### `causality_cleaned.xlsx` — 22,043 rows, 12,377 cases

One WHO-UMC assessment per drug–event pair.

| Column | Description |
|---|---|
| `report ID` | Case identifier (join key) |
| `drug` | WHODrug active ingredient variant |
| `reaction` | MedDRA preferred term |
| `verdict_original` | Verdict exactly as recorded in the source |
| `verdict_normalized` | Mapped to one of the six WHO-UMC categories |
| `method` | Assessment method as recorded |
| `source` | Assessment source, kept unchanged |
| `source_category` | Keyword-based classification of the source |

**Verdict distribution:** Possible 9,636 · Probable 8,754 · Unlikely 1,205 ·
Certain 967 · Unassessable 878 · Conditional 603

**Source categories:** Hospital/Clinic/Provider 9,976 · Other 3,666 ·
Pharmacovigilance Centre 3,129 · Regional Health Authority 2,197 ·
National Regulatory Authority 1,830 · Company/MAH 1,204 · Reporter 41

---

### `reactions_cleaned.xlsx` — 96,609 rows

One row per reaction, expanded from the stacked cells in the Case sheet.

| Column | Description |
|---|---|
| `report ID` | Case identifier (join key) |
| `umc_term_code` | Numeric MedDRA code reported to UMC |
| `mapped_term` | Reaction as described by the reporter |
| `meddra_term` | MedDRA preferred term |
| `outcome` | Recovered / Recovering / Not recovered / Died / Recovered with sequelae / Unknown |
| `code_term_mismatch` | TRUE where the UMC code maps to more than one MedDRA term (499 rows) |

**Outcome distribution:** Recovered 40,307 · Unknown 24,420 ·
Not recovered 14,725 · Recovering 12,532 · blank 2,974 · Died 1,074 ·
Recovered with sequelae 577

---

### `reaction_dates_cleaned.xlsx` — 97,044 rows

One row per reaction with its start and end dates.

| Column | Description |
|---|---|
| `report ID` | Case identifier (join key) |
| `meddra_term` | MedDRA preferred term |
| `reaction_start` | Start date, assigned only where alignment is reliable |
| `reaction_end` | End date, assigned only where alignment is reliable |
| `start_unaligned` | TRUE where start dates exist but could not be matched (12,110 rows) |
| `end_unaligned` | TRUE where end dates exist but could not be matched (8,059 rows) |
| `start_precision` | day / month / year |
| `end_precision` | day / month / year |
| `date_sequence_invalid` | TRUE where the end date precedes the start date (1 row) |

Rows with a start date: 58,126 · with an end date: 27,791

---

## Method notes

**Stacked cells.** Cells in the source file hold several values separated by
`_x000D_`, an artefact of the export from the authority's system where a line
break was written out as literal text. All scripts convert it back to a line
break before splitting.

**Position-based alignment.** Where one row holds several reactions, the *i*-th
value in each column is taken to belong to the *i*-th reaction. Verified
independently: counts match in 96% of rows for outcomes and 99.4% for UMC
codes, and only 12 UMC codes out of thousands map to more than one MedDRA
term.

**Dates are the exception.** Date columns frequently hold fewer values than
reactions, so position gives no reliable match. Dates are assigned only where
the counts agree; the rest are left blank and flagged.

**Nothing is silently corrected.** Rows that look wrong are flagged rather than
edited or deleted, so the original data stays recoverable.
