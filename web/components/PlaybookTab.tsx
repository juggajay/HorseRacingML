import { useState, useMemo } from 'react';
import type { PlaybookResponse, PlaybookStrategy } from '../lib/api';
import styles from '../styles/PlaybookTab.module.css';

interface PlaybookTabProps {
  playbookData?: PlaybookResponse;
  error?: Error;
}

export default function PlaybookTab({ playbookData, error }: PlaybookTabProps) {
  const [selectedStrategyId, setSelectedStrategyId] = useState<string>('');
  const [showRawData, setShowRawData] = useState(false);

  const playbook = playbookData?.latest;
  const strategies = playbook?.strategies ?? [];
  const contexts = playbook?.contexts ?? [];
  const tracks = playbook?.tracks ?? [];
  const globalStats = playbook?.global;

  const selectedStrategy = useMemo(
    () => strategies.find((s) => s.strategy_id === selectedStrategyId) || strategies[0],
    [strategies, selectedStrategyId]
  );

  const formatPercent = (value: number | null | undefined) => {
    if (value === null || value === undefined || Number.isNaN(value)) return '—';
    return `${value.toFixed(1)}%`;
  };

  const formatRatioPercent = (value: number | null | undefined) => {
    if (value === null || value === undefined || Number.isNaN(value)) return '—';
    return `${(value * 100).toFixed(1)}%`;
  };

  const formatCurrency = (value: number | null | undefined) => {
    if (value === null || value === undefined || Number.isNaN(value)) return '—';
    return `$${value.toFixed(2)}`;
  };

  const getStrategyLabel = (strategy: PlaybookStrategy) => {
    const params = (strategy.params ?? {}) as Record<string, unknown>;
    const parts: string[] = [];
    if (typeof params.margin === 'number') parts.push(`${((params.margin - 1) * 100).toFixed(0)}% margin`);
    if (typeof params.top_n === 'number') parts.push(`Top ${params.top_n}`);
    if (typeof params.stake === 'number') parts.push(`$${params.stake} stake`);
    return parts.length ? parts.join(' • ') : strategy.strategy_id;
  };

  return (
    <div className={styles.playbookTab}>
      <div className={styles.header}>
        <div>
          <h2 className={styles.title}>ACE Playbook Insights</h2>
          <p className={styles.subtitle}>Strategic intelligence from autonomous strategy evaluation</p>
        </div>
        <button onClick={() => setShowRawData(!showRawData)} className={styles.rawDataButton}>
          {showRawData ? 'Hide' : 'Show'} Raw Data
        </button>
      </div>

      {error && <div className={styles.error}>Failed to load playbook: {error.message}</div>}

      {!error && !playbook && (
        <div className={styles.empty}>
          <p>No playbook data available.</p>
          <p className={styles.emptyHint}>Run ACE to generate strategic insights.</p>
        </div>
      )}

      {!error && playbook && (
        <>
          {/* Global Stats */}
          <div className={styles.statsGrid}>
            <div className={styles.statCard}>
              <div className={styles.statLabel}>Overall POT</div>
              <div className={styles.statValue}>{formatPercent(globalStats?.pot_pct)}</div>
              <div className={styles.statMeta}>{globalStats?.total_bets ?? 0} total bets</div>
            </div>
            <div className={styles.statCard}>
              <div className={styles.statLabel}>Hit Rate</div>
              <div className={styles.statValue}>{formatRatioPercent(globalStats?.hit_rate)}</div>
              <div className={styles.statMeta}>{strategies.length} strategies evaluated</div>
            </div>
            <div className={styles.statCard}>
              <div className={styles.statLabel}>Total Profit</div>
              <div className={styles.statValue}>{formatCurrency(globalStats?.total_profit)}</div>
              <div className={styles.statMeta}>Across all strategies</div>
            </div>
            <div className={styles.statCard}>
              <div className={styles.statLabel}>Experiences</div>
              <div className={styles.statValue}>{playbook.metadata.experience_rows.toLocaleString()}</div>
              <div className={styles.statMeta}>Logged betting decisions</div>
            </div>
          </div>

          {/* Strategy Selector */}
          {strategies.length > 0 && (
            <section className={styles.section}>
              <h3>Strategy Performance</h3>
              <select
                value={selectedStrategy?.strategy_id || ''}
                onChange={(e) => setSelectedStrategyId(e.target.value)}
                className={styles.strategySelector}
              >
                {strategies.map((strategy) => (
                  <option key={strategy.strategy_id} value={strategy.strategy_id}>
                    {getStrategyLabel(strategy)}
                  </option>
                ))}
              </select>

              {selectedStrategy && (
                <div className={styles.strategyDetails}>
                  <div className={styles.strategyMetrics}>
                    <div className={styles.metric}>
                      <span className={styles.metricLabel}>POT</span>
                      <span className={styles.metricValue}>{formatPercent(selectedStrategy.pot_pct)}</span>
                    </div>
                    <div className={styles.metric}>
                      <span className={styles.metricLabel}>Hit Rate</span>
                      <span className={styles.metricValue}>{formatRatioPercent(selectedStrategy.hit_rate)}</span>
                    </div>
                    <div className={styles.metric}>
                      <span className={styles.metricLabel}>Profit</span>
                      <span className={styles.metricValue}>{formatCurrency(selectedStrategy.total_profit)}</span>
                    </div>
                    <div className={styles.metric}>
                      <span className={styles.metricLabel}>Bets</span>
                      <span className={styles.metricValue}>{selectedStrategy.bets}</span>
                    </div>
                  </div>
                </div>
              )}
            </section>
          )}

          {/* Top Tracks */}
          <section className={styles.section}>
            <h3>Hot Tracks</h3>
            {tracks.length === 0 ? (
              <p className={styles.empty}>No track data available</p>
            ) : (
              <div className={styles.trackGrid}>
                {tracks.slice(0, 6).map((track) => (
                  <div key={track.track} className={styles.trackCard}>
                    <div className={styles.trackName}>{track.track}</div>
                    <div className={styles.trackStats}>
                      <span className={styles.trackPot}>{formatPercent(track.pot_pct)}</span>
                      <span className={styles.trackBets}>{track.bets} bets</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* Context Cues */}
          <section className={styles.section}>
            <h3>Context Cues</h3>
            <p className={styles.sectionDesc}>
              Specific racing scenarios where your strategies perform exceptionally well
            </p>
            {contexts.length === 0 ? (
              <p className={styles.empty}>No context data available</p>
            ) : (
              <div className={styles.contextList}>
                {contexts.slice(0, 10).map((context, idx) => (
                  <div key={`ctx-${idx}`} className={styles.contextCard}>
                    <div className={styles.contextHeader}>
                      <span className={styles.contextTrack}>{context.track ?? 'Multi-track'}</span>
                      <span className={styles.contextPot}>{formatPercent(context.pot_pct)}</span>
                    </div>
                    <div className={styles.contextMeta}>
                      <span>{context.distance_band ?? 'Distance mix'}</span>
                      <span>•</span>
                      <span>{context.racing_type ?? 'Type'}</span>
                      <span>•</span>
                      <span>{context.race_type ?? 'Class'}</span>
                    </div>
                    <div className={styles.contextStats}>
                      {context.bets} bets • {formatRatioPercent((context as any).hit_rate)} hit rate
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        </>
      )}

      {/* Raw Data Modal */}
      {showRawData && (
        <div className={styles.modal} onClick={() => setShowRawData(false)}>
          <div className={styles.modalContent} onClick={(e) => e.stopPropagation()}>
            <div className={styles.modalHeader}>
              <h3>Raw Playbook Data</h3>
              <button onClick={() => setShowRawData(false)} className={styles.modalClose}>✕</button>
            </div>
            <div className={styles.modalBody}>
              <pre className={styles.codeBlock}>{JSON.stringify(playbookData, null, 2)}</pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
