import { useMemo, useState } from 'react';
import useSWR from 'swr';
import { fetchSelections, type Runner } from '../lib/api';
import { SelectionTable } from '../components/SelectionTable';
import { RaceCard } from '../components/RaceCard';
import styles from '../styles/Dashboard.module.css';

const todayIso = new Date().toISOString().slice(0, 10);

const fetcher = async (date: string, margin: number) => {
  const data = await fetchSelections(date, margin);
  return data;
};

interface RaceGroup {
  key: string;
  track: string;
  raceNo: number;
  eventDate: string;
  selections: Runner[];
}

export default function Dashboard() {
  const [date, setDate] = useState<string>(todayIso);
  const [margin, setMargin] = useState<number>(1.05);
  const [selectedTrack, setSelectedTrack] = useState<string>('all');
  const [selectedRace, setSelectedRace] = useState<string>('all');

  const { data, error, isLoading } = useSWR(['selections', date, margin], ([, d, m]) => fetcher(d, m), {
    revalidateOnFocus: false,
  });

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

  const groupedRaces = useMemo<RaceGroup[]>(() => {
    const groups = new Map<string, RaceGroup>();
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

  const edgeThreshold = (margin - 1) * 100;

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.titleRow}>
          <div className={styles.titleBlock}>
            <h1>HorseRacingML</h1>
            <p>
              ML-powered confidence signals blended with Betfair market intelligence. Track the top value runners
              across Australia with fast, responsive insights.
            </p>
          </div>
          <div className={styles.metrics}>
            <div className={styles.metricCard}>
              <span className={styles.metricLabel}>Selections Shown</span>
              <span className={styles.metricValue}>{filteredSelections.length}</span>
              <span className={styles.metricTrend}>{allSelections.length} total for {date}</span>
            </div>
            <div className={styles.metricCard}>
              <span className={styles.metricLabel}>Average Edge</span>
              <span className={styles.metricValue}>{(avgEdge * 100).toFixed(1)}%</span>
              <span className={styles.metricTrend}>Threshold ≥ {edgeThreshold.toFixed(1)}%</span>
            </div>
            <div className={styles.metricCard}>
              <span className={styles.metricLabel}>Average Odds</span>
              <span className={styles.metricValue}>${avgOdds.toFixed(2)}</span>
              <span className={styles.metricTrend}>{groupedRaces.length} races filtered</span>
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
                <label htmlFor="date-input">
                  Race Date
                </label>
                <input
                  id="date-input"
                  className={styles.controlInput}
                  type="date"
                  value={date}
                  onChange={(event) => setDate(event.target.value)}
                />
              </div>
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
                  value={(margin - 1) * 100}
                  onChange={(event) => {
                    const value = Number(event.target.value);
                    setMargin(1 + value / 100);
                  }}
                />
              </div>
              <div className={styles.controlField}>
                <label htmlFor="track-select">
                  Track
                </label>
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
                  <label htmlFor="race-select">
                    Race
                  </label>
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
                <strong>{(filteredSelections.filter((runner) => runner.model_prob >= 0.6).length)}</strong>
                <span>High confidence runners</span>
              </div>
              <div className={styles.summaryItem}>
                <strong>{filteredSelections.filter((runner) => (runner.model_prob - runner.implied_prob) >= 0.1).length}</strong>
                <span>Edges ≥ 10%</span>
              </div>
            </div>
          </section>
        </aside>

        <main className={styles.main}>
          <section>
            <div className={styles.sectionHeader}>
              <h2 className={styles.sectionTitle}>Value Heatmap</h2>
            </div>

            {error && (
              <div className={styles.errorBox}>Failed to load selections – {error.message}</div>
            )}

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
                  />
                ))}
              </div>
            )}
          </section>

          <section className={styles.tableSection}>
            <h3>Detailed Selections</h3>
            <SelectionTable selections={filteredSelections} />
          </section>
        </main>
      </div>
    </div>
  );
}
