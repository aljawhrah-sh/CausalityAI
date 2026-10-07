"""
Student 1 — Patient & Drug Data Cleaning (Case sheet)
CausalityAI / SFDA data-cleaning pipeline

Scope (per team plan):
  - Age unit standardization (-> years)
  - Reporter qualification consistency + stacked-value detection
  - Number of suspect/interacting drugs vs. actual drug count check
  - Role standardization
  - Indication consistency (UK/US spelling variants merged, unknown-indication terms unified)
  - Logical range validation (age/weight/height) + outlier flagging
  - Split stacked dose/date cells (same _x000D_ logic as split_assessments)
  - Date format standardization -> YYYY-MM-DD
  - Missing-critical-data report (Age, Sex)

Output (same column names and order as the original Case sheet, except that
the drug dates are renamed "Drug start date" / "Drug end date" so they can't be
confused with the reaction dates "Start date" / "End date" when the sheets are merged):
  - case_level_clean.csv : one row per report ID, patient-level fields
  - drug_level_clean.csv : one row per (report ID, drug_index), drug-level fields
  - review_flags.csv     : log of every value that was changed or needs review, with the reason
Blank cells and bare dash placeholders are written as "Unknown".

Team decisions applied:
  - Cases with Pregnancy case = Yes AND Sex = Male (impossible combination) are
    removed from both output files and logged in review_flags.csv.
  - Only complete dates (YYYY-MM-DD) are kept; year+month or year-only -> "Unknown".
  - End date before Start date -> both dates of that drug set to "Unknown"
    (the case itself is kept).
"""

import re
import numpy as np
import pandas as pd

import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_PATH = os.path.join(SCRIPT_DIR, "file_new_ids.xlsx")
SHEET = "Case"

OUT_DIR = SCRIPT_DIR


# ---------------------------------------------------------------------------
# Shared helper (team-wide, from the split_assessments prototype)
# ---------------------------------------------------------------------------
def split_assessments(cell):
    """Splits a cell into separate stacked values based on the _x000D_ artifact.
    Returns [] for missing cells, otherwise a list of stripped, non-empty parts."""
    if pd.isna(cell):
        return []
    text = re.sub(r"(_x000D_)+", "\n", str(cell))
    return [p.strip() for p in text.split("\n") if p.strip()]


# ---------------------------------------------------------------------------
# 1) Age unit standardization -> years
# ---------------------------------------------------------------------------
AGE_UNIT_TO_YEARS = {
    "years": 1.0,
    "year": 1.0,
    "months": 1 / 12,
    "month": 1 / 12,
    "weeks": 1 / 52.1775,
    "week": 1 / 52.1775,
    "days": 1 / 365.25,
    "day": 1 / 365.25,
    "hours": 1 / (365.25 * 24),
    "hour": 1 / (365.25 * 24),
}


def standardize_age(age, unit):
    """Returns (age_in_years, status). status flags rows needing review."""
    if pd.isna(age):
        return np.nan, "missing_age"
    if pd.isna(unit):
        return np.nan, "missing_age_unit"
    unit_clean = str(unit).strip().lower()
    if unit_clean not in AGE_UNIT_TO_YEARS:
        # e.g. the '‒' placeholder seen in the data — don't guess, flag it
        return np.nan, f"unrecognized_age_unit:{unit_clean}"
    return round(age * AGE_UNIT_TO_YEARS[unit_clean], 4), "ok"


# ---------------------------------------------------------------------------
# 2) Date standardization -> YYYY-MM-DD
#    Team decision (final):
#      - full date (YYYY-MM-DD)  -> kept as-is
#      - anything incomplete (year+month, year only) or unparseable -> "Unknown"
# ---------------------------------------------------------------------------
DATE_FULL = re.compile(r"^\d{4}-\d{2}-\d{2}$")
DATE_YM = re.compile(r"^\d{4}-\d{2}$")


def standardize_date(raw):
    """Returns (value, status). value is 'YYYY-MM-DD' or 'Unknown'."""
    if pd.isna(raw):
        return "Unknown", "missing"
    raw = str(raw).strip()
    if DATE_FULL.match(raw):
        return raw, "full"
    if DATE_YM.match(raw):
        return "Unknown", "year_month_only"
    return "Unknown", "year_only_or_unparseable"


UNKNOWN_TOKENS = {"", "-", "‒", "–", "—"}


