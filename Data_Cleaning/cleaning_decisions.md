# Cleaning decisions

Decisions applied when cleaning the causality and reaction columns, with the
rationale behind each and the number of rows affected.



---

## 1. Scope of the WHO-UMC method

**Decision.** Keep only method variants that explicitly mention UMC. Exclude
variants naming only WHO or OMS (e.g. "Causalidade OMS", "WHO Assessment",
"Uppsala/OMS"). Treat "WHO AEFI" as a separate methodology outside the scope
of this study.

**Rationale.** The causality column records the method in more than 50
spellings across several languages. Only those naming UMC can be confirmed as
the WHO-UMC framework the model is built around; WHO AEFI is a distinct
framework with its own criteria, used for adverse events following
immunisation.

**Affects.** ~5,300 assessments excluded; ~29,200 retained. The largest single
decision by volume.

**Implemented in.** `clean_causality.py` — the `re.search(r'UMC', method, ...)`
condition in the build loop.

---

## 2. Verdicts outside the six WHO-UMC categories

**Decision.** Exclude any verdict that does not belong to the six standard
categories: terms from other scales (Related, Not Related, Reasonable
Possibility, Possibly related, Probably related) and general values (Unknown,
UNK, Not assessed, Not Reported, Not Applicable, N/A dietary supplement,
non-AE). Translations of the standard categories into other languages are
retained and mapped to their English equivalent.

**Rationale.** Follows the authority's instruction to filter on the recognised
WHO-UMC terminology. "Related / Not Related" is a binary scale from a
different methodology; a general value such as "Unknown" is not a WHO-UMC
category, whereas "No evaluable/Inclasificable" is simply the Spanish wording
of Unassessable/Unclassifiable and is kept.

**Affects.** ~241 assessments excluded. Compound values such as
"Unlikely/Not Related", which mix both scales, are also excluded.

**Implemented in.** `clean_causality.py` — the `verdict_mapping` dictionary.

---

## 3. Duplicate rows in the Causality sheet

**Decision.** Remove rows identical on report ID, drug, reaction, verdict and
source.

**Rationale.** Report ID 6 holds 528 rows covering only 4 drugs and 7
reactions — a maximum of 28 unique drug–event pairs, so each pair repeats
roughly 13 times with identical values. Identical rows add no information but
inflate any count or distribution built on the data. (The "Number of
Suspect/Interacting drugs" column records 48 drugs for this same case, which
does not match the 4 actually present — noted for the team member handling
that column.)

**Affects.** 1,759 rows removed.

**Implemented in.** `clean_causality.py` — the first `drop_duplicates` call.

---

## 4. Outcomes with no corresponding reaction

**Decision.** Discard outcomes that have no reaction to attach to.

**Rationale.** An outcome describes what happened to a specific reaction. Where
the reaction columns are empty but an outcome is recorded, there is nothing for
the outcome to describe and no way to recover what the reaction was.

**Affects.** 385 rows.

**Implemented in.** `clean_reactions.py` — the filter on the reaction column.

---

## 5. Aligning reaction dates

**Decision.** Assign start and end dates to reactions by position only where
the number of dates equals the number of reactions in that row. Where dates
exist but the counts differ, leave the date blank and flag the row.

**Rationale.** Where a row holds three reactions but only two dates, position
gives no way to tell which reaction is missing its date. Attaching a date to
the wrong reaction would corrupt any time-to-onset calculation, so an
unassigned date is preferable to a wrong one. The flag preserves the
distinction between "no date recorded" and "date recorded but unmatchable".

**Affects.** Start dates unassigned in 15,421 source rows; end dates in 31,359.

**Second decision.** Partial dates are kept as recorded rather than padded to
a full date — year-and-month (5,902) and year-only (4,489) — with a precision
column recording the level of detail available.

**Implemented in.** `clean_dates.py` — the `start_aligned` / `end_aligned`
conditions.

---

## 6. Level at which "first assessment" applies

**Decision.** Take the first WHO-UMC assessment per drug–event pair, rather
than per case.

