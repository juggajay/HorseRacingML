import { useState } from 'react';
import useSWR from 'swr';
import { fetchSelections } from '../lib/api';
import { SelectionTable } from '../components/SelectionTable';

const todayIso = new Date().toISOString().slice(0, 10);

const fetcher = async (date: string, margin: number) => {
  const data = await fetchSelections(date, margin);
  return data;
};

export default function Dashboard() {
  const [date, setDate] = useState<string>(todayIso);
  const [margin, setMargin] = useState<number>(1.05);
  const [selectedTrack, setSelectedTrack] = useState<string>('all');
  const [selectedRace, setSelectedRace] = useState<string>('all');

  const { data, error, isLoading } = useSWR(['selections', date, margin], ([, d, m]) => fetcher(d, m), {
    revalidateOnFocus: false,
  });

  const allSelections = data?.selections ?? [];

  // Get unique tracks and races for filtering
  const tracks = Array.from(new Set(allSelections.map((s) => s.track))).sort();
  const races = selectedTrack === 'all'
    ? []
    : Array.from(new Set(allSelections.filter(s => s.track === selectedTrack).map(s => s.race_no))).sort((a, b) => a - b);

  // Filter selections based on selected track and race
  const selections = allSelections.filter(s => {
    if (selectedTrack !== 'all' && s.track !== selectedTrack) return false;
    if (selectedRace !== 'all' && s.race_no !== parseInt(selectedRace)) return false;
    return true;
  });

  return (
    <div className="page">
      <header>
        <h1>HorseRacingML</h1>
        <p>Live selections powered by Betfair + Kash + Top5 priors.</p>
      </header>
      <section className="controls">
        <label>
          Race Date
          <input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
        </label>
        <label>
          Margin
          <input
            type="number"
            min={1}
            step={0.01}
            value={margin}
            onChange={(e) => setMargin(parseFloat(e.target.value) || 1)}
          />
        </label>
        <label>
          Track
          <select value={selectedTrack} onChange={(e) => { setSelectedTrack(e.target.value); setSelectedRace('all'); }}>
            <option value="all">All Tracks ({tracks.length})</option>
            {tracks.map(track => (
              <option key={track} value={track}>{track}</option>
            ))}
          </select>
        </label>
        {selectedTrack !== 'all' && (
          <label>
            Race
            <select value={selectedRace} onChange={(e) => setSelectedRace(e.target.value)}>
              <option value="all">All Races ({races.length})</option>
              {races.map(race => (
                <option key={race} value={race}>Race {race}</option>
              ))}
            </select>
          </label>
        )}
      </section>

      <section className="stats">
        <span>Showing {selections.length} of {allSelections.length} selections</span>
      </section>

      <section className="content">
        {error && <p className="error">Failed to load selections – {error.message}</p>}
        {isLoading && <p>Loading selections…</p>}
        {!isLoading && !error && <SelectionTable selections={selections} />}
      </section>

      <style jsx>{`
        .page {
          min-height: 100vh;
          padding: 2rem;
          max-width: 1200px;
          margin: 0 auto;
        }
        header {
          margin-bottom: 2rem;
        }
        h1 {
          margin: 0 0 0.25rem;
          font-size: 2.5rem;
        }
        p {
          margin: 0;
          color: rgba(148, 163, 184, 0.9);
        }
        .controls {
          display: flex;
          gap: 1.5rem;
          margin-bottom: 2rem;
          flex-wrap: wrap;
        }
        label {
          display: flex;
          flex-direction: column;
          font-size: 0.9rem;
          color: rgba(226, 232, 240, 0.9);
        }
        input, select {
          margin-top: 0.5rem;
          padding: 0.5rem 0.75rem;
          border-radius: 8px;
          border: 1px solid rgba(94, 114, 134, 0.7);
          background: rgba(15, 23, 42, 0.6);
          color: #f8fafc;
          min-width: 180px;
        }
        select {
          cursor: pointer;
        }
        .stats {
          margin-bottom: 1rem;
          padding: 0.75rem 1rem;
          background: rgba(15, 23, 42, 0.4);
          border-radius: 8px;
          border: 1px solid rgba(94, 114, 134, 0.3);
        }
        .stats span {
          color: rgba(226, 232, 240, 0.8);
          font-size: 0.9rem;
        }
        .error {
          color: #f87171;
        }
      `}</style>
    </div>
  );
}