def to_unknown(value):
    """Blank cells and bare dash placeholders -> 'Unknown' (team decision)."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "Unknown"
    if isinstance(value, str) and value.strip() in UNKNOWN_TOKENS:
        return "Unknown"
    return value


# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------
def load_case_sheet():
    return pd.read_excel(RAW_PATH, sheet_name=SHEET)


# ---------------------------------------------------------------------------
# 3) Case-level (patient) cleaning
# ---------------------------------------------------------------------------
PATIENT_COLS = [
    "report ID", "Completeness score", "Reporter qualification", "Sex",
    "Age", "Age unit", "Age group", "Weight (kg)", "Height (cm)",
    "Serious", "Seriousness criteria", "Fatal", "Pregnancy case",
    "Number of Suspect/Interacting drugs",
]

VALID_AGE_RANGE = (0, 120)
VALID_WEIGHT_RANGE = (0.2, 300)   # kg — 0.2 covers premature neonates
VALID_HEIGHT_RANGE = (20, 250)    # cm


def fix_weight(w, age_years=None):
    """Returns (final_value, note). Corrects likely decimal/unit errors; anything
    still implausible after correction (or too small/zero to safely guess) -> 'Unknown'.
    Adults (18y+) with weight under 25kg are set to Unknown outright — even the
    least extreme of these fall below/at the edge of the lowest weight ever
    medically documented for a living adult of normal stature, so the value
    can't be trusted regardless of which specific number it is."""
    if pd.isna(w):
        return "Unknown", "missing"
    if w == 0 or w < VALID_WEIGHT_RANGE[0]:
        return "Unknown", "zero_or_too_small"
    if isinstance(age_years, (int, float)) and age_years >= 18 and w < 25:
        return "Unknown", f"adult weight implausibly low: {w}kg at age {age_years}y"
    if w > VALID_WEIGHT_RANGE[1]:
        if 500 <= w < 1000:
            fixed = round(w / 10, 2)
        else:
            fixed = round(w / 1000, 2)
        if VALID_WEIGHT_RANGE[0] <= fixed <= VALID_WEIGHT_RANGE[1]:
            return fixed, f"corrected from {w} (likely decimal/unit entry error)"
        return "Unknown", f"uncorrectable outlier: {w}"
    return w, "ok"


def fix_height(h, age_years):
    """Same idea as fix_weight, but height also needs to make sense for the
    patient's age — a /10 correction that is numerically in range but not a
    plausible human height for an adult (or an infant) is rejected -> 'Unknown'."""
    if pd.isna(h):
        return "Unknown", "missing"
    if h == 0 or h < VALID_HEIGHT_RANGE[0]:
        return "Unknown", "zero_or_too_small"
    if h > VALID_HEIGHT_RANGE[1]:
        fixed = round(h / 10, 1)
        # age-aware plausibility: infants (<2y) can be 40-100cm; everyone else
        # needs a fully adult/child-plausible height, not just "in range"
        if pd.notna(age_years) and isinstance(age_years, (int, float)) and age_years < 2:
            plausible = 40 <= fixed <= 100
        else:
            plausible = 100 <= fixed <= VALID_HEIGHT_RANGE[1]
        if plausible:
            return fixed, f"corrected from {h} (likely decimal entry error)"
        return "Unknown", f"uncorrectable outlier: {h} (fix {fixed} not plausible for age {age_years})"
    return h, "ok"


