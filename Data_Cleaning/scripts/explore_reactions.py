import pandas as pd
import re
from collections import Counter

df_case = pd.read_excel("file_new_ids.xlsx", sheet_name="Case")

print("Columns in Case sheet:")
for i, c in enumerate(df_case.columns):
    print(f"{i}: {c}")

print("\nTotal rows:", len(df_case))


col_outcome = "Outcome"

# 1. Count non-empty and empty cells, and unique raw values 
print("Non-empty Outcome cells:", df_case[col_outcome].notna().sum())
print("Empty Outcome cells:", df_case[col_outcome].isna().sum())
print("Unique raw values:", df_case[col_outcome].nunique())

# 2. the most frequent raw values (as it is, without splitting the stacked values)
print("\nTop 30 raw values:")
print(df_case[col_outcome].value_counts().head(30))


# 3. Split the stacked values within each cell
def split_cell(cell):
    if pd.isna(cell):
        return []
    text = re.sub(r'(_x000D_)+', '\n', str(cell))
    return [p.strip() for p in text.split('\n') if p.strip()]


df_case["n_outcomes"] = df_case[col_outcome].apply(lambda x: len(split_cell(x)))
print("\nDistribution of outcomes per cell:")
print(df_case["n_outcomes"].value_counts().sort_index())

# 4. Count the unique values after splitting the stacked values 
all_outcomes = Counter()
for cell in df_case[col_outcome].dropna():
    for o in split_cell(cell):
        all_outcomes[o] += 1

print(f"\nUnique outcome values after splitting: {len(all_outcomes)}")
print("\nAll values (top 50):")
for val, count in all_outcomes.most_common(50):
    print(f"{count:>7}  |  {val}")



# compare the number of outcomes with the number of reactions in each row, to see if they match 
df_case["n_outcomes"] = df_case["Outcome"].apply(lambda x: len(split_cell(x)))
df_case["n_reactions"] = df_case["MedDRA preferred term"].apply(lambda x: len(split_cell(x)))

match = (df_case["n_outcomes"] == df_case["n_reactions"]).sum()
mismatch = (df_case["n_outcomes"] != df_case["n_reactions"]).sum()

print("Rows where outcome count == reaction count:", match)
print("Rows where counts differ:", mismatch)

print("\nSample of mismatches:")
print(df_case[df_case["n_outcomes"] != df_case["n_reactions"]][
    ["report ID", "MedDRA preferred term", "Outcome", "n_reactions", "n_outcomes"]
].head(10).to_string())


diff = df_case[df_case["n_outcomes"] != df_case["n_reactions"]]

# Count the number of rows with zero outcomes 
zero_outcomes = (diff["n_outcomes"] == 0).sum()
print("Rows with reactions but NO outcomes at all:", zero_outcomes)

# Count the number of rows with fewer outcomes than reactions
fewer = ((diff["n_outcomes"] > 0) & (diff["n_outcomes"] < diff["n_reactions"])).sum()
print("Rows with fewer outcomes than reactions:", fewer)

# Count the number of rows with more outcomes than reactions
more = (diff["n_outcomes"] > diff["n_reactions"]).sum()
print("Rows with MORE outcomes than reactions:", more)

# Show examples where outcomes exceed reactions 
if more > 0:
    print("\nExamples where outcomes exceed reactions:")
    print(diff[diff["n_outcomes"] > diff["n_reactions"]][
        ["report ID", "n_reactions", "n_outcomes"]
    ].head(10).to_string())


diff = df_case[df_case["n_outcomes"] > df_case["n_reactions"]]

# is MedDRA empty but Mapped term has values?
diff_copy = diff.copy()
diff_copy["n_mapped"] = diff_copy["Mapped term"].apply(lambda x: len(split_cell(x)))

print("Rows where MedDRA is empty but Mapped term has values:")
print(((diff_copy["n_reactions"] == 0) & (diff_copy["n_mapped"] > 0)).sum())

print("\nSample:")
print(diff_copy[["report ID", "Mapped term", "MedDRA preferred term", "Outcome",
                 "n_mapped", "n_reactions", "n_outcomes"]].head(10).to_string())

