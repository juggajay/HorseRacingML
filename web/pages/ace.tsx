import { useState } from 'react';
import useSWR from 'swr';
import Link from 'next/link';
import {
  fetchPlaybook,
  runAce,
  type PlaybookResponse,
  type AceRunResponse,
} from '../lib/api';
import styles from '../styles/Ace.module.css';

const formatPercent = (value: number | null | undefined, decimals = 1) => {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  return `${value.toFixed(decimals)}%`;
};

const formatNumber = (value: number | null | undefined) => {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  return value.toLocaleString();
};

export default function AceConsole() {
  const { data: playbookData, mutate } = useSWR<PlaybookResponse>('playbook', fetchPlaybook, {
    revalidateOnFocus: false,
  });
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastRun, setLastRun] = useState<AceRunResponse | null>(null);

  const latestSnapshot = playbookData?.latest;
  const globalStats = latestSnapshot?.global;
  const metadata = latestSnapshot?.metadata;
  const history = playbookData?.history ?? [];

  const handleRun = async () => {
    setIsRunning(true);
    setError(null);
    try {
      const response = await runAce();
      setLastRun(response);
      await mutate();
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Failed to run ACE.');
      }
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.headerTop}>
          <div className={styles.titleBlock}>
            <h1>ACE Operations Console</h1>
            <p>
              Manage the autonomous context engine (ACE) that powers the playbook. The LightGBM model delivers raw
              win probabilities, while ACE learns betting contexts by replaying entire race days and curating the
              strategies you see on the dashboard.
            </p>
          </div>
          <div className={styles.headerLinks}>
            <Link href="/" className={styles.backLink}>
              ← Back to Dashboard
            </Link>
          </div>
        </div>

        <div className={styles.runPanel}>
          <div className={styles.runCard}>
            <h2>Run ICE Today</h2>
            <p className={styles.runDescription}>
              Pulls today&apos;s Punting Form data, appends it to the ACE knowledge base, and regenerates the playbook in one
              step. Use this after the day&apos;s meetings are available.
            </p>
            <button type="button" className={styles.runButton} onClick={handleRun} disabled={isRunning}>
              {isRunning ? 'Running…' : 'Run ICE'}
            </button>
            {error && <div className={styles.errorBox}>{error}</div>}
            {lastRun && !error && (
              <div className={styles.successMessage}>
                Last run completed at {new Date(lastRun.finished_at).toLocaleString()} &middot; {formatNumber(lastRun.experience_rows)}
                {' '}experiences evaluated
              </div>
            )}
          </div>

          <div className={styles.statusCard}>
            <h3 className={styles.statusTitle}>Playbook Summary</h3>
            <div className={styles.statusGrid}>
              <div className={styles.statusItem}>
                <strong>{formatPercent(globalStats?.pot_pct, 1)}</strong>
                <span>Global POT</span>
              </div>
              <div className={styles.statusItem}>
                <strong>{formatNumber(globalStats?.total_bets)}</strong>
                <span>Total Bets Simulated</span>
              </div>
              <div className={styles.statusItem}>
                <strong>{formatNumber(metadata?.experience_rows)}</strong>
                <span>Experiences Logged</span>
              </div>
              <div className={styles.statusItem}>
                <strong>{metadata ? new Date(metadata.generated_at).toLocaleString() : '—'}</strong>
                <span>Last Refreshed</span>
              </div>
            </div>
          </div>
        </div>
      </header>

      <main className={styles.body}>
        <section className={styles.infoSection}>
          <article className={styles.infoCard}>
            <h3>Model Engine</h3>
            <p>
              The LightGBM model transforms market prices, form ratings, and historical Betfair features into calibrated
              win probabilities for every runner. It feeds the selections grid in real time.
            </p>
          </article>
          <article className={styles.infoCard}>
            <h3>ACE / ICE Layer</h3>
            <p>
              ICE (our implementation of Agentic Context Engineering) replays races with simulated staking strategies,
              records the outcomes, and curates a playbook of profitable contexts—hot tracks, race types, and strategy
              presets.
            </p>
          </article>
          <article className={styles.infoCard}>
            <h3>What the Playbook Shows</h3>
            <p>
              The dashboard&apos;s Playbook POT tile, strategy focus card, and context grids are generated from ACE results.
              Each daily run keeps these insights aligned with the latest racing conditions.
            </p>
          </article>
        </section>

        <section className={styles.historySection}>
          <h2>Recent ACE Runs</h2>
          <div className={styles.historyList}>
            {lastRun && (
              <div className={styles.historyItem}>
                <span>
                  {lastRun.target_date} &middot; {formatPercent(lastRun.global_pot_pct, 1)} POT &middot; {formatNumber(lastRun.experience_rows)}
                  {' '}experiences
                </span>
                <span>
                  Schema +{formatNumber(lastRun.schema_runners_added)} runners &middot; Duration {lastRun.duration_seconds.toFixed(1)}s
                </span>
              </div>
            )}
            {history
              .slice(-4)
              .reverse()
              .map((snapshot) => (
                <div key={snapshot.metadata.generated_at} className={styles.historyItem}>
                  <span>
                    {snapshot.metadata.generated_at.slice(0, 10)} &middot; {formatPercent(snapshot.global.pot_pct, 1)} POT
                  </span>
                  <span>{formatNumber(snapshot.global.total_bets)} bets analysed</span>
                </div>
              ))}
          </div>
        </section>
      </main>
    </div>
  );
}
