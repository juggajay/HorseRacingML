import { useMemo, useState } from 'react';
import type { Runner, PlaybookResponse } from '../lib/api';
import { RaceCard } from './RaceCard';
import styles from '../styles/RacesTab.module.css';

interface RacesTabProps {
  selectionsData?: { selections: Runner[]; message?: string };
  playbookData?: PlaybookResponse;
  date: string;
  setDate: (date: string) => void;
  margin: number;
  setMargin: (margin: number) => void;
  isLoading: boolean;
  error?: Error;
}

export default function RacesTab({
  selectionsData,
  playbookData,
  date,
  setDate,
  margin,
  setMargin,
  isLoading,
  error,
}: RacesTabProps) {
  const [selectedTrack, setSelectedTrack] = useState<string>('all');
  const [selectedRace, setSelectedRace] = useState<string>('all');

  const allSelections = selectionsData?.selections ?? [];

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

  const playbookTrackMap = useMemo(() => {
    const map = new Map();
    (playbookData?.latest?.tracks ?? []).forEach((track) => {
      map.set(track.track, track);
    });
    return map;
  }, [playbookData]);

  const edgeThreshold = (margin - 1) * 100;

  return (
    <div className={styles.racesTab}>
      <div className={styles.header}>
        <div>
          <h2 className={styles.title}>Race Cards & Value Analysis</h2>
          <p className={styles.subtitle}>Detailed race-by-race breakdown with model probabilities</p>
        </div>
      </div>

      {/* Filters */}
      <div className={styles.filters}>
        <div className={styles.filterGroup}>
          <label>Date</label>
          <input
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            className={styles.filterInput}
          />
        </div>

        <div className={styles.filterGroup}>
          <label>Track</label>
          <select
            value={selectedTrack}
            onChange={(e) => {
              setSelectedTrack(e.target.value);
              setSelectedRace('all');
            }}
            className={styles.filterInput}
          >
            <option value="all">All Tracks ({tracks.length})</option>
            {tracks.map((track) => (
              <option key={track} value={track}>
                {track}
              </option>
            ))}
          </select>
        </div>

        {selectedTrack !== 'all' && (
          <div className={styles.filterGroup}>
            <label>Race</label>
            <select
              value={selectedRace}
              onChange={(e) => setSelectedRace(e.target.value)}
              className={styles.filterInput}
            >
              <option value="all">All Races ({raceOptions.length})</option>
              {raceOptions.map((race) => (
                <option key={race} value={race}>
                  Race {race}
                </option>
              ))}
            </select>
          </div>
        )}

        <div className={styles.filterGroup}>
          <label>
            Margin Threshold <span className={styles.filterMeta}>{edgeThreshold.toFixed(1)}% edge</span>
          </label>
          <input
            type="range"
            min={0}
            max={20}
            step={0.5}
            value={Math.min(Math.max((margin - 1) * 100, 0), 20)}
            onChange={(e) => {
              const value = Number(e.target.value);
              setMargin(1 + value / 100);
            }}
            className={styles.filterSlider}
          />
        </div>
      </div>

      {/* Stats Summary */}
      <div className={styles.summary}>
        <div className={styles.summaryItem}>
          <span className={styles.summaryValue}>{groupedRaces.length}</span>
          <span className={styles.summaryLabel}>Races Found</span>
        </div>
        <div className={styles.summaryItem}>
          <span className={styles.summaryValue}>{filteredSelections.length}</span>
          <span className={styles.summaryLabel}>Runners</span>
        </div>
        <div className={styles.summaryItem}>
          <span className={styles.summaryValue}>{filteredSelections.filter((r) => r.model_prob >= 0.20).length}</span>
          <span className={styles.summaryLabel}>High Confidence</span>
        </div>
        <div className={styles.summaryItem}>
          <span className={styles.summaryValue}>{filteredSelections.filter((r) => (r.model_prob - r.implied_prob) >= 0.1).length}</span>
          <span className={styles.summaryLabel}>Strong Edges</span>
        </div>
      </div>

      {/* Race Cards */}
      {error && (
        <div className={styles.error}>
          <strong>Failed to load races:</strong> {error.message}
          {error.message.includes('timeout') && (
            <div style={{ marginTop: '0.75rem', fontSize: '0.95rem' }}>
              <strong>Troubleshooting:</strong>
              <ul style={{ marginTop: '0.5rem', paddingLeft: '1.5rem' }}>
                <li>Make sure you've selected a specific date (not a date range)</li>
                <li>Try lowering the margin threshold to reduce data size</li>
                <li>The backend API might be loading a large dataset - this can take up to 2 minutes</li>
                <li>Check that the Railway backend is running: <a href="https://horseracingml-production.up.railway.app/health" target="_blank" style={{ color: '#60a5fa' }}>Health Check</a></li>
              </ul>
            </div>
          )}
        </div>
      )}

      {isLoading && (
        <div className={styles.loading}>
          <div className={styles.spinner} />
          <p>Loading race cards...</p>
        </div>
      )}

      {!isLoading && !error && groupedRaces.length === 0 && (
        <div className={styles.empty}>
          <p>No races found matching your filters.</p>
          <p className={styles.emptyHint}>
            Try lowering the margin threshold or selecting a different date/track.
          </p>
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
    </div>
  );
}
