# Three patches to the cleaning pipeline

Reviewed against the raw export. Every figure in `cleaning_decisions.md` and the
README was verified and holds: 21,995 / 95,828 / 95,828 rows, keys unique, no
stacked values remaining, reactions and dates joining one-to-one with zero
orphans. The three changes below address things the review found on top of that.

Apply from the repository root:

```bash
git apply 01-carry-who-umc-criteria.patch
git apply 02-drug-alignment-guard.patch
cp 03-drug_level_for_merge.py drug_level_for_merge.py
```

Then re-run `clean_causality.py`, `student1_case_cleaning.py`, and
`drug_level_for_merge.py`.

---

## 1. Carry the WHO-UMC criteria columns through

`clean_causality.py`

**Problem.** `Time-to-onset`, `Dechallenge performed? / Reaction
resolved/resolving?` and `Rechallenge performed? / Reaction recurred?` were
absent from all five cleaned outputs. They exist only on the Causality sheet, so
dropping them there removed them from the pipeline entirely — and they are the
criteria the WHO-UMC framework actually assesses on. The cleaned data held the
label and almost none of the predictors.

**Change.** The build loop now carries all three through. A normalisation block
splits the two packed pairs into four columns and buckets time-to-onset:

| new column | values |
|---|---|
| `dechallenge_performed` | Yes 10,689 · Unknown 7,071 · No 4,235 |
| `reaction_resolved` | Yes 14,888 · Unknown 4,654 · No 2,453 |
| `rechallenge_performed` | Unknown 20,005 · Yes 1,990 |
| `reaction_recurred` | Unknown 20,737 · Yes 742 · No 516 |
| `time_to_onset_bucket` | same day 7,935 · 1-7 days 3,823 · 1-6 months 2,131 · >6 months 1,473 · 1-4 weeks 1,409 · Unknown 5,224 |

The raw text is kept alongside as `time_to_onset_raw`, `dechallenge_raw` and
`rechallenge_raw`, so nothing is lost and the normalisation can be re-derived.

**Why the pairs are split rather than kept as one field.** `No / Yes` means the
reaction resolved *without* the drug being withdrawn, which argues against the
drug. `Yes / Yes` means it resolved *because* the drug was withdrawn, which
argues for it. Those two are opposite evidence and they must not share a column.
`No / Yes` occurs 13,360 times in the source.

**Verified.** Row count still 21,995; verdict distribution byte-identical. The
patch only adds columns.

---

## 2. Guard positional alignment in the drug explode

`student1_case_cleaning.py`

**Problem.** The explode assumed the *i*-th value in every stacked column
belongs to the *i*-th drug. For the drug name and Role that holds — verified at
100%. For the rest it frequently does not. Among the 14,031 rows holding more
than one drug:

| column | rows where the value count ≠ the drug count |
|---|---|
| `Action taken with drug` | 5,302 (38%) |
| `Dose` / `Dose unit` | 4,780 (34%) |
| `Route of admin.` | 3,374 (24%) |
| `Indication` | 3,280 (23%) |

Where a row lists 5 drugs and 3 doses, there is no way to know which two drugs
are the ones missing a dose, so the values were being attached to the wrong
drug — silently.

**Change.** A column is aligned by position only when it holds exactly as many
values as there are drugs. Otherwise its values are set to Unknown and the row
is flagged. This is the same rule `clean_dates.py` already applies to its date
columns; the two scripts now agree.

**Effect.** Values corrected from wrong to Unknown: 12,480 doses, 10,501 dosage
regimens, 7,180 routes, 7,001 `Action taken with drug`, 6,637 drug start dates,
6,369 drug end dates, 6,627 indications. 34,184 new flags across 10,120 reports.
Row counts unchanged (49,966 / 94,491) — only values moved.

This one *loses* data, which looks like a step backwards. It isn't: those cells
were not missing before, they were wrong, and a wrong dose attached to the wrong
drug is worse for the model than a blank. `Action taken with drug` matters most
here, since it is the only remaining stand-in for dechallenge at drug level.

---

## 3. A merge-safe drug table

New file: `drug_level_for_merge.py`

