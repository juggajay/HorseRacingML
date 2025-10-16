import { useMemo, useState } from 'react';
import styles from './RaceCard.module.css';
import type { PlaybookTrackInsight, Runner } from '../lib/api';

interface RaceCardProps {
  track: string;
  raceNo: number;
  eventDate: string;
  selections: Runner[];
  playbookTrack?: PlaybookTrackInsight;
}

type ConfidenceLevel = 'high' | 'mediumHigh' | 'medium' | 'low';

// Thresholds updated to reflect realistic calibrated probabilities
// After retraining on clean Betfair features, favorites average 52%, long shots 0-5%
function getConfidenceLevel(prob: number): ConfidenceLevel {
  if (prob >= 0.25) return 'high';
  if (prob >= 0.15) return 'mediumHigh';
  if (prob >= 0.10) return 'medium';
  return 'low';
}

function formatPercent(value: number, decimals = 1) {
  return `${(value * 100).toFixed(decimals)}%`;
}

export const RaceCard: React.FC<RaceCardProps> = ({ track, raceNo, eventDate, selections, playbookTrack }) => {
  const [expanded, setExpanded] = useState(false);

  const sorted = useMemo(() => {
    return [...selections].sort((a, b) => b.model_prob - a.model_prob);
  }, [selections]);

  const visible = expanded ? sorted : sorted.slice(0, 3);

  const bestEdge = useMemo(() => {
    return Math.max(...sorted.map((runner) => runner.model_prob - runner.implied_prob));
  }, [sorted]);

  const raceLabel = useMemo(() => {
    const date = new Date(eventDate);
    return date.toLocaleDateString('en-AU', { weekday: 'short', month: 'short', day: 'numeric' });
  }, [eventDate]);

  return (
    <article className={styles.card}>
      <header className={styles.header}>
        <div className={styles.identity}>
          <span className={styles.meta}>{raceLabel}</span>
          <h3 className={styles.track}>{track} • Race {raceNo}</h3>
        </div>
        <div className={styles.badges}>
          <span className={`${styles.badge} ${styles.edgeBadge}`}>Top edge {formatPercent(bestEdge)}</span>
          <span className={styles.badge}>Selections {sorted.length}</span>
          {playbookTrack && (
            <span className={`${styles.badge} ${styles.playbookBadge}`}>
              Playbook POT {playbookTrack.pot_pct.toFixed(1)}% • {playbookTrack.bets} bets
            </span>
          )}
        </div>
      </header>

      <div className={styles.grid}>
        {visible.map((runner) => {
          const diff = runner.model_prob - runner.implied_prob;
          const confidenceLevel = getConfidenceLevel(runner.model_prob);
          const confidenceClass = {
            high: styles.confidenceHigh,
            mediumHigh: styles.confidenceMediumHigh,
            medium: styles.confidenceMedium,
            low: styles.confidenceLow,
          }[confidenceLevel];

          return (
            <div key={`${runner.win_market_id}-${runner.selection_id}`} className={styles.runner}>
              <div className={styles.runnerMain}>
                <h4 className={styles.horseName}>{runner.selection_name}</h4>
                <div className={styles.secondaryLine}>
                  {runner.betfair_horse_rating !== undefined && (
                    <span className={styles.tag}>Rating {runner.betfair_horse_rating.toFixed(1)}</span>
                  )}
                  {runner.win_rate !== undefined && (
                    <span className={styles.tag}>Win {formatPercent(runner.win_rate, 0)}</span>
                  )}
                  <span className={`${styles.confidence} ${confidenceClass}`}>
                    {formatPercent(runner.model_prob, 0)} confidence
                  </span>
                </div>
              </div>
              <div className={styles.runnerMetrics}>
                <span className={styles.metricLabel}>Odds</span>
                <span className={styles.metricValue}>${runner.win_odds.toFixed(2)}</span>
                <span className={styles.metricLabel}>Edge</span>
                <span className={styles.metricValue} style={{ color: diff >= 0 ? 'var(--profit-green)' : 'var(--loss-red)' }}>
                  {formatPercent(diff)}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {sorted.length > 3 && (
        <button
          type="button"
          className={styles.expandButton}
          onClick={() => setExpanded((prev) => !prev)}
        >
          {expanded ? 'Show fewer runners' : `Show all ${sorted.length} selections`}
        </button>
      )}
    </article>
  );
};
