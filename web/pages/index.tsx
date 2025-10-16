import { useEffect, useMemo, useState } from 'react';
import useSWR from 'swr';
import {
  fetchSelections,
  fetchPlaybook,
  type Runner,
  type PlaybookResponse,
  type PlaybookStrategy,
  type PlaybookTrackInsight,
} from '../lib/api';
import { SelectionTable } from '../components/SelectionTable';
import { RaceCard } from '../components/RaceCard';
import styles from '../styles/Dashboard.module.css';

const todayIso = new Date().toISOString().slice(0, 10);

const selectionFetcher = async (date: string, margin: number) => {
  const data = await fetchSelections(date, margin);
  return data;
};

const formatPercent = (value: number | null | undefined, decimals = 1) => {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  return `${value.toFixed(decimals)}%`;
};

const formatRatioPercent = (value: number | null | undefined, decimals = 1) => {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  return `${(value * 100).toFixed(decimals)}%`;
};

const formatCurrency = (value: number | null | undefined, decimals = 1) => {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  return `$${value.toFixed(decimals)}`;
};

const getStrategyLabel = (strategy: PlaybookStrategy) => {
  const params = (strategy.params ?? {}) as Record<string, unknown>;
  const parts: string[] = [];
  if (typeof params.margin === 'number') parts.push(`Margin ${(params.margin * 100 - 100).toFixed(0)}%`);
  if (typeof params.top_n === 'number') parts.push(`Top ${params.top_n}`);
  if (typeof params.stake === 'number') parts.push(`Stake ${params.stake}`);
  return parts.length ? parts.join(' • ') : strategy.strategy_id;
};