**Problem.** `drug_level_clean.csv` is keyed on (report ID, drug_index), which
is right for the drug data — a case genuinely can list one ingredient several
times at different doses, and report 6 lists Atropine on 29 rows. But merging it
to the causality table on (report ID, drug) multiplies rows: **21,995 → 24,082,
a 9.5% inflation**, with 5,340 (report, drug) pairs appearing more than once.
This is the same failure that inflated a table by 1.61× during the earlier merge
stage.

**Change.** A new script collapses the table to one row per (report ID, drug).
`drug_level_clean.csv` is untouched and stays the source of truth.

Collapsing rules:

- **Role** — Suspect > Interacting > Concomitant. If a drug is suspect anywhere
  in the case, that is the role that matters for causality.
- **Action taken with drug** — Drug withdrawn > Dose reduced > Dose increased >
  Dose not changed > Not applicable. `Drug withdrawn` is the dechallenge signal
  and must survive the collapse.
- **Drug start date** — earliest known; **Drug end date** — latest known, so the
  row spans the whole exposure.
- **Everything else** — the single known value where the rows agree, otherwise
  `"Multiple"`. Picking one dose out of three would look like data and be a
  guess; `"Multiple"` sends the reader back to `drug_level_clean.csv`.
- `n_drug_rows` records how many rows collapsed; `collapsed_values` is TRUE
  where a field had to become `"Multiple"` (1,275 rows).

**Verified.** 85,453 rows, unique on the key, and the merge is one-to-one.
End-to-end across all four tables: 21,995 → 21,995 rows, 47 columns.

---

## Open questions, not patched

**The OMS exclusion.** Decision 1 keeps only methods naming "UMC", excluding
`Causalidade OMS`, `WHO Assessment` and `Causalidad de la OMS` — 4,605
assessments, about 16% of the WHO/OMS material. The caution is reasonable, but
the verdicts inside the excluded group are exactly the six WHO-UMC categories in
Portuguese and Spanish: `possível` (1,196), `provável` (281), `não avaliável /
não classificável` (176), `condicional / não classificado` (86), `improvável`
(110). No other WHO framework uses that six-category vocabulary, and ANVISA does
use WHO-UMC. Worth one question to the authority before writing off 16% of the
data. Not changed here, because it is a scope decision for the team and the
authority, not a bug.

**Decision 8 undercounts its own impact.** The document records 25 rows affected
by conflicting assessments. The real figure is **1,170** — cells holding more
than one WHO-UMC assessment whose verdicts disagree. The `break` in the build
loop resolves those before `drop_duplicates` ever sees them, so the dedup step
only counts the leftovers. The rule itself is the one agreed with the authority,
so nothing is wrong in the code; the number in the write-up should read 1,170,
and it is worth stating plainly that on those 1,170 cases the label is decided
by row order in the export rather than by anything clinical.

**Partial dates are handled two different ways.** `clean_dates.py` keeps
year-month and year-only dates with a `precision` column.
`student1_case_cleaning.py` discards them — 44% of drug start dates and 69% of
drug end dates become Unknown. Both choices are defensible, but they are
opposite rules applied to the same problem in one pipeline, and together with the
dropped `Time-to-onset` column they removed every route to reconstructing time to
onset. Patch 1 restores the column; the date rules still need reconciling.

**`Age`, `Weight (kg)` and `Height (cm)` are text columns** in
`case_level_clean.csv`, because `"Unknown"` is stored in the same column as the
numbers. They need coercing to numeric with a separate missing indicator before
any model reads them.

**Separators disagree** — `"; "` for seriousness criteria, `"|"` for the reaction
tables. Worth settling on one before the merge.

**Scripts write to their working directory**, not to `Data_Cleaning/outputs/`, so
a regenerated `causality_cleaned.xlsx` lands next to the script and the copy in
`outputs/` goes stale. Worth making the output path explicit.

---

## Checked and correct

The indication spelling normalisation was audited in full: 168 merged groups,
every one a genuine UK/US variant (`Anaemia`/`Anemia`, `oedema`/`edema`,
`immunisation`/`immunization`), no two different conditions collapsed together.
The only wrinkle is cosmetic — the surviving spelling is whichever is more
frequent, so `Anemia` wins in one group while `Anaemia iron deficiency` wins in
another. Harmless for the model, slightly untidy in a report table.
