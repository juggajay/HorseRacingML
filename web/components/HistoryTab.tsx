import type { PlaybookResponse } from '../lib/api';
import styles from '../styles/HistoryTab.module.css';

interface HistoryTabProps {
  playbookData?: PlaybookResponse;
}

export default function HistoryTab({ playbookData }: HistoryTabProps) {
  const history = playbookData?.history ?? [];

  const formatTimestamp = (iso: string) => {
    const date = new Date(iso);
    return date.toLocaleString('en-AU', {
      timeZone: 'Australia/Sydney',
      weekday: 'short',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const formatPercent = (value: number | null | undefined) => {
    if (value === null || value === undefined || Number.isNaN(value)) return '—';
    return `${value.toFixed(1)}%`;
  };

  const formatRatioPercent = (value: number | null | undefined) => {
    if (value === null || value === undefined || Number.isNaN(value)) return '—';
    return `${(value * 100).toFixed(1)}%`;
  };

  return (
    <div className={styles.historyTab}>
      <div className={styles.header}>
        <h2 className={styles.title}>Performance History</h2>
        <p className={styles.subtitle}>Historical playbook snapshots and performance tracking</p>
      </div>

      {history.length === 0 ? (
        <div className={styles.empty}>
          <p>No historical data available yet.</p>
          <p className={styles.emptyHint}>ACE will generate snapshots as you accumulate betting experiences.</p>
        </div>
      ) : (
        <div className={styles.timeline}>
          {history.map((snapshot, idx) => {
            const metadata = snapshot.metadata as any || {};
            const global = snapshot.global as any || {};

            return (
              <div key={`snapshot-${idx}`} className={styles.snapshotCard}>
                <div className={styles.snapshotHeader}>
                  <div className={styles.snapshotTime}>
                    {metadata.generated_at ? formatTimestamp(metadata.generated_at) : 'Unknown date'}
                  </div>
                  <div className={styles.snapshotBadge}>
                    {idx === 0 ? 'Latest' : `${idx + 1} runs ago`}
                  </div>
                </div>

                <div className={styles.snapshotStats}>
                  <div className={styles.stat}>
                    <span className={styles.statLabel}>POT</span>
                    <span className={styles.statValue}>{formatPercent(global.pot_pct)}</span>
                  </div>
                  <div className={styles.stat}>
                    <span className={styles.statLabel}>Hit Rate</span>
                    <span className={styles.statValue}>{formatRatioPercent(global.hit_rate)}</span>
                  </div>
                  <div className={styles.stat}>
                    <span className={styles.statLabel}>Bets</span>
                    <span className={styles.statValue}>{global.total_bets ?? 0}</span>
                  </div>
                  <div className={styles.stat}>
                    <span className={styles.statLabel}>Experiences</span>
                    <span className={styles.statValue}>{(metadata.experience_rows ?? 0).toLocaleString()}</span>
                  </div>
                </div>

                <div className={styles.snapshotMeta}>
                  <span>{(snapshot.strategies ?? []).length} strategies</span>
                  <span>•</span>
                  <span>{(snapshot.contexts ?? []).length} contexts</span>
                  <span>•</span>
                  <span>{(snapshot.tracks ?? []).length} tracks</span>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {history.length > 0 && (
        <div className={styles.insights}>
          <h3>Insights</h3>
          <div className={styles.insightGrid}>
            <div className={styles.insightCard}>
              <div className={styles.insightIcon}>📈</div>
              <h4>Trend Analysis</h4>
              <p>
                {history.length} playbook snapshots recorded.
                {history[0]?.global?.pot_pct && history[history.length - 1]?.global?.pot_pct &&
                history[0].global.pot_pct > history[history.length - 1].global.pot_pct
                  ? ' POT is improving over time.'
                  : ' Continue accumulating data for better insights.'}
              </p>
            </div>
            <div className={styles.insightCard}>
              <div className={styles.insightIcon}>🎯</div>
              <h4>Strategy Evolution</h4>
              <p>
                ACE continuously learns from betting outcomes to refine strategy recommendations.
                More experiences lead to better performance predictions.
              </p>
            </div>
            <div className={styles.insightCard}>
              <div className={styles.insightIcon}>💡</div>
              <h4>Next Steps</h4>
              <p>
                Keep logging betting decisions through the Races tab. ACE will automatically
                update the playbook as new patterns emerge.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