def clean_case_level(df):
    case = df[PATIENT_COLS].copy()
    flags = []  # (report_id, reason)

    # --- age standardization ---
    ages_units = case.apply(lambda r: standardize_age(r["Age"], r["Age unit"]), axis=1)
    raw_age_years = [a for a, _ in ages_units]
    age_note = [s for _, s in ages_units]

    final_age = []
    for a, note in zip(raw_age_years, age_note):
        if note == "ok" and VALID_AGE_RANGE[0] <= a <= VALID_AGE_RANGE[1]:
            final_age.append(a)
        else:
            final_age.append("Unknown")
    # --- age unit: reflects the unit of the standardized value we now store.
    #     Known age -> "years" (since that's what's in the standardized column).
    #     Unknown/blank/unrecognized original unit -> "Unknown". ---
    case["Age unit"] = ["years" if isinstance(a, (int, float)) else "Unknown" for a in final_age]

    # --- age group: derive from the standardized age using standard
    #     pharmacovigilance brackets when the original value is missing;
    #     keep the original value if present, but flag it if it conflicts
    #     with what the age itself implies. Unknown age -> Unknown group. ---
    def derive_age_group(age_years):
        if not isinstance(age_years, (int, float)):
            return "Unknown"
        if age_years < 28 / 365.25:
            return "Neonate"
        if age_years < 2:
            return "Infant"
        if age_years < 12:
            return "Child"
        if age_years < 18:
            return "Adolescent"
        if age_years < 65:
            return "Adult"
        return "Elderly"

    derived_groups = [derive_age_group(a) for a in final_age]
    for rid, raw_group, derived, age_val in zip(case["report ID"], case["Age group"], derived_groups, final_age):
        if pd.notna(raw_group) and isinstance(age_val, (int, float)) and raw_group != derived:
            flags.append((rid, f"Age group recorded as '{raw_group}' but age-derived group is "
                                f"'{derived}' (age = {age_val} years) — derived value used"))
    case["Age group"] = derived_groups

    # --- sex: missing -> Unknown ---
    case["Sex"] = case["Sex"].fillna("Unknown")

    # --- weight / height: zero and missing -> Unknown; large outliers corrected
    #     where the fix lands in a plausible range, else Unknown ---
    w_fixed = [fix_weight(w, a) for w, a in zip(case["Weight (kg)"], final_age)]
    case["Weight (kg)"] = [v for v, _ in w_fixed]
    w_notes = [n for _, n in w_fixed]

    # second pass: infants (<2y) whose weight is inside the generic 0.2-300kg
    # range but implausible for their age (e.g. 100kg for a 3-month-old) —
    # same decimal-shift pattern as the >300kg cases, just not caught by the
    # absolute range check. Confirmed against source data before correcting.
    # Plausibility is checked against approximate WHO weight-for-age bounds
    # (generous, ~1st-99th percentile) by age bucket, not just a flat cutoff —
    # a /10 fix is only kept if it actually lands in a sane range for that age;
    # otherwise the value is set to Unknown rather than kept wrong.
    def infant_weight_bounds(age_years):
        months = age_years * 12
        if months <= 1:
            return (2.0, 6.0)
        if months <= 3:
            return (3.0, 8.5)
        if months <= 6:
            return (4.0, 10.5)
        if months <= 12:
            return (5.5, 13.0)
        return (7.0, 16.0)  # 12-24 months

    corrected_weight = []
    for i, (age_val, w) in enumerate(zip(final_age, case["Weight (kg)"])):
        if isinstance(w, (int, float)) and isinstance(age_val, (int, float)) and age_val < 2 and w > 25:
            lo, hi = infant_weight_bounds(age_val)
            fixed = round(w / 10, 2)
            if lo <= fixed <= hi:
                corrected_weight.append(fixed)
                w_notes[i] = f"corrected from {w} (implausible for infant age {age_val}y, decimal entry error)"
            else:
                corrected_weight.append("Unknown")
                w_notes[i] = (f"uncorrectable: {w} (÷10={fixed} still implausible for infant "
                              f"age {age_val}y, expected {lo}-{hi}kg) — needs manual review")
        else:
            corrected_weight.append(w)
    case["Weight (kg)"] = corrected_weight

    h_fixed = [fix_height(h, a) for h, a in zip(case["Height (cm)"], final_age)]
    case["Height (cm)"] = [v for v, _ in h_fixed]
    h_notes = [n for _, n in h_fixed]

    for rid, note in zip(case["report ID"], w_notes):
        if note.startswith("corrected") or note.startswith("uncorrectable") or note.startswith("adult weight"):
            flags.append((rid, f"weight {note}"))
    for rid, note in zip(case["report ID"], h_notes):
        if note.startswith("corrected") or note.startswith("uncorrectable"):
            flags.append((rid, f"height {note}"))

    # --- reporter qualification: split stacked values, pick primary by priority order ---
    REPORTER_PRIORITY = [
        "physician", "pharmacist", "other health professional",
        "consumer/non health professional", "lawyer",
    ]

    def pick_primary(vals):
        if not vals:
            return np.nan
        ranked = sorted(vals, key=lambda v: (
            REPORTER_PRIORITY.index(v.strip().lower())
            if v.strip().lower() in REPORTER_PRIORITY else len(REPORTER_PRIORITY)
        ))
        return ranked[0]

    rq_split = case["Reporter qualification"].apply(split_assessments)
    for rid, vals in zip(case["report ID"], rq_split):
        if len(vals) > 1:
            flags.append((rid, f"multiple reporter qualifications stacked: {vals} — "
                                f"primary chosen by priority order (Physician > Pharmacist > "
                                f"Other Health Professional > Consumer > Lawyer)"))

    # --- seriousness criteria: same stacked-cell issue, can legitimately have
    #     more than one criterion per case (e.g. hospitalization + life-threatening),
    #     so we keep the full set rather than picking just the first ---
    sc_split = case["Seriousness criteria"].apply(split_assessments)
    for rid, vals in zip(case["report ID"], sc_split):
        if len(vals) != len(set(vals)):
            flags.append((rid, f"duplicate seriousness criteria repeated in the same cell: {vals}"))

    # --- missing critical data (Age, Sex) -> Unknown, still logged ---
    for rid, age, sex_raw in zip(case["report ID"], case["Age"], df["Sex"]):
        missing = []
        if pd.isna(age):
            missing.append("Age")
        if pd.isna(sex_raw):
            missing.append("Sex")
        if missing:
            flags.append((rid, f"missing critical field(s), set to Unknown: {', '.join(missing)}"))

    # --- write the cleaned values back into the ORIGINAL columns, so the output
    #     keeps the same fields (names + order) as the source Case sheet ---
    case["Age"] = final_age                                   # now in years
    case["Reporter qualification"] = rq_split.apply(pick_primary)
    case["Seriousness criteria"] = sc_split.apply(lambda x: "; ".join(sorted(set(x))) if x else np.nan)

    case = case[PATIENT_COLS]
    # Fatal and Pregnancy case are left exactly as in the original sheet
    # (only "Yes" or blank there) — team decision, no Unknown fill.
    for col in PATIENT_COLS:
        if col not in ("report ID", "Fatal", "Pregnancy case"):
            case[col] = case[col].apply(to_unknown)

    return case, flags


