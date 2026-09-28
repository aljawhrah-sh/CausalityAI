import pandas as pd
import re
from collections import Counter

df_case = pd.read_excel("file_new_ids.xlsx", sheet_name="Case")


def split_cell(cell):
    if pd.isna(cell):
        return []
    text = re.sub(r'(_x000D_)+', '\n', str(cell))
    return [p.strip() for p in text.split('\n') if p.strip()]

df_case["n_reactions"] = df_case["MedDRA preferred term"].apply(lambda x: len(split_cell(x)))

col_start = "Start date"
col_end = "End date.1"

print("Start date — non-empty:", df_case[col_start].notna().sum())
print("End date.1 — non-empty:", df_case[col_end].notna().sum())

df_case["n_start"] = df_case[col_start].apply(lambda x: len(split_cell(x)))
df_case["n_end"] = df_case[col_end].apply(lambda x: len(split_cell(x)))

print("\nStart date count == reaction count:", (df_case["n_start"] == df_case["n_reactions"]).sum())
print("End date count == reaction count:", (df_case["n_end"] == df_case["n_reactions"]).sum())

# Count the unique start date values (after splitting the stacked values) and show a sample of 40
start_dates = Counter()
for cell in df_case[col_start].dropna():
    for d in split_cell(cell):
        start_dates[d] += 1

print(f"\nUnique start date values: {len(start_dates)}")
print("\nSample of 40:")
for val, count in list(start_dates.items())[:40]:
    print(f"{count:>6}  |  {val}")


# distinguish between full dates, month-level dates, year-level dates, and other formats
def date_precision(d):
    d = str(d).strip()
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}', d):
        return "full (YYYY-MM-DD)"
    if re.fullmatch(r'\d{4}-\d{2}', d):
        return "month (YYYY-MM)"
    if re.fullmatch(r'\d{4}', d):
        return "year (YYYY)"
    return "other"


start_precision = Counter()
for cell in df_case[col_start].dropna():
    for d in split_cell(cell):
        start_precision[date_precision(d)] += 1

print("Start date precision:")
for k, v in start_precision.most_common():
    print(f"{v:>7}  |  {k}")

# non-standard start date values (not full, month-level, or year-level)
print("\nNon-standard start date values:")
odd = [d for d in start_dates if date_precision(d) == "other"]
print(f"Count: {len(odd)}")
for d in odd[:20]:
    print(" ", d)

# how many rows have a different number of start/end dates than reactions?
diff_start = df_case[df_case["n_start"] != df_case["n_reactions"]]
print("\nStart date — fewer than reactions:",
      (diff_start["n_start"] < diff_start["n_reactions"]).sum())
print("Start date — more than reactions:",
      (diff_start["n_start"] > diff_start["n_reactions"]).sum())

diff_end = df_case[df_case["n_end"] != df_case["n_reactions"]]
print("\nEnd date — fewer than reactions:",
      (diff_end["n_end"] < diff_end["n_reactions"]).sum())
print("End date — more than reactions:",
      (diff_end["n_end"] > diff_end["n_reactions"]).sum())