import pandas as pd
import re

df_case = pd.read_excel("file_new_ids.xlsx", sheet_name="Case")


def split_cell(cell):
    if pd.isna(cell):
        return []
    text = re.sub(r'(_x000D_)+', '\n', str(cell))
    return [p.strip() for p in text.split('\n') if p.strip()]


col_start = "Start date"
col_end = "End date.1"


# Build the reaction date table.
# Dates are aligned to reactions by position only where the counts match;
# otherwise they are left unassigned and flagged, since a partial date list
# gives no reliable way to tell which reaction each date belongs to.
date_rows = []

for idx, row in df_case.iterrows():
    reactions = split_cell(row["MedDRA preferred term"])
    starts = split_cell(row[col_start])
    ends = split_cell(row[col_end])

    # Alignment is only reliable when the counts match
    start_aligned = len(starts) == len(reactions) and len(reactions) > 0
    end_aligned = len(ends) == len(reactions) and len(reactions) > 0

    for i in range(len(reactions)):
        date_rows.append({
            "report ID": row["report ID"],
            "meddra_term": reactions[i],
            "reaction_start": starts[i] if start_aligned else None,
            "reaction_end": ends[i] if end_aligned else None,
            "start_unaligned": (not start_aligned) and len(starts) > 0,
            "end_unaligned": (not end_aligned) and len(ends) > 0,
        })

dates_df = pd.DataFrame(date_rows)

print("Total rows:", len(dates_df))
print("Rows with a start date:", dates_df["reaction_start"].notna().sum())
print("Rows with an end date:", dates_df["reaction_end"].notna().sum())
print("\nRows where start dates exist but could not be aligned:",
      dates_df["start_unaligned"].sum())
print("Rows where end dates exist but could not be aligned:",
      dates_df["end_unaligned"].sum())


# Classify how precise each date is (day / month / year)
def date_precision(d):
    if pd.isna(d):
        return None
    d = str(d).strip()
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}', d):
        return "day"
    if re.fullmatch(r'\d{4}-\d{2}', d):
        return "month"
    if re.fullmatch(r'\d{4}', d):
        return "year"
    return "other"


dates_df["start_precision"] = dates_df["reaction_start"].apply(date_precision)
dates_df["end_precision"] = dates_df["reaction_end"].apply(date_precision)

print("\nStart date precision:")
print(dates_df["start_precision"].value_counts(dropna=False))


# Check logical sequencing — only meaningful for full dates
full_dates = dates_df[
    (dates_df["start_precision"] == "day") & (dates_df["end_precision"] == "day")
].copy()

full_dates["start_dt"] = pd.to_datetime(full_dates["reaction_start"], errors="coerce")
full_dates["end_dt"] = pd.to_datetime(full_dates["reaction_end"], errors="coerce")

invalid = (full_dates["end_dt"] < full_dates["start_dt"]).sum()
print(f"\nRows where end date precedes start date: {invalid}")

if invalid > 0:
    print("\nExamples:")
    print(full_dates[full_dates["end_dt"] < full_dates["start_dt"]][
        ["report ID", "meddra_term", "reaction_start", "reaction_end"]
    ].head(10).to_string())

# Flag rows where the end date precedes the start date
dates_df["date_sequence_invalid"] = False

invalid_idx = full_dates[full_dates["end_dt"] < full_dates["start_dt"]].index
dates_df.loc[invalid_idx, "date_sequence_invalid"] = True

print("\nRows flagged for invalid date sequence:",
      dates_df["date_sequence_invalid"].sum())

# Remove reports excluded during cross-column validation
flags = pd.read_csv("review_flags.csv")
removed_ids = flags[flags["reason"].str.contains("REMOVED", na=False)]["report ID"].unique()

before = len(dates_df)
dates_df = dates_df[~dates_df["report ID"].isin(removed_ids)]
print(f"\nRemoved {len(removed_ids)} flagged reports → {before - len(dates_df)} rows dropped")

# Collapse to one row per (report, reaction): earliest start, latest end,
# so the row spans the full episode
before = len(dates_df)
dates_df = (
    dates_df
    .groupby(["report ID", "meddra_term"], as_index=False)
    .agg({
        "reaction_start": "min",
        "reaction_end": "max",
        "start_unaligned": "max",
        "end_unaligned": "max",
        "start_precision": "first",
        "end_precision": "first",
        "date_sequence_invalid": "max",
    })
)
print(f"Collapsed to one row per report+reaction: {before} → {len(dates_df)}")

# Align column names with the merge convention agreed with the team
dates_df = dates_df.rename(columns={
    "meddra_term": "MedDRA preferred term",
    "reaction_start": "Reaction start date",
    "reaction_end": "Reaction end date",
})

dates_df.to_excel("reaction_dates_cleaned.xlsx", index=False)
print("\nSaved to reaction_dates_cleaned.xlsx")