# ---------------------------------------------------------------------------
# 4) Drug-level cleaning (stacked, one entry per suspect/interacting drug)
# ---------------------------------------------------------------------------
# same order as in the original Case sheet
DRUG_STACK_COLS = [
    "WHODrug active ingredient variant", "Role", "Indication", "Dose",
    "Dose unit", "Dosage regimen", "Route of admin.", "Start Date",
    "End date", "Action taken with drug",
]

VALID_ROLES = {"suspect", "concomitant", "interacting"}

# Indication: "Drug use for unknown indication" is a MedDRA lower-level term
# under the preferred term "Product used for unknown indication" -> unified.
INDICATION_SYNONYMS = {
    "drug use for unknown indication": "Product used for unknown indication",
}


def _spelling_key(term):
    """Key that ignores UK/US spelling differences (anaemia/anemia,
    oedema/edema, immunisation/immunization, ...) and hyphen/comma noise."""
    t = term.lower()
    for a, b in (("z", "s"), ("ae", "e"), ("oe", "e"), ("-", " "), (",", "")):
        t = t.replace(a, b)
    return " ".join(t.split())


def build_indication_map(df):
    """Maps every Indication spelling variant to the variant used most often
    in the data, e.g. 'Anaemia' (89) -> 'Anemia' (173)."""
    counts = {}
    for cell in df["Indication"]:
        for v in split_assessments(cell):
            v = INDICATION_SYNONYMS.get(v.lower(), v)
            counts[v] = counts.get(v, 0) + 1
    groups = {}
    for v, n in counts.items():
        groups.setdefault(_spelling_key(v), []).append((n, v))
    mapping = {}
    for members in groups.values():
        best = max(members)[1]
        for _, v in members:
            mapping[v] = best
    return mapping


def standardize_indication(value, mapping):
    if pd.isna(value):
        return value
    v = INDICATION_SYNONYMS.get(str(value).strip().lower(), str(value).strip())
    return mapping.get(v, v)


