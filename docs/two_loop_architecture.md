# Two-Loop Learning Architecture (Early Experience + ACE)

_Last updated: 2025-10-16_

## 1. Goals

The objective of the next phase is to layer an autonomous improvement loop on top of the existing PF-aligned pipeline. We want the system to:

1. **Explore** betting strategies safely using historical PF data (Early Experience / tactical loop).
2. **Reflect and curate** the insights from those explorations into a durable racing playbook (ACE / strategic loop).
3. **Expose** the resulting playbook back to the modelling stack and UI so we can steer daily decisions and human review.

The loops must run without manual labelling, reuse the single source of truth we have already produced (`services/api/data/processed/pf_schema/`), and emit artefacts that can be versioned, audited, and replayed.

## 2. High-Level Flow

```
 PF tables (meetings/races/runners)  ─────┐
                                        │
                                [Feature Builder]
                                        │
                                 Runner feature set
                                        │
                           ┌────────────┴────────────┐
                           │                         │
                  [Simulation Environment]    [ACE Playbook]
                           │                         ▲
                 Early Experience loop:              │
                 - generate strategy configs         │
                 - evaluate in sim                   │
                 - persist trajectories ─────────────┘
```

In practice we will orchestrate the loops with a script (`scripts/run_ace_loop.py`):

1. Load PF tables + engineered features.
2. Generate strategy candidates (parameter grid) and run them through the simulator.
3. Store each (state, action, outcome) tuple in the **experience store**.
4. Run reflection/curation over the accumulated experiences to update the **playbook** artefact.

## 3. Data Contracts

### 3.1 Source Tables
- `services/api/data/processed/pf_schema/meetings.csv.gz`
- `services/api/data/processed/pf_schema/races.csv.gz`
- `services/api/data/processed/pf_schema/runners.csv.gz`

These already contain: meeting metadata, race metadata (scheduled start, distance, type), runner features (odds, trainer stats, outcomes).

### 3.2 Engineered Runner Features
- Location: `data/processed/features/pf_runner_features.parquet`
- Built via the existing `engineer_all_features` function.
- Key columns we will rely on for simulation/strategy conditions:
  - Identifiers: `event_date`, `race_id`, `runner_id`, `selection_id`, `track`, `race_no`
  - Model signals: `model_prob`, `win_odds`, `implied_prob`, `edge`, PF placeholders (pf_score etc.)
  - Context: `distance`, `racing_type`, `race_type`, `state_code`
  - Outcomes: `win_result`, `place_result`

### 3.3 Experience Store
- Location: `data/experiences/`
- File format: partitioned Parquet (e.g. `experiences/2025-09/part-0.parquet`).
- Schema (first iteration):
  | Column | Type | Description |
  |--------|------|-------------|
  | `event_date` | date | Race date |
  | `race_id` | string | PF-style race identifier |
  | `runner_id` | string | PF-style runner identifier |
  | `strategy_id` | string | Hashable descriptor (e.g. `margin_1.05_top3_stake1`) |
  | `params` | JSON string | Full parameter dict for reproducibility |
  | `action` | string | `bet` or `skip` (top-level decision) |
  | `stake` | float | Units risked |
  | `profit` | float | Resulting units returned |
  | `model_prob` | float | Model-estimated win probability |
  | `implied_prob` | float | Derived from odds |
  | `edge` | float | `model_prob - implied_prob` |
  | `track` | string | Track name |
  | `state_code` | string | State code |
  | `distance` | float | Race distance |
  | `context_hash` | string | Stable hash of state snapshot (feature subset) |

  Additional columns can be appended as we introduce richer strategies (e.g. `pf_score`, `trainer_a2e`).

### 3.4 Playbook Artefact
- Location: `artifacts/playbook/playbook.json`
- Content: structured summary the ACE loop produces, versioned by timestamp, for example:

```json
{
  "metadata": {
    "generated_at": "2025-10-16T12:00:00Z",
    "experience_rows": 45231
  },
  "global": {
    "best_margin": 1.08,
    "pot_pct": 6.2,
    "hit_rate": 0.23
  },
  "by_track": {
    "FLEMINGTON": {"pot_pct": 12.4, "bets": 320, "notes": "Prefer soft tracks, margin 1.05"},
    "RANDWICK": {"pot_pct": -3.9, "bets": 280, "notes": "Avoid margins <1.1"}
  },
  "strategy_notes": [
    {"strategy_id": "margin_1.08_top2", "summary": "Strong ROI on 1400-1800m", "actions": ["increase stake", "monitor jockey claims"]}
  ]
}
```

