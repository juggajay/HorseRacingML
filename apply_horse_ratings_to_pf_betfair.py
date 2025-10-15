# apply_horse_ratings_to_pf_betfair.py
# Join per-horse ratings onto PF+Betfair merged data by horse_name_norm only (no date overlap needed).
import os, re, pandas as pd

MERGED_IN  = r"data/processed/ml/pf_betfair_merged.csv.gz"
RATINGS_IN = r"artifacts/horse_ratings_2021.csv"
OUT_PATH   = r"data/processed/ml/pf_betfair_with_kagglepriors.csv.gz"

def norm(s):
    import pandas as pd, re
    if pd.isna(s): return s
    s = str(s).lower().strip()
    s = re.sub(r"[^\w\s]", "", s); s = re.sub(r"\s+", " ", s)
    return s

if not os.path.exists(MERGED_IN):
    raise SystemExit("❌ PF+Betfair merged file not found: "+MERGED_IN)
if not os.path.exists(RATINGS_IN):
    raise SystemExit("❌ Ratings file not found: "+RATINGS_IN)

df = pd.read_csv(MERGED_IN, low_memory=False)
rt = pd.read_csv(RATINGS_IN)

# Detect horse column on PF+Betfair side
def pick(cols, pats):
    cl = [c.lower() for c in cols]
    for patt in pats:
        for i,c in enumerate(cl):
            if re.search(patt, c):
                return cols[i]
    return None

horse_col = pick(df.columns, [r"horse_name_norm", r"horse.?name", r"runner.?name", r"selection_name"])
if horse_col != "horse_name_norm":
    df["horse_name_norm"] = df[horse_col].map(norm)
# Ratings already have horse_name_norm
enriched = df.merge(rt[["horse_name_norm","horse_rating_2021","runs_life","win_rate_life","model_prob"]],
                    on="horse_name_norm", how="left")

# Coverage
cov = enriched["horse_rating_2021"].notna().mean()
print(f"Ratings coverage: {cov:.1%} of rows")
os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
enriched.to_csv(OUT_PATH, index=False, compression="gzip")
print("Saved:", OUT_PATH, "rows:", len(enriched))
