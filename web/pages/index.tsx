import { useState } from 'react';
import useSWR from 'swr';
import {
  fetchSelections,
  fetchPlaybook,
  fetchTopPicks,
  type PlaybookResponse,
  type TopPicksResponse,
} from '../lib/api';
import styles from '../styles/TabbedDashboard.module.css';
import TodayTab from '../components/TodayTab';
import RacesTab from '../components/RacesTab';
import PlaybookTab from '../components/PlaybookTab';
import HistoryTab from '../components/HistoryTab';

// Get today's date in Australian Eastern time (Sydney)
const getTodayInAustralia = () => {
  const now = new Date();
  const australianDate = new Date(now.toLocaleString('en-US', { timeZone: 'Australia/Sydney' }));
  const year = australianDate.getFullYear();
  const month = String(australianDate.getMonth() + 1).padStart(2, '0');
  const day = String(australianDate.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
};

const todayIso = getTodayInAustralia();

type Tab = 'today' | 'races' | 'playbook' | 'history';

export default function Dashboard() {
  const [activeTab, setActiveTab] = useState<Tab>('today');
  const [date, setDate] = useState<string>(todayIso);
  const [margin, setMargin] = useState<number>(1.05);

  const { data: selectionsData, error: selectionsError, isLoading: selectionsLoading } = useSWR(
    ['selections', date, margin],
    ([, d, m]) => fetchSelections(d, m, undefined, 500), // Limit to 500 selections for performance
    {
      revalidateOnFocus: false,
      errorRetryCount: 2,
      errorRetryInterval: 2000,
    }
  );

  const { data: playbookData, error: playbookError } = useSWR<PlaybookResponse>('playbook', fetchPlaybook, {
    revalidateOnFocus: false,
  });

  const { data: topPicksData, error: topPicksError } = useSWR<TopPicksResponse>(
    ['top-picks', date],
    ([, d]: [string, string]) => fetchTopPicks(d, 10),
    { revalidateOnFocus: false }
  );

  const tabs: { id: Tab; label: string; icon: string }[] = [
    { id: 'today', label: 'Today', icon: '🎯' },
    { id: 'races', label: 'Races', icon: '🏇' },
    { id: 'playbook', label: 'Playbook', icon: '📊' },
    { id: 'history', label: 'History', icon: '📈' },
  ];

  return (
    <div className={styles.dashboard}>
      <header className={styles.header}>
        <div className={styles.headerContent}>
          <h1 className={styles.title}>HorseRacingML</h1>
          <p className={styles.subtitle}>ACE-powered betting intelligence for Australian racing</p>
        </div>
      </header>

      <nav className={styles.tabs}>
        {tabs.map((tab) => (
          <button
            key={tab.id}
            className={`${styles.tab} ${activeTab === tab.id ? styles.tabActive : ''}`}
            onClick={() => setActiveTab(tab.id)}
          >
            <span className={styles.tabIcon}>{tab.icon}</span>
            <span className={styles.tabLabel}>{tab.label}</span>
          </button>
        ))}
      </nav>

      <main className={styles.main}>
        {activeTab === 'today' && (
          <TodayTab
            topPicksData={topPicksData}
            playbookData={playbookData}
            date={date}
            setDate={setDate}
            topPicksError={topPicksError}
          />
        )}

        {activeTab === 'races' && (
          <RacesTab
            selectionsData={selectionsData}
            playbookData={playbookData}
            date={date}
            setDate={setDate}
            margin={margin}
            setMargin={setMargin}
            isLoading={selectionsLoading}
            error={selectionsError}
          />
        )}

        {activeTab === 'playbook' && (
          <PlaybookTab
            playbookData={playbookData}
            error={playbookError}
          />
        )}

        {activeTab === 'history' && (
          <HistoryTab playbookData={playbookData} />
        )}
      </main>
    </div>
  );
}