const formatTimestamp = (iso: string | undefined) => {
  if (!iso) return null;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return null;
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

export default function Dashboard() {
  const [date, setDate] = useState<string>(todayIso);
  const [margin, setMargin] = useState<number>(1.05);
  const [selectedTrack, setSelectedTrack] = useState<string>('all');
  const [selectedRace, setSelectedRace] = useState<string>('all');
  const [selectedStrategyId, setSelectedStrategyId] = useState<string>('');

  const { data, error, isLoading } = useSWR(['selections', date, margin], ([, d, m]) => selectionFetcher(d, m), {
    revalidateOnFocus: false,
  });
  const { data: playbookData } = useSWR<PlaybookResponse>('playbook', fetchPlaybook, {
    revalidateOnFocus: false,
  });

  const playbookSnapshot = playbookData?.latest;
  const playbookStrategies = playbookSnapshot?.strategies ?? [];

  useEffect(() => {
    if (!selectedStrategyId && playbookStrategies.length) {
      setSelectedStrategyId(playbookStrategies[0].strategy_id);
    }
  }, [selectedStrategyId, playbookStrategies]);

  const selectedStrategy = useMemo(
    () => playbookStrategies.find((strategy) => strategy.strategy_id === selectedStrategyId),
    [playbookStrategies, selectedStrategyId],
  );

  const strategyParams = useMemo(() => (selectedStrategy?.params ?? {}) as Record<string, unknown>, [selectedStrategy]);
  const recommendedMargin = typeof strategyParams.margin === 'number' ? (strategyParams.margin as number) : undefined;
  const recommendedTopN = typeof strategyParams.top_n === 'number' ? (strategyParams.top_n as number) : undefined;
  const recommendedStake = typeof strategyParams.stake === 'number' ? (strategyParams.stake as number) : undefined;

  const allSelections = data?.selections ?? [];

  const tracks = useMemo(() => {
    return Array.from(new Set(allSelections.map((item) => item.track))).sort();
  }, [allSelections]);

  const filteredSelections = useMemo(() => {
    return allSelections.filter((item) => {
      if (selectedTrack !== 'all' && item.track !== selectedTrack) return false;
      if (selectedRace !== 'all' && item.race_no !== Number(selectedRace)) return false;
      return true;
    });
  }, [allSelections, selectedRace, selectedTrack]);

  const groupedRaces = useMemo(() => {
    const groups = new Map<string, { key: string; track: string; raceNo: number; eventDate: string; selections: Runner[] }>();
    filteredSelections.forEach((runner) => {
      const key = `${runner.track}-${runner.race_no}`;
      if (!groups.has(key)) {
        groups.set(key, {
          key,
          track: runner.track,
          raceNo: runner.race_no,
          eventDate: runner.event_date,
          selections: [],
        });
      }
      groups.get(key)?.selections.push(runner);
    });
    return Array.from(groups.values()).sort((a, b) => a.raceNo - b.raceNo);
  }, [filteredSelections]);

  const raceOptions = useMemo(() => {
    if (selectedTrack === 'all') return [];
    return Array.from(new Set(allSelections.filter((item) => item.track === selectedTrack).map((item) => item.race_no)))
      .sort((a, b) => a - b);
  }, [allSelections, selectedTrack]);

  const avgEdge = useMemo(() => {
    if (!filteredSelections.length) return 0;
    const total = filteredSelections.reduce((sum, runner) => sum + (runner.model_prob - runner.implied_prob), 0);
    return total / filteredSelections.length;
  }, [filteredSelections]);

  const avgOdds = useMemo(() => {
    if (!filteredSelections.length) return 0;
    const total = filteredSelections.reduce((sum, runner) => sum + runner.win_odds, 0);
    return total / filteredSelections.length;
  }, [filteredSelections]);

  const playbookTrackMap = useMemo(() => {
    const map = new Map<string, PlaybookTrackInsight>();
    (playbookSnapshot?.tracks ?? []).forEach((track) => {
      map.set(track.track, track);
    });
    return map;
  }, [playbookSnapshot]);

  const topTracks = useMemo(() => (playbookSnapshot?.tracks ?? []).slice(0, 6), [playbookSnapshot]);
  const topContexts = useMemo(() => (playbookSnapshot?.contexts ?? []).slice(0, 6), [playbookSnapshot]);

  const lastUpdated = formatTimestamp(playbookSnapshot?.metadata.generated_at);
  const experienceRows = playbookSnapshot?.metadata.experience_rows ?? 0;
  const strategiesEvaluated = playbookSnapshot?.metadata.strategies_evaluated ?? 0;
  const globalStats = playbookSnapshot?.global;

  const edgeThreshold = (margin - 1) * 100;

  const handleApplyStrategyMargin = () => {
    if (recommendedMargin) {
      const sliderPercent = Math.max(0, Math.min((recommendedMargin - 1) * 100, 20));
      setMargin(1 + sliderPercent / 100);
    }
  };

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.titleRow}>
          <div className={styles.titleBlock}>
            <h1>HorseRacingML</h1>
            <p>
              ACE-powered intelligence surfaces the best value contexts across Australian racing. Explore the playbook,
              apply strategy-aligned margins, and scan today&apos;s runners with confidence.
            </p>
            {lastUpdated && <span className={styles.playbookMeta}>Playbook refreshed {lastUpdated}</span>}
          </div>
          <div className={styles.metrics}>
            <div className={styles.metricCard}>
              <span className={styles.metricLabel}>Playbook POT</span>
              <span className={styles.metricValue}>{formatPercent(globalStats?.pot_pct ?? null, 1)}</span>
              <span className={styles.metricTrend}>
                {globalStats ? `${globalStats.total_bets} bets analysed` : 'Awaiting ACE run'}
              </span>
            </div>
            <div className={styles.metricCard}>
              <span className={styles.metricLabel}>Hit Rate</span>
              <span className={styles.metricValue}>{formatRatioPercent(globalStats?.hit_rate ?? null, 1)}</span>
              <span className={styles.metricTrend}>
                {strategiesEvaluated ? `${strategiesEvaluated} strategies evaluated` : '—'}
              </span>
            </div>
            <div className={styles.metricCard}>
              <span className={styles.metricLabel}>Experiences Logged</span>
              <span className={styles.metricValue}>{experienceRows.toLocaleString()}</span>
              <span className={styles.metricTrend}>Margin threshold ≥ {edgeThreshold.toFixed(1)}%</span>
            </div>
          </div>
        </div>
      </header>

      <div className={styles.body}>
        <aside className={styles.sidebar}>
          <section className={styles.panel}>
            <h2>Filters</h2>
            <div className={styles.controlGroup}>
              <div className={styles.controlField}>
                <label htmlFor="date-input">Race Date</label>
                <input
                  id="date-input"
                  className={styles.controlInput}
                  type="date"
                  value={date}
                  onChange={(event) => setDate(event.target.value)}
                />
              </div>

              {playbookStrategies.length > 0 && (
                <div className={styles.controlField}>
                  <label htmlFor="strategy-select">Strategy</label>
                  <div className={styles.strategyControl}>
                    <select
                      id="strategy-select"
                      className={styles.controlInput}
                      value={selectedStrategyId}
                      onChange={(event) => setSelectedStrategyId(event.target.value)}
                    >
                      {playbookStrategies.map((strategy) => (
                        <option key={strategy.strategy_id} value={strategy.strategy_id}>
                          {getStrategyLabel(strategy)}
                        </option>
                      ))}
                    </select>
                    {recommendedMargin && (
                      <button type="button" className={styles.inlineButton} onClick={handleApplyStrategyMargin}>
                        Apply {formatPercent((recommendedMargin - 1) * 100, 1)} margin
                      </button>
                    )}
                  </div>
                  {(recommendedTopN || recommendedStake) && (
                    <p className={styles.helperText}>
                      {recommendedTopN ? `Top ${recommendedTopN} runners per race` : ''}
                      {recommendedTopN && recommendedStake ? ' • ' : ''}
                      {recommendedStake ? `Stake ${recommendedStake}u` : ''}
                    </p>
                  )}
                </div>
              )}

              <div className={styles.controlField}>
                <label htmlFor="margin-slider">
                  Margin Threshold <span>{edgeThreshold.toFixed(1)}% edge</span>
                </label>
                <input
                  id="margin-slider"
                  className={`${styles.controlInput} ${styles.slider}`}
                  type="range"
                  min={0}
                  max={20}
                  step={0.5}
                  value={Math.min(Math.max((margin - 1) * 100, 0), 20)}
                  onChange={(event) => {
                    const value = Number(event.target.value);
                    setMargin(1 + value / 100);
                  }}
                />
              </div>

              <div className={styles.controlField}>
                <label htmlFor="track-select">Track</label>
                <select
                  id="track-select"
                  className={styles.controlInput}
                  value={selectedTrack}
                  onChange={(event) => {
                    setSelectedTrack(event.target.value);
                    setSelectedRace('all');
                  }}
                >
                  <option value="all">All tracks ({tracks.length})</option>
                  {tracks.map((track) => (
                    <option key={track} value={track}>
                      {track}
                    </option>
                  ))}
                </select>
              </div>

              {selectedTrack !== 'all' && (
                <div className={styles.controlField}>
                  <label htmlFor="race-select">Race</label>
                  <select
                    id="race-select"
                    className={styles.controlInput}
                    value={selectedRace}
                    onChange={(event) => setSelectedRace(event.target.value)}
                  >
                    <option value="all">All races ({raceOptions.length})</option>
                    {raceOptions.map((race) => (
                      <option key={race} value={race}>
                        Race {race}
                      </option>
                    ))}
                  </select>
                </div>
              )}
            </div>
          </section>

          <section className={styles.panel}>
            <h2>Session Snapshot</h2>
            <div className={styles.summaryList}>
              <div className={styles.summaryItem}>
                <strong>{groupedRaces.length}</strong>
                <span>Races with value edges</span>
              </div>
              <div className={styles.summaryItem}>
                <strong>{filteredSelections.filter((runner) => runner.model_prob >= 0.6).length}</strong>
                <span>High confidence runners</span>
              </div>
              <div className={styles.summaryItem}>
                <strong>{filteredSelections.filter((runner) => runner.model_prob - runner.implied_prob >= 0.1).length}</strong>
                <span>Edges ≥ 10%</span>
              </div>
            </div>
          </section>
        </aside>

        <main className={styles.main}>
          {playbookSnapshot && (
            <section className={styles.playbookSection}>
              <div className={styles.sectionHeader}>
                <h2 className={styles.sectionTitle}>ACE Playbook Insights</h2>
                {lastUpdated && <span className={styles.sectionMeta}>Updated {lastUpdated}</span>}
              </div>
              <div className={styles.playbookGrid}>
                <div className={styles.playbookColumn}>
                  <h3>Strategy Focus</h3>
                  {selectedStrategy ? (
                    <div className={styles.strategyCard}>
                      <span className={styles.strategyLabel}>{getStrategyLabel(selectedStrategy)}</span>
                      <div className={styles.strategyMetrics}>
                        <div className={styles.statBlock}>
                          <span className={styles.statLabel}>POT</span>
                          <span className={styles.statValue}>{formatPercent(selectedStrategy.pot_pct, 1)}</span>
                        </div>
                        <div className={styles.statBlock}>
                          <span className={styles.statLabel}>Hit Rate</span>
                          <span className={styles.statValue}>{formatRatioPercent(selectedStrategy.hit_rate, 1)}</span>
                        </div>
                        <div className={styles.statBlock}>
                          <span className={styles.statLabel}>Profit</span>
                          <span className={styles.statValue}>{formatCurrency(selectedStrategy.total_profit, 1)}</span>
                        </div>
                        <div className={styles.statBlock}>
                          <span className={styles.statLabel}>Bets</span>
                          <span className={styles.statValue}>{selectedStrategy.bets}</span>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <p className={styles.helperText}>Playbook will surface strategy stats after the next ACE run.</p>
                  )}
                </div>

                <div className={styles.playbookColumn}>
                  <h3>Hot Tracks</h3>
                  <div className={styles.trackGrid}>
                    {topTracks.length > 0 ? (
                      topTracks.map((track) => (
                        <div key={track.track} className={styles.trackCard}>
                          <div className={styles.trackTitle}>{track.track}</div>
                          <div className={styles.trackStats}>
                            <span>{formatPercent(track.pot_pct, 1)}</span>
                            <span>{track.bets} bets</span>
                          </div>
                        </div>
                      ))
                    ) : (
                      <p className={styles.helperText}>Run ACE to populate track insights.</p>
                    )}
                  </div>
                </div>

                <div className={styles.playbookColumn}>
                  <h3>Context Cues</h3>
                  <div className={styles.contextGrid}>
                    {topContexts.length > 0 ? (
                      topContexts.map((context, index) => (
                        <div key={`${context.track ?? 'ctx'}-${index}`} className={styles.contextCard}>
                          <div className={styles.contextMeta}>
                            <span>{context.track ?? 'Multi-track cluster'}</span>
                            <span>{context.distance_band ?? 'Distance mix'}</span>
                          </div>
                          <div className={styles.contextMeta}>
                            <span>{context.racing_type ?? 'Type'}</span>
                            <span>{context.race_type ?? ''}</span>
                          </div>
                          <div className={styles.contextStats}>
                            <span>{formatPercent(context.pot_pct, 1)}</span>
                            <span>{context.bets} bets</span>
                          </div>
                        </div>
                      ))
                    ) : (
                      <p className={styles.helperText}>Contextual patterns will appear once enough experiences accumulate.</p>
                    )}
                  </div>
                </div>
              </div>
            </section>
          )}

          <section>
            <div className={styles.sectionHeader}>
              <h2 className={styles.sectionTitle}>Value Heatmap</h2>
            </div>

            {error && <div className={styles.errorBox}>Failed to load selections – {error.message}</div>}

            {isLoading && (
              <div className={styles.skeletonGrid}>
                <div className={styles.skeletonCard} />
                <div className={styles.skeletonCard} />
                <div className={styles.skeletonCard} />
              </div>
            )}

            {!isLoading && !error && groupedRaces.length === 0 && (
              <div className={styles.emptyBox}>
                No selections match the current filters. Try lowering the margin threshold or choosing a different track.
              </div>
            )}

            {!isLoading && !error && groupedRaces.length > 0 && (
              <div className={styles.raceGrid}>
                {groupedRaces.map((race) => (
                  <RaceCard
                    key={race.key}
                    track={race.track}
                    raceNo={race.raceNo}
                    selections={race.selections}
                    eventDate={race.eventDate}
                    playbookTrack={playbookTrackMap.get(race.track)}
                  />
                ))}
              </div>
            )}
          </section>

          <section className={styles.tableSection}>
            <h3>Detailed Selections</h3>
            <SelectionTable selections={filteredSelections} />
            <div className={styles.tableFootnote}>
              Showing {filteredSelections.length.toLocaleString()} runners filtered by current settings. Average edge{' '}
              {(avgEdge * 100).toFixed(1)}% • Average odds ${avgOdds.toFixed(2)}
            </div>
          </section>
        </main>
      </div>
    </div>
  );
}