def explode_drug_level(df):
    rows = []
    flags = []
    indication_map = build_indication_map(df)

    for _, r in df.iterrows():
        rid = r["report ID"]
        declared_n = r["Number of Suspect/Interacting drugs"]

        split_cols = {c: split_assessments(r[c]) for c in DRUG_STACK_COLS}
        lengths = {c: len(v) for c, v in split_cols.items() if v}  # ignore fully-empty cols

        # actual drug count = the most common non-empty stack length across drug cols
        # (Role and WHODrug active ingredient should always be present per drug)
        actual_n = max(
            len(split_cols["Role"]),
            len(split_cols["WHODrug active ingredient variant"]),
        )
        if actual_n == 0:
            actual_n = 1  # single, non-stacked drug

        # "Number of Suspect/Interacting drugs" counts ONLY Suspect + Interacting
        # drugs (not Concomitant), so compare it against those roles only.
        n_suspect_interacting = sum(
            1 for role in split_cols["Role"] if role.strip().lower() in ("suspect", "interacting")
        )
        if pd.notna(declared_n) and n_suspect_interacting != declared_n:
            flags.append((rid, f"declared Suspect/Interacting count ({int(declared_n)}) != "
                                f"Suspect/Interacting drugs listed ({n_suspect_interacting})"))

        # role standardization + stacked-without-separator check
        roles = split_cols["Role"] or [np.nan] * actual_n
        for role in roles:
            if pd.notna(role) and role.strip().lower() not in VALID_ROLES:
                flags.append((rid, f"unrecognized/possibly concatenated Role value: '{role}'"))

        # Position-based alignment is only trustworthy when a column holds
        # exactly as many values as there are drugs. Where a row lists 5 drugs
        # but only 3 doses, there is no way to know which two drugs are the
        # ones missing a dose, so the i-th dose does NOT belong to the i-th
        # drug. Those values are left Unknown and flagged rather than attached
        # to the wrong drug — the same rule the reaction-date cleaning applies
        # to its date columns.
        aligned = {}
        for c in DRUG_STACK_COLS:
            vals = split_cols[c]
            aligned[c] = (not vals) or len(vals) == actual_n
            if vals and not aligned[c]:
                flags.append((rid, f"{c}: {len(vals)} value(s) for {actual_n} drug(s) — "
                                    f"cannot be matched by position, set to Unknown"))

        n = actual_n
        for i in range(n):
            def get(col):
                vals = split_cols[col]
                if not vals or not aligned[col]:
                    return np.nan
                return vals[i] if i < len(vals) else np.nan

            start_raw = get("Start Date")
            end_raw = get("End date")
            start_val, start_status = standardize_date(start_raw)
            end_val, end_status = standardize_date(end_raw)

            for label, raw, status in (("Start Date", start_raw, start_status), ("End date", end_raw, end_status)):
                if status == "year_month_only":
                    flags.append((rid, f"drug #{i+1}: {label} '{raw}' is incomplete (no day) — set to Unknown"))
                elif status == "year_only_or_unparseable":
                    flags.append((rid, f"drug #{i+1}: {label} '{raw}' has no month — set to Unknown"))

            # End before Start -> both dates of this drug set to Unknown
            # (we can't tell which one is wrong; the case itself is kept).
            if start_val != "Unknown" and end_val != "Unknown" and end_val < start_val:
                flags.append((rid, f"drug #{i+1}: End date ({end_val}) is before Start date "
                                    f"({start_val}) — both set to Unknown"))
                start_val, end_val = "Unknown", "Unknown"

            row = {"report ID": rid, "drug_index": i + 1}
            for col in DRUG_STACK_COLS:
                if col == "Start Date":
                    row[col] = start_val
                elif col == "End date":
                    row[col] = end_val
                elif col == "Indication":
                    row[col] = to_unknown(standardize_indication(get(col), indication_map))
                else:
                    row[col] = to_unknown(get(col))
            rows.append(row)

    return pd.DataFrame(rows), flags


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    df = load_case_sheet()

    case_clean, case_flags = clean_case_level(df)
    drug_clean, drug_flags = explode_drug_level(df)

    # Team decision: Pregnancy case = Yes with Sex = Male is impossible and we
    # can't tell which field is wrong -> remove the whole case from both files.
    preg = df["Pregnancy case"].astype(str).str.strip().str.lower() == "yes"
    male = df["Sex"].astype(str).str.strip().str.lower() == "male"
    removed_ids = set(df.loc[preg & male, "report ID"])
    removal_flags = [(rid, "Pregnancy case = Yes but Sex = Male — case REMOVED from output "
                           "(remove this report ID from the other sheets too)")
                     for rid in sorted(removed_ids)]
    case_clean = case_clean[~case_clean["report ID"].isin(removed_ids)]
    drug_clean = drug_clean[~drug_clean["report ID"].isin(removed_ids)]

    all_flags = pd.DataFrame(removal_flags + case_flags + drug_flags, columns=["report ID", "reason"])

    case_clean.to_csv(f"{OUT_DIR}/case_level_clean.csv", index=False, encoding="utf-8-sig")
    # Drug dates renamed so they never clash with the reaction dates at merge time
    drug_clean = drug_clean.rename(columns={"Start Date": "Drug start date",
                                            "End date": "Drug end date"})
    drug_clean.to_csv(f"{OUT_DIR}/drug_level_clean.csv", index=False, encoding="utf-8-sig")
    all_flags.to_csv(f"{OUT_DIR}/review_flags.csv", index=False, encoding="utf-8-sig")

    print(f"Cases removed (pregnant + male): {len(removed_ids)}")
    print(f"Case-level rows: {len(case_clean)}")
    print(f"Drug-level rows: {len(drug_clean)}")
    print(f"Rows flagged for manual review: {all_flags['report ID'].nunique()} "
          f"({len(all_flags)} individual flags)")


if __name__ == "__main__":
    main()
