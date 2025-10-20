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

      {/* Explanation Section */}
      <div className={styles.explainerSection}>
        <div className={styles.explainerCard}>
          <h3 className={styles.explainerTitle}>📖 What Am I Looking At?</h3>
          <p className={styles.explainerText}>
            This page shows <strong>historical snapshots from every ACE run</strong> - a timeline of how your betting strategies
            have evolved over time. ACE keeps the last 10 playbook snapshots so you can track performance trends and see
            if strategies are improving.
          </p>
          <div className={styles.explainerPoints}>
            <div className={styles.explainerPoint}>
              <span className={styles.explainerBullet}>📅</span>
              <span><strong>Snapshots:</strong> Each card represents one ACE run. The most recent is at the top. ACE runs daily when you click "Run ACE Daily Update"</span>
            </div>
            <div className={styles.explainerPoint}>
              <span className={styles.explainerBullet}>📊</span>
              <span><strong>Performance Metrics:</strong> Each snapshot shows POT, hit rate, total bets, and experiences analyzed at that point in time</span>
            </div>
            <div className={styles.explainerPoint}>
              <span className={styles.explainerBullet}>📈</span>
              <span><strong>Trend Analysis:</strong> Compare snapshots to see if your strategies are getting better. Rising POT = improving profitability</span>
            </div>
            <div className={styles.explainerPoint}>
              <span className={styles.explainerBullet}>🧠</span>
              <span><strong>Learning Over Time:</strong> More experiences = better patterns. ACE gets smarter as it analyzes more betting decisions</span>
            </div>
            <div className={styles.explainerPoint}>
              <span className={styles.explainerBullet}>💾</span>
              <span><strong>Anti-Erosion:</strong> ACE never forgets. Even if recent performance is poor, it keeps historical learnings to prevent knowledge loss</span>
            </div>
          </div>
        </div>
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
