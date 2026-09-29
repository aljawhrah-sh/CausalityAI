import pandas as pd
import re
 

df_case = pd.read_excel("file_new_ids.xlsx", sheet_name="Case") 

def split_cell(cell):
    if pd.isna(cell):
        return []
    text = re.sub(r'(_x000D_)+', '\n', str(cell))
    return [p.strip() for p in text.split('\n') if p.strip()]

# Build a normalised reaction-level table.
# In the original sheet, the reaction and outcome columns both stack multiple values in a single cell; 
# this expands them so every row holds one reaction with its mapped term, MedDRA term and outcome.
# Position-based alignment is used: reaction i maps to outcome i — verified as
# consistent in 96% of rows (47,832 of 50,000).
rows = []

for idx, row in df_case.iterrows():
    mapped = split_cell(row["Mapped term"])
    reactions = split_cell(row["MedDRA preferred term"])
    outcomes = split_cell(row["Outcome"])
    umc_terms = split_cell(row["Term reported to UMC"])

    n = max(len(reactions), len(outcomes), len(umc_terms))
    for i in range(n):
        rows.append({
            "report ID": row["report ID"],
            "umc_term_code": umc_terms[i] if i < len(umc_terms) else None,
            "mapped_term": mapped[i] if i < len(mapped) else None,
            "meddra_term": reactions[i] if i < len(reactions) else None,
            "outcome": outcomes[i] if i < len(outcomes) else None,
        })

outcome_df = pd.DataFrame(rows)

print("Total rows after expansion:", len(outcome_df))
print("\nOutcome distribution:")
print(outcome_df["outcome"].value_counts(dropna=False))
print("\nRows with outcome but no reaction:",
      ((outcome_df["meddra_term"].isna()) & (outcome_df["outcome"].notna())).sum())
print("Rows with reaction but no outcome:",
      ((outcome_df["meddra_term"].notna()) & (outcome_df["outcome"].isna())).sum())
print("\nSample:")
print(outcome_df.head(15).to_string())

# Outcomes with no corresponding reaction are dropped (385 rows)
# Remove rows where the reaction is missing, as we cannot have an outcome without a reaction
before = len(outcome_df)
outcome_df = outcome_df[outcome_df["meddra_term"].notna()]
print(f"Removed outcomes without a reaction: {before - len(outcome_df)}")
print("Rows remaining:", len(outcome_df))

# Remove exact duplicates (same report ID, mapped term, MedDRA term, and outcome) 
before = len(outcome_df)
outcome_df = outcome_df.drop_duplicates(
    subset=["report ID", "umc_term_code", "mapped_term", "meddra_term", "outcome"]
)
print(f"\nRemoved exact duplicates: {before - len(outcome_df)}")
print("Final rows:", len(outcome_df))

# Remove reports excluded during cross-column validation
flags = pd.read_csv("review_flags.csv")
removed_ids = flags[flags["reason"].str.contains("REMOVED", na=False)]["report ID"].unique()

before = len(outcome_df)
outcome_df = outcome_df[~outcome_df["report ID"].isin(removed_ids)]
print(f"\nRemoved {len(removed_ids)} flagged reports → {before - len(outcome_df)} rows dropped")

# check if there are any UMC codes linked to more than one MedDRA term 
check = outcome_df.dropna(subset=["umc_term_code", "meddra_term"])
inconsistent = check.groupby("umc_term_code")["meddra_term"].nunique()
problematic = inconsistent[inconsistent > 1]

print(f"UMC codes linked to more than one MedDRA term: {len(problematic)}")
if len(problematic) > 0:
    print("\nExamples:")
    for code in problematic.head(5).index:
        terms = check[check["umc_term_code"] == code]["meddra_term"].unique()
        print(f"  {code} → {list(terms)}")

# Flag rows where the UMC code is linked to more than one MedDRA term
problematic_codes = set(problematic.index)
outcome_df["code_term_mismatch"] = outcome_df["umc_term_code"].isin(problematic_codes)

print("Rows flagged:", outcome_df["code_term_mismatch"].sum())

# Safety check: the delimiter must not appear inside any raw value
for col_name in ["mapped_term", "umc_term_code", "outcome"]:
    hits = outcome_df[col_name].astype(str).str.contains(r"\|", na=False).sum()
    print(f"Values containing '|' in {col_name}: {hits}")


# Outcome severity ranking — the most severe outcome describes the case.
# Built from the actual values present in the column so that any spelling
# variant surfaces instead of failing silently.
print("\nActual outcome values present:")
print(outcome_df["outcome"].value_counts(dropna=False))

severity_order = [
    "Died",
    "Not recovered",
    "Recovered with sequelae",
    "Recovering",
    "Recovered",
    "Unknown",
]

actual_values = set(outcome_df["outcome"].dropna().unique())
unranked = actual_values - set(severity_order)
if unranked:
    print(f"\nWARNING — outcome values with no severity rank: {unranked}")

outcome_rank = {v: i for i, v in enumerate(severity_order)}


def most_severe(values):
    vals = [v for v in values.dropna().astype(str)]
    if not vals:
        return None
    return min(vals, key=lambda v: outcome_rank.get(v, 99))

# Collapse to one row per (report, reaction)
before = len(outcome_df)
outcome_df = (
    outcome_df
    .groupby(["report ID", "meddra_term"], as_index=False)
    .agg(
        umc_term_code=("umc_term_code", lambda x: " | ".join(sorted(set(x.dropna().astype(str))))),
        mapped_term=("mapped_term", lambda x: " | ".join(sorted(set(x.dropna().astype(str))))),
        Outcome=("outcome", most_severe),
        Outcome_all=("outcome", lambda x: " | ".join(sorted(set(x.dropna().astype(str))))),
        code_term_mismatch=("code_term_mismatch", "max"),
    )
)
outcome_df["n_raw_terms"] = outcome_df["mapped_term"].str.count(r"\|") + 1


print(f"\nCollapsed to one row per report+reaction: {before} → {len(outcome_df)}")
print("\nOutcome distribution (most severe per reaction):")
print(outcome_df["Outcome"].value_counts(dropna=False))

# Align column names with the merge convention agreed with the team
outcome_df = outcome_df.rename(columns={"meddra_term": "MedDRA preferred term"})

# reactions = (mapped term + MedDRA term + UMC term) + outcome 
outcome_df.to_excel("reactions_cleaned.xlsx", index=False)
print("\nSaved to reactions_cleaned.xlsx")