**Rationale.** In pharmacovigilance, causality is assessed for each drug–event
pair separately: within one case, one drug may be strongly linked to a given
reaction while another is not. The authority's framing of the question ("for
the same drug–event pair") supports this reading.

**Implemented in.** `clean_causality.py` — the `break` in the build loop.

---

## 7. Reports excluded during cross-column validation

**Decision.** Remove the 34 reports flagged in `review_flags.csv` from all
three output tables.

**Rationale.** Those reports record `Pregnancy case = Yes` together with
`Sex = Male`, a combination that cannot occur. They were removed from the
case-level tables by the team member handling those columns, so keeping
them here would leave the tables inconsistent at merge time.

**Affects.** 23 rows in the causality table, 109 rows in each of the reaction
and date tables.

**Implemented in.** All three `clean_*` scripts — the filter on
`review_flags.csv`.

---

## 8. Duplicate drug–event pairs with differing assessments

**Decision.** Where the same report, drug and reaction carry more than one
WHO-UMC assessment, keep the first and drop the rest.

**Rationale.** Removing only identical rows (decision 3) left pairs that
repeat with a different verdict or source. The rule already agreed with the
authority — first WHO-UMC assessment in order — resolves them consistently
rather than excluding the pair altogether.

**Affects.** 25 rows.

**Implemented in.** `clean_causality.py` — the second `drop_duplicates` call.

---

## 9. Collapsing to one row per key

**Decision.** Collapse the reaction and date tables so each is unique on
`report ID` + `MedDRA preferred term`. Raw reporter terms and UMC codes are
joined by a pipe with a count in `n_raw_terms`; dates take the earliest start
and the latest end.

**Rationale.** The same reaction can appear more than once in a case when the
reporter described it in different words — "Generalized itching" and "Itchy
scalp" both map to Pruritus. Left as-is, a merge on the key silently
multiplies rows; this happened on another table during the merge stage and
inflated it by 1.61 times. Taking the earliest start and latest end keeps the
row spanning the full episode. The pipe was verified absent from every source
value before use, so the joined fields can be split again if needed.

**Affects.** Reaction table 96,500 → 95,828; date table 96,935 → 95,828.

**Implemented in.** `clean_reactions.py` and `clean_dates.py` — the `groupby`
calls.

---

## 10. Outcome as a single graded value

**Decision.** Where a collapsed row carries several outcomes, `Outcome` holds
the most severe one and `Outcome_all` keeps the full list. Severity order:

> Died > Not recovered > Recovered with sequelae > Recovering > Recovered > Unknown

**Rationale.** Merging outcomes into one pipe-separated field would break the
column as a categorical feature, giving the model dozens of compound classes
instead of six. Where two episodes of the same reaction ended differently, the
more severe one is the accurate description of the case.

The placement of "Recovered with sequelae" was discussed: it denotes a final
state with permanent harm, so it ranks above "Recovering", whose trajectory is
still open. Ranking it below "Not recovered" is the team's judgement, on the
basis that an unresolved case may still worsen — recorded here as an
assumption rather than a settled fact. It affects 674 rows, under 1%.

The ranking is checked against the values actually present in the column at
run time, and any unranked value raises a warning rather than failing
silently. No warning was raised: the column holds exactly the six expected
values with no spelling variants.

**Implemented in.** `clean_reactions.py` — the `severity_order` list and the
`most_severe` function.

---

## Items flagged rather than corrected

Nothing that looks wrong is silently edited or deleted, so the original data
stays recoverable.

**UMC codes mapping to several MedDRA terms.** A UMC code is a fixed
identifier for one MedDRA term, so a code appearing against two different
terms points to a small ordering inconsistency in the source. 12 codes,
affecting 499 rows, flagged in `code_term_mismatch` — below 0.1% of the data.
This check also serves as independent confirmation that position-based
alignment holds across the rest.

**Invalid date sequence.** Report ID 45048 records an end date of 2022-11-17
against a start date of 2023-11-17. Flagged in `date_sequence_invalid`, not
corrected, since there is no way to tell which of the two years is wrong.


