# Causality & Reaction Data Cleaning

Cleaning of the WHO-UMC causality assessments and reaction data from
`file_new_ids.xlsx` (Case sheet: 50,000 rows; Causality sheet: 150,068 rows).

Column names follow the naming convention agreed with the team for merging,
and every output table is unique on its key so that joins do not multiply rows.

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

All three `clean_*` scripts read `review_flags.csv` to drop the reports
excluded during cross-column validation. That file is produced by the case-data cleaning and lives in its folder — copy it next to these scripts before running them.

---

## Output files

### `causality_cleaned.xlsx` — 21,995 rows

One WHO-UMC assessment per drug–event pair.

**Key:** `report ID` + `WHODrug active ingredient variant` + `MedDRA preferred term`

The key is three-part, not two. Joining on report ID and reaction alone will
multiply rows by the number of drugs in the case.

| Column | Description |
|---|---|
| `report ID` | Case identifier (join key) |
| `WHODrug active ingredient variant` | Suspect drug |
| `MedDRA preferred term` | Reaction |
| `verdict_original` | Verdict exactly as recorded in the source |
| `verdict_normalized` | Mapped to one of the six WHO-UMC categories |
| `method` | Assessment method as recorded |
| `source` | Assessment source, kept unchanged |
| `source_category` | Keyword-based classification of the source |

**Verdict distribution:** Possible 9,621 · Probable 8,744 · Unlikely 1,189 · 
Certain 964 · Unassessable 878 · Conditional 599

**Source categories:** Hospital/Clinic/Provider 9,958 · Other 3,654 ·
Pharmacovigilance Centre 3,118 · Regional Health Authority 2,196 ·
National Regulatory Authority 1,825 · Company/MAH 1,203 · Reporter 41

---

### `reactions_cleaned.xlsx` — 95,828 rows

One row per reaction.

**Key:** `report ID` + `MedDRA preferred term` (unique)

| Column | Description |
|---|---|
| `report ID` | Case identifier (join key) |
| `MedDRA preferred term` | Reaction |
| `umc_term_code` | Numeric MedDRA code reported to UMC; several codes joined by a pipe |
| `mapped_term` | Reaction as described by the reporter; several terms joined by a pipe |
| `Outcome` | Single value — the most severe outcome recorded for this reaction |
| `Outcome_all` | All outcomes recorded for this reaction, pipe-separated |
| `n_raw_terms` | How many raw reporter terms collapsed into this row |
| `code_term_mismatch` | TRUE where the UMC code maps to more than one MedDRA term |

**Outcome distribution:** Recovered 39,943 · Unknown 24,197 ·
Not recovered 14,657 · Recovering 12,452 · blank 2,935 · Died 1,073 ·
Recovered with sequelae 571

---

### `reaction_dates_cleaned.xlsx` — 95,828 rows

One row per reaction with its start and end dates.

**Key:** `report ID` + `MedDRA preferred term` (unique)

Same row count and same key as `reactions_cleaned.xlsx`, so the two join
one-to-one.

| Column | Description |
|---|---|
| `report ID` | Case identifier (join key) |
| `MedDRA preferred term` | Reaction |
| `Reaction start date` | Earliest start date, assigned only where alignment is reliable |
| `Reaction end date` | Latest end date, assigned only where alignment is reliable |
| `start_unaligned` | TRUE where start dates exist but could not be matched |
| `end_unaligned` | TRUE where end dates exist but could not be matched |
| `start_precision` | day / month / year |
| `end_precision` | day / month / year |
| `date_sequence_invalid` | TRUE where the end date precedes the start date (1 row) |

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

**Collapsing to one row per key.** The same reaction can appear more than once
in a case when the reporter described it in different words — for example
"Generalized itching" and "Itchy scalp" both map to Pruritus. Those rows are
collapsed so each table is unique on its key. Raw terms and codes are joined
by a pipe (verified absent from the source values), dates take the earliest
start and latest end so the row spans the full episode, and the outcome takes
the most severe value with the full list kept in `Outcome_all`.

**Nothing is silently corrected.** Rows that look wrong are flagged rather than
edited or deleted, so the original data stays recoverable.
