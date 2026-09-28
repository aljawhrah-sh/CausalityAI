# Cleaning decisions

Decisions applied when cleaning the causality and reaction columns, with the
rationale behind each and the number of rows affected.

All decisions below were put to the authority and confirmed without changes.

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

**Affects.** 1,759 rows removed; 22,043 retained.

**Implemented in.** `clean_causality.py` — the `drop_duplicates` call.

---

## 4. Outcomes with no corresponding reaction

**Decision.** Discard outcomes that have no reaction to attach to.

**Rationale.** An outcome describes what happened to a specific reaction. Where
the reaction columns are empty but an outcome is recorded, there is nothing for
the outcome to describe and no way to recover what the reaction was.

**Affects.** 385 rows.

**Implemented in.** `clean_reactions.py` — the filter on `meddra_term.notna()`.

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
In the output: 12,110 rows flagged `start_unaligned`, 8,059 flagged
`end_unaligned`.

**Second decision.** Partial dates are kept as recorded rather than padded to
a full date — year-and-month (5,902) and year-only (4,489) — with a precision
column recording the level of detail available.

**Implemented in.** `clean_dates.py` — the `start_aligned` / `end_aligned`
conditions.

---

## 6. Level at which "first assessment" applies

**Decision.** Take the first WHO-UMC assessment per row, i.e. per drug–event
pair, rather than per case.

**Rationale.** In pharmacovigilance, causality is assessed for each drug–event
pair separately: within one case, one drug may be strongly linked to a given
reaction while another is not. The authority's framing of the question ("for
the same drug–event pair") supports this reading.

**Affects.** 22,043 rows. Applying it per case would yield roughly 12,377.

**Implemented in.** `clean_causality.py` — the `break` in the build loop.

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

---

## Notes passed to other team members

**Completeness score.** One row in the Case sheet holds "Yes" in a column that
otherwise contains decimal values between 0 and 1.

**Number of Suspect/Interacting drugs.** Records 48 drugs for report ID 6,
against the 4 drugs actually present in that case.
