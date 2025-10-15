"""Compare baseline vs PF-enhanced betting results."""
from __future__ import annotations

import pandas as pd
from pathlib import Path

print("=" * 70)
print("MODEL COMPARISON: Baseline vs PF-Enhanced")
print("=" * 70)

baseline_path = Path("artifacts/baseline_results.csv")
pf_path = Path("artifacts/pf_enhanced_results.csv")

if not baseline_path.exists():
    print("✗ baseline_results.csv not found in artifacts/")
    raise SystemExit(1)

if not pf_path.exists():
    print("✗ pf_enhanced_results.csv not found. Run train_model_pf.py first")
    raise SystemExit(1)

baseline = pd.read_csv(baseline_path)
pf = pd.read_csv(pf_path)

if "month" not in baseline.columns or "month" not in pf.columns:
    raise SystemExit("✗ monthly results require a 'month' column")

comparison = baseline.merge(pf, on="month", suffixes=("_baseline", "_pf"))
comparison["pot_improvement"] = comparison["pot_pct_pf"] - comparison["pot_pct_baseline"]

print("\n" + "=" * 70)
print("MONTHLY COMPARISON")
print("=" * 70)
print(f"{'Month':<10} {'Base POT':>10} {'PF POT':>10} {'Δ POT':>10}")
print("-" * 70)
for _, row in comparison.iterrows():
    arrow = "📈" if row["pot_improvement"] > 0 else "📉" if row["pot_improvement"] < 0 else "➡️"
    print(
        f"{row['month']:<10} {row['pot_pct_baseline']:>+9.2f}% "
        f"{row['pot_pct_pf']:>+9.2f}% {arrow} {row['pot_improvement']:>+9.2f}%"
    )

base_total = comparison["total_return_baseline"].sum()
base_staked = comparison["total_staked_baseline"].sum()
pf_total = comparison["total_return_pf"].sum()
pf_staked = comparison["total_staked_pf"].sum()

base_pot = (base_total / max(base_staked, 1)) * 100
pf_pot = (pf_total / max(pf_staked, 1)) * 100
improvement = pf_pot - base_pot

print("\n" + "=" * 70)
print(f"Baseline POT: {base_pot:+.2f}% | PF POT: {pf_pot:+.2f}% | Δ {improvement:+.2f}%")
print("=" * 70)
