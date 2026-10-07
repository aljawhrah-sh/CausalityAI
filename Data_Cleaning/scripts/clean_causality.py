import pandas as pd
import re
from collections import Counter

df = pd.read_excel("file_new_ids.xlsx", sheet_name="Causality")
col = "Causality assessment, method, source"

# Define a mapping of verdict variants to six standardized verdicts
verdict_mapping = {
    # Certain
    "certain": "Certain", 
    "definida": "Certain", 
    "визначений": "Certain",

    # Probable/Likely
    "probable/likely": "Probable", 
    "probable": "Probable", 
    "імовірний": "Probable",
    "probable / likely": "Probable", 
    "вероятная": "Probable", 
    "likely": "Probable",

    # Possible
    "possible": "Possible", 
    "posible": "Possible", 
    "можливий": "Possible",
    "possível": "Possible", 

    # Unlikely
    "unlikely": "Unlikely", 
    "improbable": "Unlikely", 
    "improvável": "Unlikely",

    # Conditional
    "conditional/unclassified": "Conditional",
    "condicional/no clasificada": "Conditional",
    "conditional / unclassified": "Conditional",
    "unclassified": "Conditional", 
    "conditional/unclassifiable": "Conditional",

    # Unassessable
    "unassessable/unclassifiable": "Unassessable",
    "no evaluable/inclasificable": "Unassessable",
    "unassessable / unclassifiable": "Unassessable",
    "не підлягає класифікації": "Unassessable",
    "not assessable": "Unassessable", 
    "unassessable": "Unassessable",
    "not assessible": "Unassessable",


    # new variants of Probable/Likely and Certain that are not in the original mapping
    "probable/ likely": "Probable", 
    "достоверная": "Certain",

    # Terms outside the six WHO-UMC categories — excluded per authority guidance
    "unknown": "Excluded",
    "unk": "Excluded",
    "не визначений": "Excluded",
    "not assessed": "Excluded",
    "not reported": "Excluded",
    "8 - недостатньо інформації для оцін": "Excluded",

    "not applicable": "Excluded",
    "não aplicável": "Excluded",
    "n/a (dietary supplement)": "Excluded",
    "non-ae": "Excluded",

    "not related": "Excluded",
    "unlikely/not related": "Excluded",
    "reasonable possibility": "Excluded",
    "no reasonable possibility": "Excluded",
    "possivelmente relacionado": "Excluded",
    "possibly related": "Excluded",
    "probably related": "Excluded",
    "não relacionado": "Excluded",   

}

def normalize_verdict(verdict):
    key = verdict.strip().lower()
    return verdict_mapping.get(key, None) # Return None if the verdict is not in the mapping

def split_assessments(cell):
    if pd.isna(cell):
        return []
    text = re.sub(r'(_x000D_)+', '\n', str(cell))
    return [p.strip() for p in text.split('\n') if p.strip()]



unmapped = Counter()
mapped_count = 0

for cell in df[col].dropna():
    for a in split_assessments(cell):
        fields = a.split(',', 2)
        if len(fields) >= 2 and "WHO-UMC" in fields[1]:
            normalized = normalize_verdict(fields[0])
            if normalized:
                mapped_count += 1
            else:
                unmapped[fields[0].strip()] += 1

print("Successfully mapped verdicts:", mapped_count)
print("\nUnmapped verdicts (need decision):")
for v, c in unmapped.most_common():
    print(f"{c:>6}  |  {v}")


# build a cleaned table with one raw per WHO-UMC assessment, with normalized verdicts and original text for reference
cleaned_rows = []

for idx, row in df.iterrows():
    cell = row[col]
    if pd.isna(cell):
        continue

    selected = None # the first valid assessment 
     

    for a in split_assessments(cell):
        fields = a.split(',', 2)
        if len(fields) < 3:
            continue

        verdict_raw, method, source = [f.strip() for f in fields]

        if not re.search(r'UMC', method, re.IGNORECASE):
           continue

        normalized = normalize_verdict(verdict_raw)

        if normalized == "Excluded":
            continue  # skip excluded assessments

        if normalized is not None:
            selected = {
                "report ID": row["report ID"],
                "drug": row["WHODrug active ingredient variant"],
                "reaction": row["MedDRA preferred term"],
                "verdict_original": verdict_raw,
                "verdict_normalized": normalized,
                "method": method,
                "source": source,
                # The three WHO-UMC criteria columns. They live only on this
                # sheet, so if they are not carried here they are lost from the
                # whole pipeline — and they are what the framework assesses on.
                # Kept raw; normalised further down.
                "Time-to-onset": row["Time-to-onset"],
                "dechallenge_raw": row[
                    "Dechallenge performed? / Reaction resolved/resolving?"],
                "rechallenge_raw": row[
                    "Rechallenge performed? / Reaction recurred?"],
            }
            break  # the first valid assessment only — stop here

    if selected:
        cleaned_rows.append(selected)

cleaned_df = pd.DataFrame(cleaned_rows)

