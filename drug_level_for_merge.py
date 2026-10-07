"""
Drug-level table collapsed to one row per (report ID, drug), for merging.

Why this file exists
--------------------
`drug_level_clean.csv` is keyed on (report ID, drug_index), which is correct for
the drug data itself: a case genuinely can list the same active ingredient
several times, with a different dose or route each time. Report 6 lists Atropine
on 29 separate rows.

But the causality table is keyed on (report ID, drug, reaction). Merging the two
on (report ID, drug) therefore multiplies rows — 21,995 labelled assessments
become 24,082, a 9.5% inflation, and every count, distribution and metric built
on top of it is wrong by that much.

This script collapses the drug table to one row per (report ID, drug) so the
merge is one-to-one. Nothing is deleted: `drug_level_clean.csv` stays as it is
and remains the source of truth for drug-level questions.

Collapsing rules
----------------
Role, Action taken   most informative value wins, by a fixed priority
Drug start date      earliest known date  (the episode's true beginning)
Drug end date        latest known date    (the episode's true end)
everything else      the single known value if the rows agree, else "Multiple"

Run:  python3 drug_level_for_merge.py
Out:  drug_level_for_merge.csv  (one row per report ID + drug)
"""

import os
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
IN = os.path.join(HERE, "drug_level_clean.csv")
OUT = os.path.join(HERE, "drug_level_for_merge.csv")

KEY = ["report ID", "WHODrug active ingredient variant"]
UNKNOWN = "Unknown"

# Suspect outranks Interacting outranks Concomitant: if a drug is listed as
# suspect anywhere in the case, that is the role that matters for causality.
ROLE_PRIORITY = ["Suspect", "Interacting", "Concomitant"]

# "Drug withdrawn" is the dechallenge signal, so it must survive the collapse;
# a row that also says "Dose not changed" elsewhere must not hide it.
ACTION_PRIORITY = ["Drug withdrawn", "Dose reduced", "Dose increased",
                   "Dose not changed", "Not applicable"]

PASSTHROUGH = ["Indication", "Dose", "Dose unit", "Dosage regimen",
               "Route of admin."]


def by_priority(values, priority):
    """First value in priority order that is present; else Unknown."""
    present = {str(v).strip() for v in values}
    for p in priority:
        if p in present:
            return p
    other = present - {UNKNOWN, "nan", ""}
    return sorted(other)[0] if other else UNKNOWN


def single_or_multiple(values):
    """The one known value if the rows agree, else 'Multiple'.

    'Multiple' is deliberate: silently picking one dose out of three would look
    like data and be a guess. A reader can see 'Multiple' and go back to
    drug_level_clean.csv for the detail.
    """
    known = {str(v).strip() for v in values} - {UNKNOWN, "nan", ""}
    if not known:
        return UNKNOWN
    if len(known) == 1:
        return known.pop()
    return "Multiple"


def earliest(values):
    known = sorted(v for v in (str(x).strip() for x in values)
                   if v not in (UNKNOWN, "nan", ""))
    return known[0] if known else UNKNOWN


def latest(values):
    known = sorted(v for v in (str(x).strip() for x in values)
                   if v not in (UNKNOWN, "nan", ""))
    return known[-1] if known else UNKNOWN


def main():
    drug = pd.read_csv(IN, low_memory=False)
    print(f"drug_level_clean.csv : {len(drug):,} rows")
    print(f"unique (report, drug): {len(drug.drop_duplicates(KEY)):,}")

    agg = {
        "Role": lambda s: by_priority(s, ROLE_PRIORITY),
        "Action taken with drug": lambda s: by_priority(s, ACTION_PRIORITY),
        "Drug start date": earliest,
        "Drug end date": latest,
        "drug_index": lambda s: int(s.min()),
    }
    for col in PASSTHROUGH:
        agg[col] = single_or_multiple

    out = drug.groupby(KEY, as_index=False, sort=False).agg(agg)
    out["n_drug_rows"] = drug.groupby(KEY, sort=False).size().values
    out["collapsed_values"] = out[PASSTHROUGH].eq("Multiple").any(axis=1)

    assert not out.duplicated(KEY).any(), "still not unique on the merge key"
    print(f"\ndrug_level_for_merge : {len(out):,} rows  (unique on {KEY})")
    print(f"rows that collapsed more than one source row: "
          f"{(out['n_drug_rows'] > 1).sum():,}")
    print(f"rows where a field held conflicting values -> 'Multiple': "
          f"{out['collapsed_values'].sum():,}")

    print("\nRole after collapsing:")
    print(out["Role"].value_counts().to_string())
    print("\nAction taken with drug after collapsing:")
    print(out["Action taken with drug"].value_counts().to_string())

    out.to_csv(OUT, index=False, encoding="utf-8-sig")
    print(f"\nSaved to {OUT}")

    # Prove the merge is now one-to-one against the label table.
    caus_path = os.path.join(HERE, "Data_Cleaning", "outputs", "causality_cleaned.xlsx")
    if os.path.exists(caus_path):
        caus = pd.read_excel(caus_path)
        merged = caus.merge(out, on=KEY, how="left")
        print(f"\nmerge check: causality {len(caus):,} rows x drug_level_for_merge "
              f"-> {len(merged):,} rows "
              f"{'[PASS]' if len(merged) == len(caus) else '[FAIL - still inflating]'}")


if __name__ == "__main__":
    main()
