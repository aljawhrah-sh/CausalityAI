import pandas as pd 
import re 
from collections import Counter

df = pd.read_excel("file_new_ids.xlsx", sheet_name="Causality")
col = "Causality assessment, method, source"

def split_assessments(cell):
    if pd.isna(cell):
        return []
    text = re.sub(r'(_x000D_)+', '\n', str(cell))
    parts = [p.strip() for p in text.split('\n') if p.strip()]
    return parts

# Count the number of assessments per cell
df["n_assessments"] = df[col].apply(lambda x: len(split_assessments(x)))

print("Distribution of assessments per cell:")
print(df["n_assessments"].value_counts().sort_index())
print("\nTotal rows:", len(df))
print("Empty cells:", df[col].isna().sum())

methods = []
for cell in df[col].dropna():
    for a in split_assessments(cell):
        fields = a.split(',', 2)
        if len(fields) >= 2:
            methods.append(fields[1].strip())

method_counts = Counter(methods)
print("All methods found (top 40):")
for method, count in method_counts.most_common(40):
    print(f"{count:>7}  |  {method}")


verdicts = []
for cell in df[col].dropna():
    for a in split_assessments(cell):
        fields = a.split(',', 2)
        if len(fields) >= 2 and "WHO-UMC" in fields[1]:
            verdicts.append(fields[0].strip())

verdict_counts = Counter(verdicts)
print("All WHO-UMC verdicts found:")
for verdict, count in verdict_counts.most_common(50):
    print(f"{count:>7}  |  {verdict}")


who_variants = Counter()

for cell in df[col].dropna():
    for a in split_assessments(cell):
        fields = a.split(',', 2)
        if len(fields) >= 2:
            method = fields[1].strip()
            if re.search(r'WHO|OMS|ВОЗ|ОМС', method, re.IGNORECASE):
                who_variants[method] += 1

print("\nAll WHO/OMS method variants found:")
for method, count in who_variants.most_common():
    print(f"{count:>7}  |  {method}")

print("\nTotal WHO/OMS-related assessments:", sum(who_variants.values()))