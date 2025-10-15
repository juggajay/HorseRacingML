"""Feature engineering utilities for PF + Betfair merged datasets."""
from __future__ import annotations

import numpy as np
import pandas as pd

PF_BASE_FEATURES = [
    "pf_score",
    "neural_rating",
    "time_rating",
    "early_time_rating",
    "late_sectional_rating",
    "weight_class_rating",
    "pf_ai_rank",
    "pf_ai_score",
    "pf_ai_price",
]

PF_ENGINEERED_FEATURES = [
    "pf_score_advantage",
    "class_rating_advantage",
    "combined_rating_adv",
    "speed_rating_norm",
    "pace_ratio",
    "is_front_runner",
    "is_closer",
    "neural_rating_pct",
    "pf_ai_value",
    "is_pf_ai_favorite",
    "ai_confident_fav",
    "ratings_agree_top3",
    "value_with_rating",
    "second_up_rated",
]

MARKET_FEATURES = [
    "win_odds",
    "total_matched",
    "is_favorite",
    "odds_vs_favorite",
    "volume_rank",
    "is_high_volume",
]

FORM_CYCLE_FEATURES = [
    "days_since_last_run",
    "is_spell",
    "prep_run_number",
    "is_first_up",
    "is_second_up",
    "is_third_up",
]

HISTORICAL_PRIORS = [
    "betfair_horse_rating",
    "win_rate",
    "place_rate",
    "total_starts",
    "betfair_rating_advantage",
    "is_experienced",
    "is_novice",
    "is_strong_form",
    "is_consistent",
]

EXTERNAL_PRIORS = [
    "value_pct",
    "race_speed",
    "early_speed",
    "late_speed",
    "speed_category_code",
    "model_rank",
    "win_bsp_kash",
    "win_bsp_top5",
]

INTERACTION_FEATURES = [
    "value_edge",
    "value_with_rating",
    "second_up_rated",
]


def _coerce_datetime(series: pd.Series) -> pd.Series:
    converted = pd.to_datetime(series, errors="coerce")
    return converted


def _get_best_series(df: pd.DataFrame, candidates: list[str], *, numeric: bool = False) -> pd.Series:
    for col in candidates:
        if col in df.columns:
            if numeric:
                return pd.to_numeric(df[col], errors="coerce")
            return df[col]
    return pd.Series(np.nan, index=df.index)


def _ensure_race_id(df: pd.DataFrame) -> pd.Series:
    if "race_id_bf" in df.columns:
        return df["race_id_bf"].astype(str)
    if "win_market_id" in df.columns:
        return df["win_market_id"].astype(str)
    if "market_id" in df.columns:
        return df["market_id"].astype(str)
    return df.groupby(["event_date", "track_name_norm"]).cumcount().astype(str)


def _ensure_selection_id(df: pd.DataFrame) -> pd.Series:
    if "selection_id" in df.columns:
        return df["selection_id"].astype(str)
    if "runner_id" in df.columns:
        return df["runner_id"].astype(str)
    return df.groupby(["event_date", "horse_name_norm"]).cumcount().astype(str)