A human-readable Markdown report can be generated alongside (optional).

## 4. Components

### 4.1 Simulation Environment (`ace/simulator.py`)
- Loads engineered runner features for a date range.
- Accepts a `StrategyAction` object describing the rule (e.g. margin threshold, max selections per race, stake size, optional filters).
- Outputs per-runner results and aggregated metrics (bets placed, POT%, drawdown-inferred metrics later).

### 4.2 Strategy Definition (`ace/strategies.py`)
- Declarative dataclass representing tunable parameters:
  ```python
  @dataclass
  class StrategyConfig:
      strategy_id: str
      margin: float
      top_n: int
      stake: float = 1.0
      filters: dict[str, Any] = field(default_factory=dict)
  ```
- Utility to generate candidate grids (e.g. margin 1.00–1.20, top_n {1,2,3}).

### 4.3 Early Experience Loop (`ace/early_experience.py`)
- Iterates over races ➜ evaluates each strategy ➜ records experience rows.
- May include simple exploration heuristics (e.g. epsilon-greedy over strategies, random track subsets).
- Persists experiences incrementally to avoid RAM blow-ups.

### 4.4 ACE Playbook (`ace/playbook.py`)
- Reflection: aggregates experiences, identifies profitable patterns/ failure modes.
- Curation: merges new insights into existing playbook JSON (keeps history, avoids catastrophic forgetting by performing diff-based updates).
- Also produces summary stats per strategy and per context (track, distance band, surface, state, day-of-week).

### 4.5 Orchestrator (`scripts/run_ace_loop.py`)
- CLI entry point combining the previous components.
- Flags: `--start-date`, `--end-date`, `--strategies` (path to config JSON), `--max-races`, `--write-report`.
- Sequence: load features → run Early Experience → run ACE → emit artefacts (experience shard, playbook JSON, optional Markdown summary).

## 5. Implementation Plan

1. **Design + scaffolding** (this document). ✅
2. **Simulator** with regression tests comparing to baseline ROI numbers.
3. **Early Experience** loop writing to `data/experiences/`.
4. **ACE** reflector/curator updating `artifacts/playbook/`.
5. **Orchestration** script + documentation.

Each module will ship with logging hooks and optional dry-run flags to aid debugging.

## 6. Running the Loops

Once a LightGBM model has been trained and the PF schema tables are available, run:

```bash
python3 scripts/run_ace_loop.py \
  --start-date 2025-07-18 \
  --end-date 2025-09-30 \
  --strategies configs/strategies_default.json \
  --max-races 500
```

This will:

1. Load the PF runner dataset for the requested date range and score it with the latest model.
2. Evaluate the supplied strategy grid, writing experience shards to `data/experiences/`.
3. Reflect over the experiences and update `artifacts/playbook/playbook.json` with fresh track/strategy insights.

Use `--output-experiences` or `--playbook-path` to redirect artefacts (useful for experimentation). Set `--min-bets` to control how many bets a context needs before it appears in the playbook summary.

## 7. Frontend Surface

The dashboard now consumes `GET /playbook` to drive three new UI elements:

- **Playbook Snapshot bar** (header): POT%, hit rate, and total experiences with last-updated timestamp.
- **Strategy-aware filters** (sidebar): pick an ACE strategy, optionally apply its recommended margin, and view helper text for top selections/stake.
- **Insights panel** (main): highlights the selected strategy&apos;s performance, the hottest tracks, and the leading track/distance contexts so users can align daily decisions with the playbook.

Race cards call out playbook momentum per track and the detailed table footnote summarises average edge/odds under the active filters.

## 6. Open Questions / Future Enhancements

- **Sectionals / Ratings**: once PF unlocks these endpoints the simulator and strategies should ingest the extra columns automatically.
- **Bankroll management**: future iterations can incorporate Kelly fractions or drawdown controls in the simulator.
- **UI integration**: expose playbook highlights in the dashboard (e.g. “today’s best tracks” widget).
- **Model feedback loop**: feed ACE-derived contexts back into model retraining (e.g. as sample weights or feature expectations).

---

This document will be kept up to date as the implementation proceeds.
