export interface Runner {
  event_date: string;
  track: string;
  race_no: number;
  win_market_id: string;
  selection_id: string;
  selection_name: string;
  win_odds: number;
  model_prob: number;
  implied_prob: number;
  edge: number;
  value_pct?: number;
  betfair_horse_rating?: number;
  win_rate?: number;
  model_rank?: number;
}

export interface SelectionResponse {
  date?: string;
  start_date?: string;
  end_date?: string;
  margin: number;
  selections: Runner[];
  total?: number;
  limited?: boolean;
  message?: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? 'http://localhost:8000';
const todayIso = new Date().toISOString().slice(0, 10);

export interface PlaybookMetadata {
  generated_at: string;
  experience_rows: number;
  strategies_evaluated: number;
}

export interface PlaybookGlobal {
  total_bets: number;
  total_profit: number;
  total_staked: number;
  pot_pct: number;
  hit_rate: number | null;
}

export interface PlaybookStrategy {
  strategy_id: string;
  bets: number;
  wins: number;
  hit_rate: number;
  mean_edge: number;
  total_staked: number;
  total_profit: number;
  pot_pct: number;
  roi_pct: number;
  params?: Record<string, unknown> | null;
}

export interface PlaybookTrackInsight {
  track: string;
  bets: number;
  profit: number;
  pot_pct: number;
  hit_rate?: number;
}

export interface PlaybookContextInsight {
  track?: string;
  distance_band?: string;
  racing_type?: string;
  race_type?: string;
  bets: number;
  profit: number;
  pot_pct: number;
}

export interface PlaybookSnapshot {
  metadata: PlaybookMetadata;
  global: PlaybookGlobal;
  strategies: PlaybookStrategy[];
  tracks: PlaybookTrackInsight[];
  contexts: PlaybookContextInsight[];
}

export interface PlaybookResponse {
  history: PlaybookSnapshot[];
  latest: PlaybookSnapshot;
}

export interface AceRunResponse {
  status: string;
  message: string;
  target_date: string;
  started_at: string;
  finished_at: string;
  duration_seconds: number;
  experience_rows: number;
  strategies_evaluated: number;
  global_pot_pct: number | null;
  global_total_bets: number | null;
  playbook_generated_at?: string | null;
  schema_meetings_added: number;
  schema_races_added: number;
  schema_runners_added: number;
}

export async function fetchSelections(date?: string, margin?: number, top?: number, limit?: number) {
  const params = new URLSearchParams();
  if (date) params.append('date_str', date);
  if (margin) params.append('margin', margin.toString());
  if (top) params.append('top', top.toString());
  if (limit) params.append('limit', limit.toString());

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 180000); // 180 second (3 min) timeout for large datasets

  try {
    const res = await fetch(`${API_BASE}/selections?${params.toString()}`, {
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    if (res.status === 404) {
      const payload = await res.json().catch(() => ({ detail: 'No runners found' }));
      return {
        date: date ?? todayIso,
        margin: margin ?? 1.05,
        selections: [],
        total: 0,
        limited: false,
        message: typeof payload.detail === 'string' ? payload.detail : 'No runners found for the selected date.',
      };
    }

    if (!res.ok) {
      const errorText = await res.text().catch(() => 'Unknown error');
      throw new Error(`API error (${res.status}): ${errorText}`);
    }
    return (await res.json()) as SelectionResponse;
  } catch (error) {
    clearTimeout(timeoutId);
    if (error instanceof Error) {
      if (error.name === 'AbortError') {
        throw new Error('Request timeout - the data might be too large. Try selecting a specific date.');
      }
      throw error;
    }
    throw new Error('Failed to fetch selections');
  }
}

export async function fetchPlaybook(): Promise<PlaybookResponse> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 15000);

  try {
    const res = await fetch(`${API_BASE}/playbook`, { signal: controller.signal });
    clearTimeout(timeoutId);
    if (!res.ok) {
      const message = await res.text().catch(() => 'Unknown error');
      throw new Error(`Playbook error (${res.status}): ${message}`);
    }
    return (await res.json()) as PlaybookResponse;
  } catch (error) {
    clearTimeout(timeoutId);
    if (error instanceof Error) {
      if (error.name === 'AbortError') {
        throw new Error('Playbook request timeout');
      }
      throw error;
    }
    throw new Error('Failed to fetch playbook');
  }
}

export interface TopPick {
  track: string;
  race_no: number | null;
  selection_name: string;
  model_prob: number;
  confidence: string;
  win_odds: number | null;
  implied_prob: number | null;
  edge: number | null;
  summary: string;
  win_market_id: string;
  event_date: string;
}

export interface TopPicksResponse {
  date: string;
  total_races: number;
  total_runners: number;
  top_picks: TopPick[];
}

export async function fetchTopPicks(date?: string, limit?: number): Promise<TopPicksResponse> {
  const params = new URLSearchParams();
  if (date) params.append('date_str', date);
  if (limit) params.append('limit', limit.toString());

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 30000);

  try {
    const res = await fetch(`${API_BASE}/top-picks?${params.toString()}`, {
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    if (!res.ok) {
      const errorText = await res.text().catch(() => 'Unknown error');
      throw new Error(`API error (${res.status}): ${errorText}`);
    }
    return (await res.json()) as TopPicksResponse;
  } catch (error) {
    clearTimeout(timeoutId);
    if (error instanceof Error) {
      if (error.name === 'AbortError') {
        throw new Error('Request timeout - the data might be too large.');
      }
      throw error;
    }
    throw new Error('Failed to fetch top picks');
  }
}

export async function runAce(forceRefresh = false): Promise<AceRunResponse> {
  const res = await fetch(`${API_BASE}/ace/run`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ force_refresh: forceRefresh }),
  });

  if (!res.ok) {
    const message = await res.text().catch(() => 'Unknown error');
    throw new Error(`ACE run failed (${res.status}): ${message}`);
  }

  return (await res.json()) as AceRunResponse;
}
