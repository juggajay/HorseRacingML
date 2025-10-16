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
  date: string;
  margin: number;
  selections: Runner[];
}

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? 'http://localhost:8000';

export async function fetchSelections(date?: string, margin?: number, top?: number) {
  const params = new URLSearchParams();
  if (date) params.append('date_str', date);
  if (margin) params.append('margin', margin.toString());
  if (top) params.append('top', top.toString());

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout

  try {
    const res = await fetch(`${API_BASE}/selections?${params.toString()}`, {
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

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
