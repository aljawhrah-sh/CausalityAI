"""
Join the five cleaned tables into one model-ready table.

Grain
-----
One row per WHO-UMC assessed drug-event pair, which is the grain of
`causality_cleaned.xlsx`. That table carries the label, so it defines the shape
of the output: every join is a LEFT join onto it, and the row count must come
out unchanged. Nothing is allowed to add rows.

Why the row count is asserted after every join
----------------------------------------------
A merge key that is not unique on the right-hand side multiplies rows silently.
Pandas does not warn. The table still looks reasonable, the model still trains,
and every count, class balance and metric downstream is wrong by whatever factor
the duplication introduced. This has already happened twice on this project —
once at 1.61x during an earlier merge, and once at 1.095x from the drug table
before `drug_level_for_merge.py` existed.

So each join asserts. A failure here stops the pipeline with a clear message,
which is cheap. The alternative is a quietly wrong model, which is not.

Run:  python3 build_model_table.py
Out:  model_table.csv  +  model_table_report.txt
"""

import os
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "model_table.csv")
LOG = os.path.join(HERE, "model_table_report.txt")

CAUSALITY = os.path.join(HERE, "Data_Cleaning", "outputs", "causality_cleaned.xlsx")
REACTIONS = os.path.join(HERE, "Data_Cleaning", "outputs", "reactions_cleaned.xlsx")
DATES = os.path.join(HERE, "Data_Cleaning", "outputs", "reaction_dates_cleaned.xlsx")
CASE = os.path.join(HERE, "case_level_clean.csv")
DRUG = os.path.join(HERE, "drug_level_for_merge.csv")

report = []


def note(line=""):
    print(line)
    report.append(line)


def join(left, right, on, name, expected_rows):
    """Left join, then prove nothing was added, dropped or multiplied."""
    if right.duplicated(on).any():
        dupes = int(right.duplicated(on).sum())
        raise SystemExit(
            f"\nSTOP: {name} is not unique on {on} ({dupes:,} duplicate keys).\n"
            f"Joining it would multiply rows. Collapse it to one row per key first\n"
            f"- see drug_level_for_merge.py for how the drug table was handled."
        )
    merged = left.merge(right, on=on, how="left")
    matched = merged[right.columns.difference(on)[0]].notna().sum()
    note(f"  {name:<26} {len(merged):>7,} rows   matched {matched:>7,} "
         f"({matched / len(merged):.1%})")
    if len(merged) != expected_rows:
        raise SystemExit(
            f"\nSTOP: joining {name} changed the row count "
            f"({expected_rows:,} -> {len(merged):,}).\n"
            f"The output must stay at one row per assessed drug-event pair."
        )
    return merged


# ----------------------------------------------------------------- load ----
note("=== Inputs ===")
caus = pd.read_excel(CAUSALITY)
case = pd.read_csv(CASE, low_memory=False)
drug = pd.read_csv(DRUG, low_memory=False)
reac = pd.read_excel(REACTIONS)
date = pd.read_excel(DATES)
for name, df in [("causality (labels)", caus), ("case level", case),
                 ("drug level (merge-safe)", drug), ("reactions", reac),
                 ("reaction dates", date)]:
    note(f"  {name:<26} {len(df):>7,} rows  {len(df.columns):>3} cols")

n = len(caus)
note(f"\nTarget grain: {n:,} rows (one per WHO-UMC assessed drug-event pair)")

# Drop the reaction-date columns that duplicate names in the reaction table.
date = date.drop(columns=[c for c in date.columns
                          if c in reac.columns and c not in
                          ["report ID", "MedDRA preferred term"]])

# ----------------------------------------------------------------- join ----
note("\n=== Joins (each asserts the row count) ===")
m = caus.copy()
m = join(m, case, ["report ID"], "case level", n)
m = join(m, drug, ["report ID", "WHODrug active ingredient variant"],
         "drug level", n)
m = join(m, reac, ["report ID", "MedDRA preferred term"], "reactions", n)
m = join(m, date, ["report ID", "MedDRA preferred term"], "reaction dates", n)
note(f"\n  all joins held at {len(m):,} rows  [PASS]")

# ------------------------------------------------------------- numerics ----
# case_level_clean.csv stores "Unknown" in the same column as the numbers, so
# these arrive as text. Converted here, with the missing count recorded: a
# model needs a real NaN, not the string "Unknown".
note("\n=== Numeric coercion ===")
for col in ["Age", "Weight (kg)", "Height (cm)", "Completeness score",
            "Number of Suspect/Interacting drugs", "n_raw_terms", "n_drug_rows"]:
    if col in m.columns:
        before = m[col].notna().sum()
        m[col] = pd.to_numeric(m[col], errors="coerce")
        note(f"  {col:<36} numeric for {m[col].notna().sum():>6,} rows "
             f"({before - m[col].notna().sum():,} were 'Unknown' or unparseable)")

m = m.rename(columns={"Age": "age_years", "verdict_normalized": "label"})

# ------------------------------------------------------------- the label ----
note("\n=== Label ===")
for k, v in m["label"].value_counts().items():
    note(f"  {k:<28} {v:>7,}  ({v / len(m):.1%})")
counts = m["label"].value_counts()
note(f"\n  imbalance (largest : smallest) = {counts.iloc[0] / counts.iloc[-1]:.0f} : 1")
note(f"  reports represented: {m['report ID'].nunique():,}")
note(f"  rows per report    : {len(m) / m['report ID'].nunique():.2f}  "
     f"<- the reason Phase 2 splits by report, not by row")

# ------------------------------------------- what the model has to work with ----
note("\n=== WHO-UMC criteria coverage ===")
for col in ["dechallenge_performed", "reaction_resolved", "rechallenge_performed",
            "reaction_recurred", "time_to_onset_bucket"]:
    known = (m[col] != "Unknown").sum()
    note(f"  {col:<24} known on {known:>7,} rows  ({known / len(m):.0%})")

note("\n=== Missingness across all columns (worst 12) ===")
miss = m.isna().mean().sort_values(ascending=False)
for col, frac in miss.head(12).items():
    note(f"  {col:<40} {frac:>6.1%} missing")

m.to_csv(OUT, index=False, encoding="utf-8-sig")
note(f"\n=== Output ===")
note(f"  {len(m):,} rows x {len(m.columns)} columns -> {os.path.basename(OUT)}")

with open(LOG, "w") as f:
    f.write("\n".join(report) + "\n")
print(f"\nReport written to {os.path.basename(LOG)}")