print("Rows in cleaned table:", len(cleaned_df))
print("\nVerdict distribution:")
print(cleaned_df["verdict_normalized"].value_counts())
print("\nSample:")
print(cleaned_df.head(10))

print("Total rows:", len(cleaned_df))
print("Unique report IDs:", cleaned_df["report ID"].nunique())
print("\nAssessments per report ID (distribution):")
print(cleaned_df["report ID"].value_counts().value_counts().sort_index())

#check : is the duplicated for the same report ID identical or different 
duplicated_ids = cleaned_df[cleaned_df.duplicated("report ID", keep=False)]
sample_id = duplicated_ids["report ID"].iloc[0]
print(f"\nExample — all rows for report ID {sample_id}:")
print(cleaned_df[cleaned_df["report ID"] == sample_id])

# check for exact duplicates in the cleaned table
exact_duplicates = cleaned_df.duplicated(
    subset=["report ID", "drug", "reaction", "verdict_normalized", "source"],
    keep=False
)
print("Exact duplicate rows:", exact_duplicates.sum())

# example of exact duplicates
print("\nExample of exact duplicates:")
print(cleaned_df[exact_duplicates].head(20))

# check for extreme cases where the same report ID has different verdicts, drugs, or reactions 
print("\nTop 5 report IDs by assessment count:")
top_ids = cleaned_df["report ID"].value_counts().head(5)
print(top_ids)

# display the biggest case 
biggest_id = top_ids.index[0]
print(f"\nAll rows for report ID {biggest_id} (first 20):")
print(cleaned_df[cleaned_df["report ID"] == biggest_id].head(20))


# is the drud realy one in every rows of the case , or is there different drugs 
case_6 = df[df["report ID"] == 6]
print("Rows for report ID 6 in original sheet:", len(case_6))
print("\nUnique drugs in report ID 6:")
print(case_6["WHODrug active ingredient variant"].unique())
print("\nUnique reactions in report ID 6:")
print(case_6["MedDRA preferred term"].unique())


# delete identical duplicates in the cleaned table 
before = len(cleaned_df)
cleaned_df = cleaned_df.drop_duplicates(
    subset=["report ID", "drug", "reaction", "verdict_normalized", "source"]
)
print(f"Before: {before} → After: {len(cleaned_df)}")
print("Removed:", before - len(cleaned_df))

print("\nUnique report IDs after dedup:", cleaned_df["report ID"].nunique())
print("\nVerdict distribution after dedup:")
print(cleaned_df["verdict_normalized"].value_counts())

# Remove reports excluded during cross-column validation (Pregnancy = Yes with Sex = Male)
flags = pd.read_csv("review_flags.csv")
removed_ids = flags[flags["reason"].str.contains("REMOVED", na=False)]["report ID"].unique()

before = len(cleaned_df)
cleaned_df = cleaned_df[~cleaned_df["report ID"].isin(removed_ids)]
print(f"\nRemoved {len(removed_ids)} flagged reports → {before - len(cleaned_df)} rows dropped")

# One assessment per drug-event pair: keep the first, as per the agreed rule
before = len(cleaned_df)
cleaned_df = cleaned_df.drop_duplicates(subset=["report ID", "drug", "reaction"], keep="first")
print(f"Resolved duplicate drug-event pairs: {before - len(cleaned_df)} rows dropped")

# Check whether the drug and reaction cells hold stacked values
multi = cleaned_df[cleaned_df["reaction"].astype(str).str.contains("_x000D_", na=False)]
print("Rows where reaction cell holds stacked values:", len(multi))
if len(multi) > 0:
    print(multi[["report ID", "drug", "reaction"]].head())

# check the number of unique sources in the cleaned table
unique_sources = cleaned_df["source"].dropna().unique()
print("Number of unique sources:", len(unique_sources))

pd.DataFrame({"source": sorted(unique_sources)}).to_excel(
    "unique_sources.xlsx", index=False
)
print("Saved to unique_sources.xlsx")

# classify the sources into categories based on keywords 
def classify_source(s):
    if pd.isna(s):
        return "Unknown"
    t = str(s).lower()

    # 1. Pharmacovigilance centres
    if re.search(
        r'^cefv/|\bcefv\b|\bcnfv\b|\bepvc\b|farmacovigilan|pharmacovigilan|'
        r'\bcrr\b|\brc\b|експерт',
        t
    ):
        return "Pharmacovigilance Centre"

    # 2. Company / Marketing Authorisation Holder
    if re.search(
        r'\bcompany\b|empresa|detentor de autoriza|\bmah\b|'
        r'pharma|farmaceutic|farmacéutic|laborator|\bgmbh\b|\bs\.p\.a\b|'
        r'drug safety|\b(alkaloid|biocodex|schülke|schulke|audifarma)\b',
        t
    ):
        return "Company/MAH"

    # 3. Reporter
    if re.search(r'\breporter\b|notificador|медичний спеціаліст', t):
        return "Reporter"

    # 4. National regulatory authorities
    if re.search(
        r'\b(anvisa|arcsa|anmat|cdsco|titck|invima|cofepris|nafdac|sfda|nppa|alims|anrp)\b|'
        r'drug regulatory authority|regulatory authority',
        t
    ):
        return "National Regulatory Authority"

    # 5. Regional health authorities
    if re.search(
        r'secretar|ministry|ministerio|dirección territorial|instituto departamental|'
        r'health directorate|district council|قطاع|\bet\s',
        t
    ):
        return "Regional Health Authority"

    # 6. Hospitals, clinics and healthcare providers
    if re.search(
        r'hospital|clinic|clínica|clinica|مستشفى|مركز|'
        r'medic|médic|salud|saúde|oncolog|oncolg|cardio|matern|'
        r'instituto|institute|fundaci|fundaç|asociaci|associaç|'
        r'caja de compensaci|caja colombiana|diagnostic|escanograf|'
        r'ips\b|\bese\b|\be\.s\.e|\bs\.a\.s|sas\b|\bc\.s\.\b|\bcnes\b|'
        r'^[a-z]{3,10}-\s?[a-z]',
        t
    ):
        return "Hospital/Clinic/Provider"

    return "Other"


