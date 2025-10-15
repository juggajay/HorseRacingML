import type { Runner } from '../lib/api';
import styles from './SelectionTable.module.css';

interface Props {
  selections: Runner[];
}

export const SelectionTable: React.FC<Props> = ({ selections }) => {
  if (!selections.length) {
    return <p className={styles.empty}>No selections at the current settings.</p>;
  }

  return (
    <div className={styles.wrapper}>
      <table className={styles.table}>
        <thead>
          <tr>
            <th>Date</th>
            <th>Track</th>
            <th>Race</th>
            <th>Runner</th>
            <th>Odds</th>
            <th>Prob%</th>
            <th>Imp%</th>
            <th>Edge%</th>
            <th>Value%</th>
          </tr>
        </thead>
        <tbody>
          {selections.map((row) => {
            const edge = (row.model_prob - row.implied_prob) * 100;
            const value = row.value_pct !== undefined ? row.value_pct * 100 : undefined;
            return (
              <tr key={`${row.win_market_id}-${row.selection_id}`}>
                <td>{new Date(row.event_date).toLocaleDateString()}</td>
                <td>{row.track}</td>
                <td>{row.race_no}</td>
                <td>{row.selection_name}</td>
                <td>${row.win_odds.toFixed(2)}</td>
                <td>{(row.model_prob * 100).toFixed(1)}</td>
                <td>{(row.implied_prob * 100).toFixed(1)}</td>
                <td className={edge >= 0 ? styles.valuePositive : styles.valueNegative}>{edge.toFixed(1)}</td>
                <td>{value !== undefined ? value.toFixed(1) : '—'}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};
