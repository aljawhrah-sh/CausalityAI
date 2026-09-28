import pandas as pd 
import re 
from collections import Counter

df_case = pd.read_excel("file_new_ids.xlsx", sheet_name="Case")

def split_cell(cell):
    if pd.isna(cell):
        return []
    text = re.sub(r'(_x000D_)+', '\n', str(cell))
    return [p.strip() for p in text.split('\n') if p.strip()]

# count the number of reactions so that we can compare it with the number of UMC terms  
df_case["n_reactions"] = df_case["MedDRA preferred term"].apply(lambda x: len(split_cell(x)))

col_umc = "Term reported to UMC"

print("Non-empty cells:", df_case[col_umc].notna().sum())
print("Empty cells:", df_case[col_umc].isna().sum())

# Count the number of UMC terms per cell, to see if they match the number of reactions
df_case["n_umc_terms"] = df_case[col_umc].apply(lambda x: len(split_cell(x)))

print("\nUMC term count == reaction count:",
      (df_case["n_umc_terms"] == df_case["n_reactions"]).sum())
print("Counts differ:",
      (df_case["n_umc_terms"] != df_case["n_reactions"]).sum())

print("\nDistribution of UMC terms per cell:")
print(df_case["n_umc_terms"].value_counts().sort_index().head(20))

print("\nSample of raw values:")
print(df_case[col_umc].dropna().head(15).to_string())