cleaned_df["source_category"] = cleaned_df["source"].apply(classify_source)

print("\nSource category distribution:")
print(cleaned_df["source_category"].value_counts())

# Review what remains unclassified
other_sources = cleaned_df[cleaned_df["source_category"] == "Other"]["source"].unique()
print(f"\nUnique sources still 'Other': {len(other_sources)}")
print("\nSample:")
for s in sorted(other_sources)[:30]:
    print(" ", s)


# ---------------------------------------------------------------------------
# Normalise the three WHO-UMC criteria columns
#
# Dechallenge and rechallenge are each recorded as two questions packed into
# one cell, e.g. "Yes / No" = drug was withdrawn / reaction did not resolve.
# They are split because the two halves carry different meaning: "No / Yes"
# (reaction resolved without withdrawing the drug) argues AGAINST the drug,
# while "Yes / Yes" argues for it. Collapsed into one field those two look
# alike, which is exactly the mistake that has to be avoided.
# ---------------------------------------------------------------------------
PLACEHOLDERS = {"", "nan", "none", "-", "‒", "–", "—", "unknown", "unk"}


def split_pair(value):
    """'Yes / No' -> ('Yes', 'No'). Anything not a clear yes/no -> 'Unknown'."""
    text = str(value) if pd.notna(value) else ""
    halves = text.split("/")
    out = []
    for i in range(2):
        half = halves[i].strip().lower() if i < len(halves) else ""
        out.append({"yes": "Yes", "no": "No"}.get(half, "Unknown"))
    return out[0], out[1]


def tto_bucket(value):
    """Time-to-onset text -> coarse bucket. The exact figure is written many
    ways and in several units, so the bucket is what can be trusted."""
    t = str(value).strip().lower() if pd.notna(value) else ""
    if t in PLACEHOLDERS:
        return "Unknown"
    number = re.search(r"(\d+(?:[.,]\d+)?)", t)
    if not number:
        return "Unknown"
    val = float(number.group(1).replace(",", "."))
    if re.search(r"minute|\bmin\b|hour|\bhr\b|same day", t):
        return "same day"
    if re.search(r"day", t):
        days = val
    elif re.search(r"week", t):
        days = val * 7
    elif re.search(r"month", t):
        days = val * 30
    elif re.search(r"year", t):
        days = val * 365
    else:
        return "Unknown"
    if days < 1:
        return "same day"
    if days <= 7:
        return "1-7 days"
    if days <= 28:
        return "1-4 weeks"
    if days <= 182:
        return "1-6 months"
    return ">6 months"


dechal = cleaned_df["dechallenge_raw"].apply(split_pair)
cleaned_df["dechallenge_performed"] = [a for a, _ in dechal]
cleaned_df["reaction_resolved"] = [b for _, b in dechal]

rechal = cleaned_df["rechallenge_raw"].apply(split_pair)
cleaned_df["rechallenge_performed"] = [a for a, _ in rechal]
cleaned_df["reaction_recurred"] = [b for _, b in rechal]

cleaned_df["time_to_onset_bucket"] = cleaned_df["Time-to-onset"].apply(tto_bucket)

print("\nWHO-UMC criteria columns (now carried through):")
for col in ["dechallenge_performed", "reaction_resolved", "rechallenge_performed",
            "reaction_recurred", "time_to_onset_bucket"]:
    counts = cleaned_df[col].value_counts()
    print(f"  {col:<24} " + " | ".join(f"{k} {v:,}" for k, v in counts.items()))

# Align column names with the merge convention agreed with the team
cleaned_df = cleaned_df.rename(columns={
    "drug": "WHODrug active ingredient variant",
    "reaction": "MedDRA preferred term",
    "Time-to-onset": "time_to_onset_raw",
})

print("\nFinal verdict distribution:")
print(cleaned_df["verdict_normalized"].value_counts())

# save the cleaned table to an Excel file
cleaned_df.to_excel("causality_cleaned.xlsx", index=False)
print("Saved to causality_cleaned.xlsx")
print("Final rows:", len(cleaned_df))