def engineer_all_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add market, form, PF, and interaction features."""
    df = df.copy()

    pf_missing = [
        "pf_score",
        "neural_rating",
        "time_rating",
        "early_time_rating",
        "late_sectional_rating",
        "weight_class_rating",
        "combined_weight_time",
        "pf_ai_rank",
        "pf_ai_score",
        "pf_ai_price",
    ]
    for col in pf_missing:
        if col not in df.columns:
            df[col] = np.nan

    # ------------------------------------------------------------------
    # CORE IDENTIFIERS
    # ------------------------------------------------------------------
    df["event_date"] = _coerce_datetime(df.get("event_date"))
    df = df[df["event_date"].notna()].copy()
    df["race_id"] = _ensure_race_id(df)
    df["selection_id"] = _ensure_selection_id(df)

    # ------------------------------------------------------------------
    # MARKET FEATURES
    # ------------------------------------------------------------------
    odds = _get_best_series(
        df,
        [
            "win_preplay_last_price_taken",
            "win_last_price_taken",
            "win_preplay_weighted_average_price_taken",
            "win_bsp",
        ],
        numeric=True,
    )
    df["win_odds"] = odds.replace({0: np.nan})

    matched = _get_best_series(df, ["win_preplay_volume", "win_inplay_volume", "place_preplay_volume"], numeric=True)
    df["total_matched"] = matched

    df["is_favorite"] = (
        df.groupby("race_id")["win_odds"].transform(lambda x: x == x.min())
    ).fillna(False).astype(int)

    df["odds_vs_favorite"] = df["win_odds"] / df.groupby("race_id")["win_odds"].transform("min")
    df["volume_rank"] = df.groupby("race_id")["total_matched"].rank(ascending=False, method="dense")
    df["is_high_volume"] = (df["volume_rank"] <= 3).astype(int)

    # ------------------------------------------------------------------
    # FORM CYCLE FEATURES (days between runs per horse)
    # ------------------------------------------------------------------
    df = df.sort_values(["selection_id", "event_date"])
    df["days_since_last_run"] = df.groupby("selection_id")["event_date"].diff().dt.days
    df["days_since_last_run"] = df["days_since_last_run"].fillna(999)
    df["is_spell"] = (df["days_since_last_run"] >= 90).astype(int)

    df["prep_run_number"] = df.groupby("selection_id")["is_spell"].cumsum() + 1
    df["is_first_up"] = (df["prep_run_number"] == 1).astype(int)
    df["is_second_up"] = (df["prep_run_number"] == 2).astype(int)
    df["is_third_up"] = (df["prep_run_number"] == 3).astype(int)

    # ------------------------------------------------------------------
    # PF FEATURE ENGINEERING
    # ------------------------------------------------------------------
    def _group_adv(column: str, race_key: str = "race_id") -> pd.Series:
        if column not in df.columns:
            return pd.Series(0, index=df.index)
        return df.groupby(race_key)[column].transform(
            lambda x: x - x.mean() if x.notna().any() else 0
        )

    pf_ai_rank_numeric = pd.to_numeric(df["pf_ai_rank"], errors="coerce")
    df["is_pf_ai_favorite"] = (pf_ai_rank_numeric == 1).astype(int)
    df["pf_ai_value"] = df.get("pf_ai_price") / (df["win_odds"] + 1e-9)
    df["pf_score_advantage"] = _group_adv("pf_score")
    df["class_rating_advantage"] = _group_adv("weight_class_rating")
    df["combined_rating_adv"] = _group_adv("pf_score")

    df["speed_rating_norm"] = df.groupby("race_id")["time_rating"].transform(
        lambda x: (x - x.mean()) / (x.std() + 1e-9) if x.notna().any() else 0
    )

    df["pace_ratio"] = df.get("early_time_rating") / (df.get("late_sectional_rating") + 1e-9)
    df["is_front_runner"] = (df["pace_ratio"] > 1.15).astype(int)
    df["is_closer"] = (df["pace_ratio"] < 0.85).astype(int)

    if "speed_category" in df.columns:
        df["speed_category_code"] = (
            df["speed_category"].astype("category").cat.codes.replace(-1, np.nan)
        )

    if "win_bsp_kash" in df.columns:
        df["kash_implied_prob"] = 1.0 / (pd.to_numeric(df["win_bsp_kash"], errors="coerce") + 1e-9)
    if "win_bsp_top5" in df.columns:
        df["top5_implied_prob"] = 1.0 / (pd.to_numeric(df["win_bsp_top5"], errors="coerce") + 1e-9)

    df["neural_rating_pct"] = df.groupby("race_id")["neural_rating"].rank(pct=True)

    median_ai_score = df.groupby("race_id")["pf_ai_score"].transform("median")
    df["ai_confident_fav"] = ((df["pf_ai_rank"] == 1) & (df["pf_ai_score"] > median_ai_score)).astype(int)

    df["ratings_agree_top3"] = (
        (df["pf_ai_rank"] <= 3)
        & (df["neural_rating_pct"] >= 0.7)
        & (df["speed_rating_norm"] > 0.5)
    ).astype(int)

    df["value_with_rating"] = (
        (df["pf_ai_value"] > 1.2)
        & (df["pf_ai_rank"] <= 3)
    ).astype(int)

    df["second_up_rated"] = (
        (df["is_second_up"] == 1)
        & (df["pf_score_advantage"] > 5)
    ).astype(int)

    # ------------------------------------------------------------------
    # HISTORICAL PRIORS (Betfair)
    # ------------------------------------------------------------------
    numeric_priors = {
        "betfair_horse_rating": 50.0,
        "win_rate": 0.10,
        "place_rate": 0.30,
        "total_starts": 5,
        "betfair_rating_advantage": 0.0,
    }
    for col, default in numeric_priors.items():
        if col not in df.columns:
            df[col] = default
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(default)

    numeric_externals = {
        "value_pct": 0.0,
        "race_speed": 0.0,
        "early_speed": 0.0,
        "late_speed": 0.0,
        "speed_category_code": 0.0,
        "model_rank": 5.0,
        "win_bsp_kash": 0.0,
        "win_bsp_top5": 0.0,
        "kash_implied_prob": 0.0,
        "top5_implied_prob": 0.0,
    }

    for col, default in numeric_externals.items():
        if col not in df.columns:
            df[col] = default
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(default)

    binary_priors = ["is_experienced", "is_novice", "is_strong_form", "is_consistent"]
    for col in binary_priors:
        if col not in df.columns:
            df[col] = 0
        df[col] = df[col].fillna(0).astype(int)

    # ------------------------------------------------------------------
    # AUXILIARY INTERACTIONS
    # ------------------------------------------------------------------
    if "model_prob" in df.columns:
        model_prob = pd.to_numeric(df["model_prob"], errors="coerce").fillna(0)
    else:
        model_prob = pd.Series(0, index=df.index, dtype=float)
    df["value_edge"] = model_prob - (1.0 / (df["win_odds"] + 1e-9))

    # ------------------------------------------------------------------
    # IMPUTATION
    # ------------------------------------------------------------------
    continuous_features = list({
        "win_odds",
        "total_matched",
        "odds_vs_favorite",
        "volume_rank",
        "days_since_last_run",
        "pf_score",
        "neural_rating",
        "time_rating",
        "early_time_rating",
        "late_sectional_rating",
        "weight_class_rating",
        "pf_ai_score",
        "pf_ai_price",
        "pf_score_advantage",
        "class_rating_advantage",
        "combined_rating_adv",
        "speed_rating_norm",
        "pace_ratio",
        "neural_rating_pct",
        "pf_ai_value",
        "value_edge",
        "betfair_horse_rating",
        "win_rate",
        "place_rate",
        "total_starts",
        "betfair_rating_advantage",
        "value_pct",
        "race_speed",
        "early_speed",
        "late_speed",
        "speed_category_code",
        "model_rank",
        "win_bsp_kash",
        "win_bsp_top5",
        "kash_implied_prob",
        "top5_implied_prob",
    } & set(df.columns))

    for col in continuous_features:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            df[col] = df[col].fillna(df[col].median())

    binary_features = list({
        "is_favorite",
        "is_high_volume",
        "is_spell",
        "is_first_up",
        "is_second_up",
        "is_third_up",
        "is_pf_ai_favorite",
        "is_front_runner",
        "is_closer",
        "ai_confident_fav",
        "ratings_agree_top3",
        "value_with_rating",
        "second_up_rated",
        "is_experienced",
        "is_novice",
        "is_strong_form",
        "is_consistent",
    } & set(df.columns))

    for col in binary_features:
        df[col] = df[col].fillna(0).astype(int)

    if "pf_ai_rank" in df.columns:
        df["pf_ai_rank"] = df["pf_ai_rank"].fillna(df["pf_ai_rank"].median())

    return df


def get_feature_columns() -> list[str]:
    return [
        *MARKET_FEATURES,
        *FORM_CYCLE_FEATURES,
        *HISTORICAL_PRIORS,
        *PF_BASE_FEATURES,
        *PF_ENGINEERED_FEATURES,
        "value_edge",
    ]


def print_feature_summary(df: pd.DataFrame, feature_cols: list[str]) -> None:
    print("\n" + "=" * 70)
    print("FEATURE SUMMARY")
    print("=" * 70)
    categories = {
        "Market": MARKET_FEATURES,
        "Form Cycle": FORM_CYCLE_FEATURES,
        "Historical": HISTORICAL_PRIORS,
        "PF Base": PF_BASE_FEATURES,
        "PF Engineered": PF_ENGINEERED_FEATURES,
        "Interaction": ["value_edge", "value_with_rating", "second_up_rated"],
    }
    total = len(df)
    for label, cols in categories.items():
        print(f"\n{label} features:")
        for col in cols:
            if col not in df.columns or col not in feature_cols:
                continue
            non_null = df[col].notna().sum()
            pct = 100 * non_null / max(total, 1)
            status = "✓" if pct >= 80 else "⚠" if pct > 0 else "✗"
            print(f"  {status} {col:25s}: {non_null:4d} / {total} ({pct:5.1f}%)")
    print("=" * 70)
