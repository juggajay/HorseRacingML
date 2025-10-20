import Head from 'next/head';
import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import useSWR from 'swr';
import { fetchPfLive, type PfLiveResponse, type PfMeetingSummary } from '../lib/api';
import styles from '../styles/PfLivePage.module.css';

const getTodayInAustralia = () => {
  const now = new Date();
  const australianDate = new Date(now.toLocaleString('en-US', { timeZone: 'Australia/Sydney' }));
  const year = australianDate.getFullYear();
  const month = String(australianDate.getMonth() + 1).padStart(2, '0');
  const day = String(australianDate.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
};

const todayIso = getTodayInAustralia();
const ALL_OPTION = 'ALL';

const preferredColumnOrder = [
  'event_date',
  'track',
  'state_code',
  'race_no',
  'race_time',
  'meeting_id',
  'race_id',
  'win_market_id',
  'selection_id',
  'tab_number',
  'selection_name',
  'runner_status',
  'is_scratched',
  'pf_ai_rank',
  'pf_ai_score',
  'pf_ai_price',
  'win_odds',
  'betfair_horse_rating',
  'win_rate',
];

const formatCellValue = (value: unknown): string => {
  if (value === null || value === undefined) {
    return '';
  }
  if (Array.isArray(value)) {
    return value.map((item) => formatCellValue(item)).join(', ');
  }
  if (value instanceof Date) {
    return value.toISOString();
  }
  if (typeof value === 'number') {
    const isInt = Number.isInteger(value);
    return isInt ? value.toString() : value.toFixed(3).replace(/\.?0+$/, '');
  }
  if (typeof value === 'object') {
    try {
      return JSON.stringify(value);
    } catch {
      return String(value);
    }
  }
  return String(value);
};

const isRunnerScratched = (runner: Record<string, unknown>) => {
  const statusRaw = runner['runner_status'];
  const status = typeof statusRaw === 'string' ? statusRaw.toLowerCase() : '';
  const scratchFlags = ['scratch', 'withdraw', 'removed'];
  if (scratchFlags.some((flag) => status.includes(flag))) {
    return true;
  }
  const scratchValue = runner['is_scratched'];
  if (typeof scratchValue === 'boolean') {
    return scratchValue;
  }
  if (typeof scratchValue === 'string') {
    return ['true', '1', 'yes'].includes(scratchValue.toLowerCase());
  }
  if (typeof scratchValue === 'number') {
    return scratchValue === 1;
  }
  return false;
};

const buildColumnOrder = (response?: PfLiveResponse) => {
  if (!response) return [];
  const set = new Set(response.columns);
  const prioritized = preferredColumnOrder.filter((col) => set.has(col));
  const remaining = response.columns.filter((col) => !prioritized.includes(col));
  return [...prioritized, ...remaining];
};

const extractTracks = (data?: PfLiveResponse) => {
  if (!data) return [];
  const tracks = new Set<string>();
  data.runners.forEach((runner) => {
    const value = runner['track'];
    if (typeof value === 'string' && value.trim().length > 0) {
      tracks.add(value);
    }
  });
  return Array.from(tracks).sort((a, b) => a.localeCompare(b));
};

const extractRaces = (data: PfLiveResponse | undefined, track: string | null) => {
  if (!data) return [];
  const races = new Set<string>();
  data.runners.forEach((runner) => {
    const runnerTrack = typeof runner['track'] === 'string' ? runner['track'] : null;
    if (track && runnerTrack !== track) {
      return;
    }
    const raceValue =
      runner['race_no'] ?? runner['race_number'] ?? runner['raceNo'] ?? runner['raceNumber'];
    if (raceValue === null || raceValue === undefined) {
      return;
    }
    races.add(String(raceValue));
  });
  return Array.from(races).sort((a, b) => Number(a) - Number(b));
};

const describeMeeting = (meeting: PfMeetingSummary) => {
  if (!meeting.track) return `${meeting.runner_count} runners`;
  const state = meeting.state_code ? ` (${meeting.state_code})` : '';
  const races = meeting.races.length ? ` • Races: ${meeting.races.join(', ')}` : '';
  return `${meeting.track}${state} • ${meeting.runner_count} runners${races}`;
};

export default function PfLivePage() {
  const [date, setDate] = useState<string>(todayIso);
  const [trackFilter, setTrackFilter] = useState<string>(ALL_OPTION);
  const [raceFilter, setRaceFilter] = useState<string>(ALL_OPTION);

  const { data, error, isLoading, isValidating, mutate } = useSWR<PfLiveResponse>(
    ['pf-live', date],
    ([, d]: [string, string]) => fetchPfLive(d),
    { revalidateOnFocus: false }
  );

  useEffect(() => {
    setTrackFilter(ALL_OPTION);
    setRaceFilter(ALL_OPTION);
  }, [date]);

  useEffect(() => {
    setRaceFilter(ALL_OPTION);
  }, [trackFilter]);

  const columnOrder = useMemo(() => buildColumnOrder(data), [data]);
  const tracks = useMemo(() => extractTracks(data), [data]);
  const races = useMemo(() => extractRaces(data, trackFilter === ALL_OPTION ? null : trackFilter), [data, trackFilter]);

  const filteredRows = useMemo(() => {
    if (!data) return [];
    return data.runners.filter((runner) => {
      const trackValue = typeof runner['track'] === 'string' ? runner['track'] : '';
      const trackMatches = trackFilter === ALL_OPTION || trackValue === trackFilter;
      if (!trackMatches) {
        return false;
      }
      if (raceFilter === ALL_OPTION) {
        return true;
      }
      const raceValue =
        runner['race_no'] ?? runner['race_number'] ?? runner['raceNo'] ?? runner['raceNumber'];
      return String(raceValue ?? '') === raceFilter;
    });
  }, [data, trackFilter, raceFilter]);

  const scratchedCount = useMemo(
    () => filteredRows.filter((runner) => isRunnerScratched(runner)).length,
    [filteredRows]
  );

  const handleForceRefresh = async () => {
    try {
      await mutate(() => fetchPfLive(date, true), {
        revalidate: false,
        populateCache: true,
      });
    } catch (refreshError) {
      // Surface the error in console; SWR will expose it through the hook as well.
      console.error(refreshError);
    }
  };

  return (
    <div className={styles.page}>
      <Head>
        <title>PF Live Data Explorer | HorseRacingML</title>
      </Head>
      <header className={styles.header}>
        <div className={styles.headerInner}>
          <div>
            <p className={styles.kicker}>PuntingForm Live Snapshot</p>
            <h1 className={styles.title}>Daily Meetings &amp; Runner Data</h1>
            <p className={styles.subtitle}>
              Inspect every field returned by the PuntingForm API for the selected date. Use the filters to
              focus on a single track or race and identify scratched runners quickly.
            </p>
          </div>
          <Link href="/" className={styles.backLink}>
            ← Back to dashboard
          </Link>
        </div>
      </header>

      <main className={styles.main}>
        <section className={styles.controlsSection}>
          <div className={styles.controlGroup}>
            <label htmlFor="pf-live-date">Meeting date</label>
            <input
              id="pf-live-date"
              type="date"
              value={date}
              onChange={(event) => setDate(event.target.value)}
            />
          </div>
          <div className={styles.controlGroup}>
            <label htmlFor="pf-live-track">Track</label>
            <select
              id="pf-live-track"
              value={trackFilter}
              onChange={(event) => setTrackFilter(event.target.value)}
            >
              <option value={ALL_OPTION}>All tracks</option>
              {tracks.map((track) => (
                <option key={track} value={track}>
                  {track}
                </option>
              ))}
            </select>
          </div>
          <div className={styles.controlGroup}>
            <label htmlFor="pf-live-race">Race</label>
            <select
              id="pf-live-race"
              value={raceFilter}
              onChange={(event) => setRaceFilter(event.target.value)}
            >
              <option value={ALL_OPTION}>All races</option>
              {races.map((race) => (
                <option key={race} value={race}>
                  Race {race}
                </option>
              ))}
            </select>
          </div>
          <button
            type="button"
            className={styles.refreshButton}
            onClick={handleForceRefresh}
            disabled={isLoading}
            title="Force refresh from PuntingForm (ignores cache)"
          >
            {isValidating ? 'Refreshing…' : 'Force refresh'}
          </button>
        </section>

        <section className={styles.summarySection}>
          <div className={styles.summaryCard}>
            <span className={styles.summaryLabel}>Runners</span>
            <strong className={styles.summaryValue}>{filteredRows.length}</strong>
          </div>
          <div className={styles.summaryCard}>
            <span className={styles.summaryLabel}>Scratched</span>
            <strong className={styles.summaryValue}>{scratchedCount}</strong>
          </div>
          <div className={styles.summaryCard}>
            <span className={styles.summaryLabel}>Meetings</span>
            <strong className={styles.summaryValue}>{data?.meetings.length ?? 0}</strong>
          </div>
          <div className={styles.summaryCard}>
            <span className={styles.summaryLabel}>Source</span>
            <strong className={styles.summaryValue}>{data?.source ?? '—'}</strong>
          </div>
        </section>

        {error && (
          <div className={styles.alert}>
            <p>{error.message}</p>
          </div>
        )}

        {!error && data && data.meetings.length > 0 && (
          <section className={styles.meetingsSection}>
            <h2>Meetings overview</h2>
            <ul className={styles.meetingList}>
              {data.meetings.map((meeting) => (
                <li key={`${meeting.track}-${meeting.state_code ?? 'na'}`}>
                  <p>{describeMeeting(meeting)}</p>
                </li>
              ))}
            </ul>
          </section>
        )}

        <section className={styles.tableSection}>
          {isLoading && !data ? (
            <div className={styles.placeholder}>Loading PuntingForm runners…</div>
          ) : (
            <div className={styles.tableWrapper}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    {columnOrder.map((column) => (
                      <th key={column}>{column}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {filteredRows.map((runner, index) => {
                    const keyParts = [
                      runner['win_market_id'],
                      runner['selection_id'],
                      runner['runner_id'],
                      index,
                    ];
                    const rowKey = keyParts.filter((part) => part !== undefined).join('-') || `row-${index}`;
                    const scratched = isRunnerScratched(runner);
                    return (
                      <tr key={rowKey} className={scratched ? styles.scratchedRow : undefined}>
                        {columnOrder.map((column) => (
                          <td key={column}>{formatCellValue(runner[column])}</td>
                        ))}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              {!filteredRows.length && (
                <div className={styles.placeholder}>No runners match the current filters.</div>
              )}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
