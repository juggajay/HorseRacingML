import { useMemo, useState, useEffect } from 'react';
import styles from './RaceCard.module.css';
import type { PlaybookTrackInsight, Runner } from '../lib/api';

interface RaceCardProps {
  track: string;
  raceNo: number;
  eventDate: string;
  selections: Runner[];
  playbookTrack?: PlaybookTrackInsight;
}

function useCountdown(targetTime: string | undefined, eventDate: string): string {
  const [countdown, setCountdown] = useState<string>('');

  useEffect(() => {
    if (!targetTime) return;

    const updateCountdown = () => {
      try {
        // Combine event_date and race_time to create full datetime
        // race_time is typically "HH:MM:SS" format
        const dateStr = eventDate.split('T')[0]; // Get YYYY-MM-DD part
        const fullDateTime = `${dateStr}T${targetTime}`;
        const target = new Date(fullDateTime);

        // Use Sydney timezone offset (AEDT is UTC+11, AEST is UTC+10)
        // For simplicity, we'll assume AEDT (UTC+11) - adjust if needed
        const now = new Date();
        const diff = target.getTime() - now.getTime();

        if (diff <= 0) {
          setCountdown('Started');
          return;
        }

        const hours = Math.floor(diff / (1000 * 60 * 60));
        const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
        const seconds = Math.floor((diff % (1000 * 60)) / 1000);

        if (hours > 0) {
          setCountdown(`${hours}h ${minutes}m`);
        } else if (minutes > 0) {
          setCountdown(`${minutes}m ${seconds}s`);
        } else {
          setCountdown(`${seconds}s`);
        }
      } catch (e) {
        setCountdown('');
      }
    };

    updateCountdown();
    const interval = setInterval(updateCountdown, 1000);
    return () => clearInterval(interval);
  }, [targetTime, eventDate]);

  return countdown;
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

  // Get race_time from first runner (all runners in same race have same time)
  const raceTime = sorted[0]?.race_time;
  const countdown = useCountdown(raceTime, eventDate);

  const formatRaceTime = (time: string | undefined) => {
    if (!time) return null;
    try {
      // race_time is "HH:MM:SS", we want "HH:MM"
      const parts = time.split(':');
      return `${parts[0]}:${parts[1]}`;
    } catch {
      return null;
    }
  };

  const formattedTime = formatRaceTime(raceTime);

  return (
    <article className={styles.card}>
      <header className={styles.header}>
        <div className={styles.identity}>
          <div className={styles.metaRow}>
            <span className={styles.meta}>{raceLabel}</span>
            {formattedTime && (
              <>
                <span className={styles.meta}>•</span>
                <span className={styles.meta}>{formattedTime}</span>
                {countdown && (
                  <>
                    <span className={styles.meta}>•</span>
                    <span className={`${styles.countdown} ${countdown === 'Started' ? styles.countdownStarted : ''}`}>
                      {countdown === 'Started' ? '🏁 Started' : `⏱️ ${countdown}`}
                    </span>
                  </>
                )}
              </>
            )}
          </div>
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
                  {/* Only show betfair_horse_rating if it's not the default 50.0 */}
                  {runner.betfair_horse_rating !== undefined && runner.betfair_horse_rating !== 50.0 && (
                    <span className={styles.tag}>Rating {runner.betfair_horse_rating.toFixed(1)}</span>
                  )}
                  {/* Only show win_rate if it's not the default 0.1 (10%) */}
                  {runner.win_rate !== undefined && runner.win_rate !== 0.1 && (
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
