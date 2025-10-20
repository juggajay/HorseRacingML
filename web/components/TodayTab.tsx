import { useState } from 'react';
import type { TopPicksResponse, PlaybookResponse } from '../lib/api';
import styles from '../styles/TodayTab.module.css';

interface TodayTabProps {
  topPicksData?: TopPicksResponse;
  playbookData?: PlaybookResponse;
  date: string;
  setDate: (date: string) => void;
  topPicksError?: Error;
}

export default function TodayTab({ topPicksData, playbookData, date, setDate, topPicksError }: TodayTabProps) {
  const [showRawData, setShowRawData] = useState(false);

  const playbook = playbookData?.latest;
  const globalStats = playbook?.global;
  const topPicks = topPicksData?.top_picks ?? [];

  const formatPercent = (value: number | null | undefined) => {
    if (value === null || value === undefined || Number.isNaN(value)) return '—';
    return `${value.toFixed(1)}%`;
  };

  const formatRatioPercent = (value: number | null | undefined) => {
    if (value === null || value === undefined || Number.isNaN(value)) return '—';
    return `${(value * 100).toFixed(1)}%`;
  };

  const formatTimestamp = (iso: string | undefined) => {
    if (!iso) return '—';
    const date = new Date(iso);
    if (Number.isNaN(date.getTime())) return '—';
    return date.toLocaleString('en-AU', {
      timeZone: 'Australia/Sydney',
      hour12: false,
      weekday: 'short',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className={styles.todayTab}>
      <div className={styles.header}>
        <div>
          <h2 className={styles.title}>Today's Betting Intelligence</h2>
          <p className={styles.subtitle}>AI-powered picks and strategic insights for {new Date(date).toLocaleDateString('en-AU')}</p>
        </div>
        <div className={styles.controls}>
          <input
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            className={styles.datePicker}
          />
          <button onClick={() => setShowRawData(!showRawData)} className={styles.rawDataButton}>
            {showRawData ? 'Hide' : 'Show'} Raw Data
          </button>
        </div>
      </div>

      {/* Explanation Section */}
      <div className={styles.explainerSection}>
        <div className={styles.explainerCard}>
          <h3 className={styles.explainerTitle}>📖 What Am I Looking At?</h3>
          <p className={styles.explainerText}>
            This page shows <strong>today's highest-probability horses</strong> selected by the machine learning model.
            These picks are ranked by the model's confidence - meaning the horses it believes have the best chance of winning
            their respective races.
          </p>
          <div className={styles.explainerPoints}>
            <div className={styles.explainerPoint}>
              <span className={styles.explainerBullet}>🤖</span>
              <span><strong>ML Model Picks:</strong> Trained on 45+ features including PuntingForm AI ratings, historical performance, and market data</span>
            </div>
            <div className={styles.explainerPoint}>
              <span className={styles.explainerBullet}>🎯</span>
              <span><strong>Confidence Level:</strong> "Very High" means model probability &gt;30%, "High" means 20-30%</span>
            </div>
            <div className={styles.explainerPoint}>
              <span className={styles.explainerBullet}>📊</span>
              <span><strong>Edge:</strong> The difference between what the model thinks the horse's chance is vs what the market odds suggest</span>
            </div>
            <div className={styles.explainerPoint}>
              <span className={styles.explainerBullet}>💰</span>
              <span><strong>POT (Profit on Turnover):</strong> Historical profitability from the Playbook - shows how profitable ACE's strategies have been</span>
            </div>
          </div>
        </div>
      </div>

      {/* Quick Stats */}
      <div className={styles.statsGrid}>
        <div className={styles.statCard}>
          <div className={styles.statIcon}>💰</div>
          <div className={styles.statContent}>
            <div className={styles.statValue}>{formatPercent(globalStats?.pot_pct)}</div>
            <div className={styles.statLabel}>Playbook POT</div>
            <div className={styles.statMeta}>{globalStats?.total_bets ?? 0} bets analyzed</div>
          </div>
        </div>

        <div className={styles.statCard}>
          <div className={styles.statIcon}>🎯</div>
          <div className={styles.statContent}>
            <div className={styles.statValue}>{formatRatioPercent(globalStats?.hit_rate)}</div>
            <div className={styles.statLabel}>Hit Rate</div>
            <div className={styles.statMeta}>{playbook?.metadata.strategies_evaluated ?? 0} strategies</div>
          </div>
        </div>

        <div className={styles.statCard}>
          <div className={styles.statIcon}>📊</div>
          <div className={styles.statContent}>
            <div className={styles.statValue}>{topPicks.length}</div>
            <div className={styles.statLabel}>Top Picks Today</div>
            <div className={styles.statMeta}>{topPicksData?.total_races ?? 0} races scanned</div>
          </div>
        </div>

        <div className={styles.statCard}>
          <div className={styles.statIcon}>🔄</div>
          <div className={styles.statContent}>
            <div className={styles.statValue}>{formatTimestamp(playbook?.metadata.generated_at)}</div>
            <div className={styles.statLabel}>Last Updated</div>
            <div className={styles.statMeta}>{playbook?.metadata.experience_rows ?? 0} experiences</div>
          </div>
        </div>
      </div>

      {/* Top Picks */}
      <section className={styles.section}>
        <h3 className={styles.sectionTitle}>🏆 Recommended Bets</h3>

        {topPicksError && (
          <div className={styles.error}>Failed to load picks: {topPicksError.message}</div>
        )}

        {!topPicksError && topPicks.length === 0 && (
          <div className={styles.empty}>No picks available for this date. Try selecting today's date.</div>
        )}

        {!topPicksError && topPicks.length > 0 && (
          <div className={styles.picksList}>
            {topPicks.map((pick, idx) => (
              <div key={`${pick.win_market_id}-${pick.selection_name}`} className={styles.pickCard}>
                <div className={styles.pickRank}>#{idx + 1}</div>
                <div className={styles.pickMain}>
                  <div className={styles.pickHeader}>
                    <h4 className={styles.pickHorse}>{pick.selection_name}</h4>
                    <span className={`${styles.confidenceBadge} ${styles[`confidence${pick.confidence.replace(/\s/g, '')}`]}`}>
                      {pick.confidence}
                    </span>
                  </div>
                  <div className={styles.pickRace}>
                    {pick.track} • Race {pick.race_no}
                  </div>
                  <p className={styles.pickSummary}>{pick.summary}</p>
                  <div className={styles.pickStats}>
                    <div className={styles.pickStat}>
                      <span className={styles.pickStatLabel}>Win Prob</span>
                      <span className={styles.pickStatValue}>{(pick.model_prob * 100).toFixed(1)}%</span>
                    </div>
                    {pick.win_odds && (
                      <div className={styles.pickStat}>
                        <span className={styles.pickStatLabel}>Odds</span>
                        <span className={styles.pickStatValue}>${pick.win_odds.toFixed(2)}</span>
                      </div>
                    )}
                    {pick.edge !== null && (
                      <div className={styles.pickStat}>
                        <span className={styles.pickStatLabel}>Edge</span>
                        <span className={`${styles.pickStatValue} ${pick.edge && pick.edge > 0 ? styles.positive : styles.negative}`}>
                          {pick.edge && pick.edge > 0 ? '+' : ''}{pick.edge ? (pick.edge * 100).toFixed(1) : '0.0'}%
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Quick Action Guide */}
      <section className={styles.section}>
        <h3 className={styles.sectionTitle}>💡 Betting Guide</h3>
        <div className={styles.guideGrid}>
          <div className={styles.guideCard}>
            <div className={styles.guideIcon}>✅</div>
            <h4>High Confidence</h4>
            <p>Focus on picks with "Very High" or "High" confidence badges. These have strong model agreement.</p>
          </div>
          <div className={styles.guideCard}>
            <div className={styles.guideIcon}>📈</div>
            <h4>Positive Edge</h4>
            <p>Look for green edge percentages. These indicate the model finds more value than the market price suggests.</p>
          </div>
          <div className={styles.guideCard}>
            <div className={styles.guideIcon}>🎯</div>
            <h4>Win Probability</h4>
            <p>The model's calibrated win chance. Higher is better, but also check the odds for value.</p>
          </div>
          <div className={styles.guideCard}>
            <div className={styles.guideIcon}>💰</div>
            <h4>Stake Sizing</h4>
            <p>Use the Playbook tab to see recommended stake sizes from ACE's best-performing strategies.</p>
          </div>
        </div>
      </section>

      {/* Raw Data Modal */}
      {showRawData && (
        <div className={styles.modal} onClick={() => setShowRawData(false)}>
          <div className={styles.modalContent} onClick={(e) => e.stopPropagation()}>
            <div className={styles.modalHeader}>
              <h3>Raw API Data</h3>
              <button onClick={() => setShowRawData(false)} className={styles.modalClose}>✕</button>
            </div>
            <div className={styles.modalBody}>
              <h4>Top Picks Response</h4>
              <pre className={styles.codeBlock}>{JSON.stringify(topPicksData, null, 2)}</pre>
              <h4>Playbook Response</h4>
              <pre className={styles.codeBlock}>{JSON.stringify(playbookData, null, 2)}</pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
